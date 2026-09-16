#!/usr/bin/env python3
"""
Figma API Client Helper
封装对 Figma REST API 的请求、Token 自动探测、持久化缓存与配额感知限流。

限流模型对齐 Figma 官方文档 (2025-11-17 生效的分级漏桶配额):
  Tier 1 (最贵): GET file / GET file nodes / GET image   -> Pro 10, Org 15, Enterprise 20 次/分
  Tier 2:        image fills / comments / variables ...   -> Pro 25, Org 50, Enterprise 100 次/分
  Tier 3 (最廉): file meta / components / styles / users   -> Pro 50, Org 100, Enterprise 150 次/分
  Viewer/Collab 座位对 Tier 1 仅有 "6 次/月"，此时任何重试都无意义，必须快速失败。

核心策略:
  1. 请求前用「跨进程持久化令牌桶」主动限速，宁可本地等待也不触发 429;
  2. 命中 429 时读取 Retry-After 与 X-Figma-* 诊断头，写入共享冷却期，避免兄弟进程继续打墙;
  3. Retry-After 超过阈值 (默认 120s) 判定为配额耗尽 -> 立刻抛出可执行的错误提示，不再盲等;
  4. 磁盘缓存持久化到 ~/.cache 且用 sha256 做键，重复运行零请求。

可用环境变量:
  FIGMA_ACCESS_TOKEN / FIGMA_TOKEN   Personal Access Token
  FIGMA_PLAN            pro | org | enterprise | starter | view   (默认 pro)
                        starter/view 代表 Viewer/Collab 座位，会额外启用 Tier1「6 次/月」硬计数
  FIGMA_RATE_SAFETY     配额安全系数 0.1~1.0 (默认 0.8，即只用官方额度的 80%)
  FIGMA_RATE_TIER1/2/3  直接覆写每分钟额度 (调试用)
  FIGMA_CACHE_DIR       缓存根目录 (默认 ~/.cache/figma-to-ios-pro)
  FIGMA_CACHE_TTL       结构类响应缓存秒数 (默认 604800 = 7 天；设为 0 表示不读缓存)
  FIGMA_NO_CACHE=1      禁用读缓存 (仍写缓存；渲染 PNG 也会强制重新下载)
  FIGMA_OFFLINE=1       仅用缓存，缺失即报错，绝不发起网络请求
  FIGMA_MAX_RETRY_WAIT  单次 429 最长等待秒数 (默认 120)
"""

import os
import re
import sys
import json
import time
import random
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterable

try:
    import fcntl  # POSIX (macOS / Linux)
except ImportError:  # pragma: no cover - Windows 回退为无锁模式
    fcntl = None

SKILL_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- 配额模型 ----
# 官方每分钟额度 (Dev/Full 座位)；starter/view 代表 Viewer/Collab 座位
PLAN_LIMITS: Dict[str, Dict[int, float]] = {
    "pro":        {1: 10, 2: 25,  3: 50},
    "org":        {1: 15, 2: 50,  3: 100},
    "enterprise": {1: 20, 2: 100, 3: 150},
    "starter":    {1: 1,  2: 5,   3: 10},
    "view":       {1: 1,  2: 5,   3: 10},
}

# Viewer/Collab 座位的 Tier1 是「每月」配额，令牌桶无法表达月度额度，
# 必须额外做一个跨进程月计数器，否则一次批量切图就把全月 6 次烧干。
PLAN_MONTHLY_CAPS: Dict[str, Dict[int, int]] = {
    "starter": {1: 6},
    "view":    {1: 6},
}

TIER3_SUFFIXES = ("/components", "/component_sets", "/styles", "/meta", "/versions")
TIER2_SUFFIXES = ("/comments", "/dev_resources", "/images", "/variables/local",
                  "/variables/published", "/webhooks")

# Tier 1 是唯一真正稀缺的额度，请求前后都要格外吝啬
TIER1_BATCH_NODES = 180      # 单次 nodes 请求最多携带多少 node id
TIER1_BATCH_IMAGES = 60      # 单次 images 渲染请求最多携带多少 node id

IMAGE_URL_TTL = 86400        # 渲染 URL Figma 侧有效期约 30 天，本地缓存 1 天足够
CDN_MAX_RETRY = 4            # 图片 CDN (CloudFront) 也会 429，需要独立退避
NO_HEADER_COOLDOWN = 30.0    # 429 未带 Retry-After 时的最小冷却，自己也必须遵守
LOW_SEAT_COOLDOWN = 6 * 3600  # type=low 且无 Retry-After 时的冷却 (月度配额，短等待毫无意义)


def _tier_for_endpoint(endpoint: str) -> int:
    """按官方分级把 endpoint 映射到 Tier(1/2/3)，未知一律按最贵的 Tier 1 处理。"""
    path = endpoint.strip("/").split("?", 1)[0]
    for suffix in TIER3_SUFFIXES:
        if path.endswith(suffix):
            return 3
    for suffix in TIER2_SUFFIXES:
        if path.endswith(suffix):
            return 2
    if path.startswith(("files/", "images/")):
        return 1
    return 3 if path.startswith(("users/", "me")) else 1


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


class FigmaRateLimitError(RuntimeError):
    """配额已耗尽且等待时间不可接受时抛出，携带可执行的处置建议。"""

    def __init__(self, message: str, retry_after: int = 0, limit_type: str = "",
                 plan_tier: str = "", upgrade_link: str = ""):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit_type = limit_type
        self.plan_tier = plan_tier
        self.upgrade_link = upgrade_link


def find_figma_token() -> Optional[str]:
    """多级探测 Figma Access Token"""
    # 1. 环境变量
    token = os.environ.get("FIGMA_ACCESS_TOKEN") or os.environ.get("FIGMA_TOKEN")
    if token and token.strip():
        return token.strip()

    # 2. Skill 本地 .env
    env_paths = [
        SKILL_DIR / ".env",
        Path.home() / ".gemini" / "config" / "skills" / "figma-mcp" / ".env",
        Path.home() / ".gemini" / "config" / "skills" / "figma-to-ios-pro" / ".env",
        Path.cwd() / ".env"
    ]
    for p in env_paths:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    if line.startswith("FIGMA_ACCESS_TOKEN=") or line.startswith("FIGMA_TOKEN="):
                        k, v = line.split("=", 1)
                        val = v.strip().strip("'\"")
                        if val:
                            return val
            except Exception:
                pass
    return None


class _CrossProcessRateLimiter:
    """
    文件持久化的分级漏桶限流器。

    技能的每个脚本都是独立进程，进程内限流形同虚设，因此桶状态与冷却期
    必须落盘共享：state.json 记录每个 Tier 的剩余令牌与全局冷却截止时间。
    """

    def __init__(self, state_dir: Path, plan: str, safety: float):
        self.state_file = state_dir / "ratelimit_state.json"
        self.lock_file = state_dir / "ratelimit.lock"
        state_dir.mkdir(parents=True, exist_ok=True)

        self.plan = plan
        base = PLAN_LIMITS.get(plan, PLAN_LIMITS["pro"])
        safety = min(max(safety, 0.1), 1.0)
        self.limits: Dict[int, float] = {}
        for tier in (1, 2, 3):
            override = _env_float(f"FIGMA_RATE_TIER{tier}", 0)
            self.limits[tier] = override if override > 0 else max(base[tier] * safety, 1.0)
        self.monthly_caps: Dict[int, int] = dict(PLAN_MONTHLY_CAPS.get(plan, {}))

    # ---- 月度配额 (Viewer/Collab 座位的 Tier1) ----
    @staticmethod
    def _month_key() -> str:
        t = time.gmtime()
        return f"{t.tm_year}-{t.tm_mon:02d}"

    def monthly_state(self, tier: int) -> Optional[Dict[str, int]]:
        """返回 {'used': n, 'cap': m}；该 Tier 无月度上限时返回 None。"""
        cap = self.monthly_caps.get(tier)
        if not cap:
            return None
        state = self._read()
        month = state.get("monthly", {}).get(self._month_key(), {})
        return {"used": int(month.get(str(tier), 0)), "cap": cap}

    def consume_monthly(self, tier: int) -> None:
        """记一次月度用量 (仅对有月度上限的 Tier 生效)。"""
        if not self.monthly_caps.get(tier):
            return
        handle = self._locked()
        try:
            state = self._read()
            monthly = state.setdefault("monthly", {})
            # 只保留当月，避免状态文件无限增长
            key = self._month_key()
            month = monthly.setdefault(key, {})
            month[str(tier)] = int(month.get(str(tier), 0)) + 1
            state["monthly"] = {key: month}
            self._write(state)
        finally:
            self._unlock(handle)

    # ---- 文件锁 ----
    def _locked(self):
        handle = open(self.lock_file, "a+")
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except OSError:
                pass
        return handle

    @staticmethod
    def _unlock(handle) -> None:
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def _read(self) -> Dict[str, Any]:
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        # 只接受对象；手工改坏或被别的工具写成 list/字符串时，
        # 后面的 state.setdefault(...) 会直接 AttributeError 崩掉整个脚本。
        return state if isinstance(state, dict) else {}

    def _write(self, state: Dict[str, Any]) -> None:
        # 临时文件必须带 pid：Windows 无 fcntl、flock 失败也会被静默忽略，
        # 共用一个 .tmp 会让两个写者互相截断，_read 再把损坏 JSON 当成空状态
        # (等于桶回满 + 冷却期丢失，429 后立刻又是一波连打)。
        tmp = self.state_file.with_suffix(f".tmp.{os.getpid()}")
        try:
            tmp.write_text(json.dumps(state), encoding="utf-8")
            tmp.replace(self.state_file)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    # ---- 冷却期 ----
    def cooldown_remaining(self, tier: int) -> float:
        state = self._read()
        until = float(state.get("cooldown", {}).get(str(tier), 0))
        return max(0.0, until - time.time())

    def set_cooldown(self, tier: int, seconds: float) -> None:
        handle = self._locked()
        try:
            state = self._read()
            cooldown = state.setdefault("cooldown", {})
            cooldown[str(tier)] = max(float(cooldown.get(str(tier), 0)), time.time() + seconds)
            # 429 说明桶已空，同步清零本地令牌，避免刚解冻就再次连打
            state.setdefault("buckets", {})[str(tier)] = {"tokens": 0.0, "ts": time.time()}
            self._write(state)
        finally:
            self._unlock(handle)

    # ---- 取令牌 ----
    def acquire(self, tier: int, verbose: bool = True) -> None:
        """阻塞直到该 Tier 有可用额度；主动等待远比事后吃 429 便宜。"""
        capacity = self.limits[tier]
        refill_per_sec = capacity / 60.0

        while True:
            handle = self._locked()
            try:
                state = self._read()
                bucket = state.setdefault("buckets", {}).setdefault(
                    str(tier), {"tokens": capacity, "ts": time.time()}
                )
                now = time.time()
                elapsed = max(0.0, now - float(bucket.get("ts", now)))
                tokens = min(capacity, float(bucket.get("tokens", capacity)) + elapsed * refill_per_sec)

                if tokens >= 1.0:
                    bucket["tokens"] = tokens - 1.0
                    bucket["ts"] = now
                    self._write(state)
                    return

                wait = (1.0 - tokens) / refill_per_sec
                bucket["tokens"] = tokens
                bucket["ts"] = now
                self._write(state)
            finally:
                self._unlock(handle)

            wait = min(wait + random.uniform(0, 0.5), 75.0)
            if verbose:
                print(f"⏳ Tier{tier} 本地配额已用尽 (上限 {capacity:.0f} 次/分)，"
                      f"主动等待 {wait:.1f}s 以避免触发 429…", file=sys.stderr)
            time.sleep(wait)


class FigmaAPIClient:
    BASE_URL = "https://api.figma.com/v1"

    def __init__(self, token: Optional[str] = None, cache_dir: Optional[Path] = None,
                 plan: Optional[str] = None, verbose: bool = True):
        self.token = token or find_figma_token()
        if not self.token:
            raise ValueError(
                "❌ 未找到有效的 Figma Token。\n"
                "👉 快速配置：复制 skill 目录下的 .env.example 为 .env 并填入 Token：\n"
                "   cp .env.example .env (编辑填入 FIGMA_ACCESS_TOKEN=figd_...)\n"
                "👉 或在终端环境中设置：export FIGMA_ACCESS_TOKEN=figd_..."
            )
        self.verbose = verbose
        self.plan = (plan or os.environ.get("FIGMA_PLAN") or "pro").strip().lower()

        default_root = Path(os.environ.get("FIGMA_CACHE_DIR") or (Path.home() / ".cache" / "figma-to-ios-pro"))
        self.cache_dir = Path(cache_dir) if cache_dir else default_root
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.cache_dir = Path("/tmp") / "figma_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_ttl = _env_float("FIGMA_CACHE_TTL", 604800.0)
        self.read_cache = not _env_flag("FIGMA_NO_CACHE")
        self.offline = _env_flag("FIGMA_OFFLINE")
        self.max_retry_wait = _env_float("FIGMA_MAX_RETRY_WAIT", 120.0)
        self.limiter = _CrossProcessRateLimiter(
            self.cache_dir, self.plan, _env_float("FIGMA_RATE_SAFETY", 0.8)
        )
        self.request_counts: Dict[int, int] = {1: 0, 2: 0, 3: 0}
        self.cache_hits = 0
        self.last_429: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------- 缓存 ----
    def _cache_path(self, endpoint: str, query_str: str) -> Path:
        """用 sha256 做缓存键：旧实现按 120 字符截断，多 node id 请求会互相串味。"""
        digest = hashlib.sha256(f"{endpoint}{query_str}".encode("utf-8")).hexdigest()[:24]
        readable = endpoint.strip("/").replace("/", "_")[:60] or "root"
        return self.cache_dir / "responses" / f"{readable}.{digest}.json"

    def _read_cache(self, path: Path, ttl: float) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            if ttl > 0 and (time.time() - path.stat().st_mtime) > ttl:
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_cache(self, path: Path, data: Dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    # -------------------------------------------------------- 429 处理 ----
    def _handle_429(self, err: urllib.error.HTTPError, tier: int, attempt: int,
                    endpoint: str) -> float:
        """返回本进程应等待的秒数；抛 FigmaRateLimitError 表示不该再重试。"""
        headers = getattr(err, "headers", {}) or {}
        try:
            retry_after = int(float(headers.get("Retry-After") or 0))
        except (TypeError, ValueError):
            retry_after = 0
        limit_type = (headers.get("X-Figma-Rate-Limit-Type") or "").strip().lower()
        plan_tier = (headers.get("X-Figma-Plan-Tier") or "").strip()
        upgrade_link = (headers.get("X-Figma-Upgrade-Link") or "").strip()

        # 缺 Retry-After 时的兜底冷却：type=low 属于月度配额，短等待毫无意义
        if retry_after > 0:
            cooldown = float(retry_after)
        elif limit_type == "low":
            cooldown = float(LOW_SEAT_COOLDOWN)
        else:
            cooldown = max(NO_HEADER_COOLDOWN, min(2 ** attempt * 5, self.max_retry_wait))

        # 无论如何都要落盘冷却期，兄弟进程才不会继续撞墙
        self.limiter.set_cooldown(tier, cooldown)
        self.last_429 = {"endpoint": endpoint, "tier": tier, "retry_after": retry_after,
                         "limit_type": limit_type, "plan_tier": plan_tier,
                         "upgrade_link": upgrade_link}

        if cooldown > self.max_retry_wait or limit_type == "low":
            raise self._quota_error(endpoint, tier, retry_after, limit_type,
                                    plan_tier, upgrade_link, cooldown)

        # 关键：自己必须遵守刚写下的冷却期，否则兄弟进程被挡在门外时
        # 本进程还在 60s 窗口内连打 4 次，正是会延长封禁的行为。
        wait = cooldown + random.uniform(0, 1.5)
        if self.verbose:
            src = f"Retry-After={retry_after}s" if retry_after > 0 else "无 Retry-After 头，按兜底冷却"
            print(f"⚠️ 收到 Figma 429 (Tier{tier}, type={limit_type or 'n/a'}, {src})，"
                  f"等待 {wait:.1f}s 后重试…", file=sys.stderr)
        return wait

    def _quota_error(self, endpoint: str, tier: int, retry_after: int, limit_type: str,
                     plan_tier: str, upgrade_link: str, cooldown: float) -> FigmaRateLimitError:
        hint = [f"❌ Figma 配额已耗尽 (HTTP 429, endpoint={endpoint}, Tier{tier})。"]
        if retry_after > 0:
            hint.append(f"   Retry-After = {retry_after}s"
                        + (f" (≈{retry_after / 3600:.1f} 小时)" if retry_after > 3600 else ""))
        else:
            hint.append(f"   响应未带 Retry-After，已按 {cooldown:.0f}s 冷却处理。")
        if plan_tier:
            hint.append(f"   账号套餐: {plan_tier}")
        if limit_type == "low":
            hint.append("   X-Figma-Rate-Limit-Type=low → 当前 Token 属于 Viewer/Collab 座位，"
                        "Tier1 (file/nodes/image) 全月仅 6 次，重试无意义。")
            hint.append("   处置: 换用 Full/Dev 座位的 Personal Access Token，或改走 Figma Desktop MCP 通道。")
        else:
            hint.append("   处置: 稍后重跑 (缓存已保留已完成部分)，或降低 FIGMA_RATE_SAFETY 让本地限速更保守。")
        if upgrade_link:
            hint.append(f"   升级链接: {upgrade_link}")
        return FigmaRateLimitError("\n".join(hint), retry_after, limit_type, plan_tier, upgrade_link)

    def _check_monthly_budget(self, tier: int, endpoint: str) -> None:
        """Viewer/Collab 座位的 Tier1 是月度配额，用光了必须快速失败而不是慢慢试。"""
        info = self.limiter.monthly_state(tier)
        if not info:
            return
        if info["used"] >= info["cap"]:
            raise FigmaRateLimitError(
                f"❌ 本月 Tier{tier} 配额已用完 ({info['used']}/{info['cap']} 次, endpoint={endpoint})。\n"
                f"   FIGMA_PLAN={self.plan} 对应 Viewer/Collab 座位，Tier1 (file/nodes/image) 全月仅 "
                f"{info['cap']} 次。\n"
                f"   处置: 换用 Full/Dev 座位的 Personal Access Token，或改走 Figma Desktop MCP 通道；\n"
                f"        若你的座位其实是 Full/Dev，请设置 FIGMA_PLAN=pro|org|enterprise。",
                limit_type="low",
            )
        if self.verbose and info["cap"] - info["used"] <= 2:
            print(f"⚠️ 本月 Tier{tier} 配额仅剩 {info['cap'] - info['used']} 次 "
                  f"(已用 {info['used']}/{info['cap']})，请谨慎使用。", file=sys.stderr)

    # ------------------------------------------------------------ 请求 ----
    def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None,
                      use_cache: bool = True, cache_ttl: Optional[float] = None,
                      cache_ok=None) -> Dict[str, Any]:
        """
        cache_ok: 可选断言，返回 False 时本次响应不写缓存 (例如 images 渲染失败返回了 null，
                  若照常缓存 24h，重跑会一直复用这份残缺结果，永远不再重试渲染)。
        """
        query_str = ""
        if params:
            query_str = "?" + urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}/{endpoint}{query_str}"

        tier = _tier_for_endpoint(endpoint)
        ttl = self.cache_ttl if cache_ttl is None else cache_ttl
        cache_file = self._cache_path(endpoint, query_str)

        # ttl<=0 语义是「不要用缓存」，而不是「永不过期」
        if use_cache and self.read_cache and ttl > 0:
            cached = self._read_cache(cache_file, ttl)
            if cached is not None:
                self.cache_hits += 1
                return cached

        if self.offline:
            raise RuntimeError(
                f"❌ FIGMA_OFFLINE=1 但缓存缺失: {endpoint}{query_str}\n"
                f"   请先在联网模式下跑一次，或取消 FIGMA_OFFLINE。"
            )

        self._check_monthly_budget(tier, endpoint)

        cooling = self.limiter.cooldown_remaining(tier)
        if cooling > 0:
            if cooling > self.max_retry_wait:
                raise FigmaRateLimitError(
                    f"❌ Tier{tier} 仍处于 429 冷却期，还需 {cooling:.0f}s (>{self.max_retry_wait:.0f}s 阈值)。\n"
                    f"   已中止以避免延长封禁；请稍后重跑，缓存会跳过已完成的请求。",
                    retry_after=int(cooling),
                )
            if self.verbose:
                print(f"⏸️ Tier{tier} 处于 429 冷却期，等待 {cooling:.1f}s…", file=sys.stderr)
            time.sleep(cooling + random.uniform(0, 1.0))

        max_retries = 5
        last_err: Optional[BaseException] = None
        self.last_429: Optional[Dict[str, Any]] = None
        for attempt in range(max_retries):
            self.limiter.acquire(tier, verbose=self.verbose)
            req = urllib.request.Request(url)
            req.add_header("X-Figma-Token", self.token)
            req.add_header("User-Agent", "FigmaToIOSPro/2.1")
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                self.request_counts[tier] = self.request_counts.get(tier, 0) + 1
                self.limiter.consume_monthly(tier)
                if use_cache and (cache_ok is None or cache_ok(data)):
                    self._write_cache(cache_file, data)
                return data
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    last_err = e
                    wait = self._handle_429(e, tier, attempt, endpoint)
                    if attempt == max_retries - 1:
                        break  # 最后一次没有下一轮了，别再白等 wait 秒才报错
                    time.sleep(wait)
                    continue
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="ignore")[:500]
                except Exception:
                    pass
                if e.code in (500, 502, 503, 504) and attempt < max_retries - 1:
                    wait = min(2 ** attempt * 2, 30) + random.uniform(0, 1)
                    if self.verbose:
                        print(f"⚠️ Figma 服务端 {e.code}，{wait:.1f}s 后重试…", file=sys.stderr)
                    time.sleep(wait)
                    last_err = e
                    continue
                raise RuntimeError(f"Figma API 请求失败 [HTTP {e.code}] {endpoint}: {body}")
            except Exception as e:
                last_err = e
                if attempt == max_retries - 1:
                    raise
                time.sleep(min(2 ** attempt * 2, 20) + random.uniform(0, 1))

        # 重试全部用完。若最后是 429，必须抛配额错误 (带处置建议 + run_cli 退出码 2)，
        # 而不是一句 last_err=None 的通用 RuntimeError。
        if self.last_429:
            info = self.last_429
            raise self._quota_error(endpoint, tier, info["retry_after"], info["limit_type"],
                                    info["plan_tier"], info["upgrade_link"],
                                    self.limiter.cooldown_remaining(tier))
        raise RuntimeError(f"Figma API 重试 {max_retries} 次仍失败: {endpoint} ({last_err})")

    def usage_summary(self) -> str:
        used = ", ".join(f"Tier{t}={self.request_counts.get(t, 0)}" for t in (1, 2, 3))
        extra = ""
        info = self.limiter.monthly_state(1)
        if info:
            extra = f"；本月 Tier1 已用 {info['used']}/{info['cap']}"
        return f"📊 本次实际网络请求: {used}；缓存命中 {self.cache_hits} 次{extra}"


    # ---------------------------------------------------------- Endpoints ----
    @staticmethod
    def _chunks(items: List[str], size: int) -> Iterable[List[str]]:
        for i in range(0, len(items), size):
            yield items[i:i + size]

    @staticmethod
    def _normalize_ids(node_ids: Iterable[str]) -> List[str]:
        """归一化 node id 并去重 (保持顺序)，重复 id 白烧 Tier1 配额。"""
        seen, out = set(), []
        for nid in node_ids:
            clean = str(nid).strip().replace("%3A", ":").replace("-", ":")
            if clean and clean not in seen:
                seen.add(clean)
                out.append(clean)
        return out

    def get_file(self, file_key: str, depth: Optional[int] = None) -> Dict[str, Any]:
        """获取文件结构 [Tier 1 — 最稀缺，务必配合 depth 限制层级]"""
        params = {}
        if depth is not None:
            params["depth"] = str(depth)
        return self._make_request(f"files/{file_key}", params=params if params else None)

    def get_file_meta(self, file_key: str) -> Dict[str, Any]:
        """获取文件元数据 (名称/最后修改时间) [Tier 3 — 只想拿文件名时用它，别拉整棵树]"""
        return self._make_request(f"files/{file_key}/meta")

    def get_file_name(self, file_key: str, fallback: str = "App Design") -> str:
        """
        安全获取文件名：优先走 Tier3 的 files/:key/meta。
        注意 meta 需要 file_metadata:read scope，只授了 file_content:read 的 Token 会 403，
        此时退回 Tier1 的 files/:key?depth=1 (响应很小，只有画布层)，别让标题退化成占位串。

        文件名只是文档标题，属于「可降级」信息：本方法永不向上抛异常 (包括配额错误)，
        否则一个纯装饰性的取名请求就能把只靠 Tier3 就能跑完的脚本整体带崩；
        真正需要配额的主流程会在后面自己报同样的错。
        """
        try:
            meta = self.get_file_meta(file_key)
            name = (meta.get("file") or meta.get("meta") or {}).get("name") or meta.get("name")
            if name:
                return str(name)
        except FigmaRateLimitError as e:
            if self.verbose:
                print(f"ℹ️ 取文件名时遇到配额限制，改用占位标题 ({fallback}):\n{e}", file=sys.stderr)
            return fallback
        except Exception as e:
            if self.verbose:
                print(f"ℹ️ files/:key/meta 不可用 ({e})，"
                      f"提示: Token 作用域需包含 file_metadata:read。", file=sys.stderr)

        # Tier1 兜底要克制：Viewer/Collab 座位全月只有 6 次 Tier1，
        # 冷却期内或月度配额将满时，宁可用占位标题也不为一个 name 字段烧掉一次。
        monthly = self.limiter.monthly_state(1)
        if monthly or self.limiter.cooldown_remaining(1) > 0:
            if self.verbose:
                print(f"ℹ️ 跳过 Tier1 兜底取名 (座位/冷却期额度太珍贵)，使用占位标题: {fallback}",
                      file=sys.stderr)
            return fallback
        try:
            if self.verbose:
                print("ℹ️ 回退 files/:key?depth=1 取文件名 (Tier1，响应仅画布层)…", file=sys.stderr)
            return str(self.get_file(file_key, depth=1).get("name") or fallback)
        except Exception as e:
            if self.verbose:
                print(f"ℹ️ 读取文件名失败 (不影响主流程): {e}", file=sys.stderr)
        return fallback

    def get_styles(self, file_key: str) -> Dict[str, Any]:
        """获取文件中定义的所有全局样式 [Tier 3]"""
        return self._make_request(f"files/{file_key}/styles")

    def get_components(self, file_key: str) -> Dict[str, Any]:
        """获取文件中所有已发布的通用组件 [Tier 3]"""
        return self._make_request(f"files/{file_key}/components")

    def get_nodes(self, file_key: str, node_ids: List[str],
                  depth: Optional[int] = None) -> Dict[str, Any]:
        """批量获取 Node 详细数据 [Tier 1]，自动去重并分批，绝不静默截断。"""
        clean_ids = self._normalize_ids(node_ids)
        if not clean_ids:
            return {"nodes": {}}
        merged: Dict[str, Any] = {"nodes": {}}
        batches = list(self._chunks(clean_ids, TIER1_BATCH_NODES))
        for idx, batch in enumerate(batches, 1):
            params = {"ids": ",".join(batch)}
            if depth is not None:
                params["depth"] = str(depth)
            if self.verbose and len(batches) > 1:
                print(f"  → nodes 分批 {idx}/{len(batches)} ({len(batch)} 个节点)", file=sys.stderr)
            res = self._make_request(f"files/{file_key}/nodes", params=params)
            merged["nodes"].update(res.get("nodes", {}) or {})
            for k, v in res.items():
                if k != "nodes":
                    merged.setdefault(k, v)
        return merged

    def get_images(self, file_key: str, node_ids: List[str], scale: int = 2,
                   fmt: str = "png") -> Dict[str, str]:
        """渲染并获取 Node 截图 URL [Tier 1]，自动去重分批合并。"""
        clean_ids = self._normalize_ids(node_ids)
        if not clean_ids:
            return {}
        images: Dict[str, str] = {}
        batches = list(self._chunks(clean_ids, TIER1_BATCH_IMAGES))
        for idx, batch in enumerate(batches, 1):
            if self.verbose and len(batches) > 1:
                print(f"  → images 分批 {idx}/{len(batches)} ({len(batch)} 个节点 @{scale}x)", file=sys.stderr)

            # Figma 渲染失败时会返回 HTTP 200 + null URL。这种残缺结果绝不能进缓存，
            # 否则 24h 内每次重跑都复用 null，"重跑即续传" 变成永远续不上。
            def _complete(data: Dict[str, Any], _batch=batch) -> bool:
                got = data.get("images") or {}
                return all(got.get(n) for n in _batch)

            res = self._make_request(
                f"images/{file_key}",
                params={"ids": ",".join(batch), "scale": str(scale), "format": fmt},
                cache_ttl=IMAGE_URL_TTL,
                cache_ok=_complete,
            )
            missing = [n for n in batch if not (res.get("images") or {}).get(n)]
            if missing and self.verbose:
                print(f"    ⚠️ {len(missing)} 个节点 Figma 未渲染成功 (未写缓存，重跑会重新渲染)",
                      file=sys.stderr)
            for k, v in (res.get("images") or {}).items():
                if v:
                    images[k] = v
        return images


    def image_cache_path(self, file_key: str, node_id: str, scale: int, image_url: str,
                         fmt: str = "png") -> Path:
        """
        渲染图的本地缓存路径。文件名带 URL 指纹：Figma 每次渲染都会给出新的 S3 URL，
        因此设计稿改动 (或 FIGMA_NO_CACHE 强制重取 URL) 会自然落到新文件，
        不会像只用 node_id 命名那样把过期 PNG 永久钉在缓存里。

        同时顺手清掉同一 node/倍数下的旧指纹文件，否则每次设计稿更新都会在
        缓存目录里多留一份永不回收的死 PNG。
        """
        safe_id = re.sub(r"[^A-Za-z0-9_]", "_", str(node_id))
        stamp = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:12]
        target = self.cache_dir / "images" / file_key / f"{safe_id}@{scale}x.{stamp}.{fmt}"
        try:
            cutoff = time.time() - 3600
            for old in target.parent.glob(f"{safe_id}@{scale}x.*.{fmt}"):
                # 只清 1 小时前的旧指纹：并发跑同一文件时，别把兄弟进程刚下好的图删掉
                if old != target and old.stat().st_mtime < cutoff:
                    old.unlink()
        except OSError:
            pass
        return target

    def download_image(self, image_url: str, dest_path: Path,
                       skip_if_exists: bool = False) -> Path:
        """
        下载渲染图片 [走 CloudFront，不占 REST 配额但同样会 429]。
        批量切图时 CDN 会在十几个请求后开始限流，因此这里也做退避重试。
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # FIGMA_NO_CACHE=1 语义是强制刷新，图片同样要重新下载
        if skip_if_exists and self.read_cache and dest_path.exists() and dest_path.stat().st_size > 0:
            return dest_path

        last_err: Optional[BaseException] = None
        for attempt in range(CDN_MAX_RETRY):
            req = urllib.request.Request(image_url, headers={"User-Agent": "FigmaToIOSPro/2.1"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = resp.read()
                if not payload:
                    raise RuntimeError("下载内容为空")
                # 先写临时文件再原子改名：中途被 Ctrl-C / 杀进程也不会留下
                # 一个「体积>0 但内容截断」的文件被后续运行当成有效缓存复用。
                tmp = dest_path.with_name(dest_path.name + f".part.{os.getpid()}")
                tmp.write_bytes(payload)
                tmp.replace(dest_path)
                return dest_path
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code not in (429, 500, 502, 503, 504) or attempt == CDN_MAX_RETRY - 1:
                    raise
                try:
                    retry_after = int(float((getattr(e, "headers", {}) or {}).get("Retry-After") or 0))
                except (TypeError, ValueError):
                    retry_after = 0
                # CDN 有时返回荒谬的 Retry-After (数万秒)，必须夹紧
                wait = min(retry_after, 30) if retry_after > 0 else min(2 ** attempt * 2, 30)
                wait += random.uniform(0, 1.0)
                if self.verbose:
                    print(f"⚠️ 图片 CDN 返回 {e.code}，{wait:.1f}s 后重试 "
                          f"({attempt + 1}/{CDN_MAX_RETRY})…", file=sys.stderr)
                time.sleep(wait)
            except Exception as e:
                last_err = e
                if attempt == CDN_MAX_RETRY - 1:
                    raise
                time.sleep(min(2 ** attempt * 2, 20) + random.uniform(0, 1))

        raise RuntimeError(f"图片下载失败: {image_url} ({last_err})")


def run_cli(main_func) -> None:
    """统一入口包装：把配额类错误转成清晰的退出提示，而不是一坨 traceback。"""
    try:
        main_func()
    except FigmaRateLimitError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\n⏹️ 已中断 (缓存保留，重跑会跳过已完成请求)。", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    client = FigmaAPIClient()
    print("✅ Figma API Client 初始化成功，已检测到有效 Token！")
    print(f"   套餐档位: {client.plan} | 本地限速: "
          + ", ".join(f"Tier{t}={client.limiter.limits[t]:.0f}/min" for t in (1, 2, 3)))
    print(f"   缓存目录: {client.cache_dir}")
    for tier in (1, 2, 3):
        cooling = client.limiter.cooldown_remaining(tier)
        if cooling > 0:
            print(f"   ⏸️ Tier{tier} 仍在 429 冷却期，剩余 {cooling:.0f}s")

    if "--diagnose" in sys.argv:
        # 只打一个 Tier 3 请求 (users/me)，用于确认 Token 是否具备 Full/Dev 座位
        print("\n🩺 正在用 1 次 Tier3 请求探测 Token 归属账号…")
        try:
            me = client._make_request("me", use_cache=False)
            print(f"   账号: {me.get('handle') or me.get('id')}")
            print(f"   ℹ️ Token 有效。若仍频繁 429，多为座位类型 (Viewer/Collab) 导致 Tier1 仅 6 次/月，"
                  f"请在 429 报错里查看 X-Figma-Rate-Limit-Type 是否为 low。")
        except FigmaRateLimitError as e:
            print(str(e), file=sys.stderr)
            sys.exit(2)
        except RuntimeError as e:
            msg = str(e)
            if "403" in msg or "Invalid token" in msg:
                print("   ❌ Token 无效或已过期 (HTTP 403 Invalid token)。", file=sys.stderr)
                print("      请到 Figma → Settings → Security → Personal access tokens 重新生成，"
                      "作用域需包含 file_content:read 与 file_metadata:read。", file=sys.stderr)
            else:
                print(f"   ❌ 探测失败: {msg}", file=sys.stderr)
            sys.exit(2)
