#!/usr/bin/env python3
"""
Figma API Client Helper
封装了对 Figma REST API 的请求、Token 自动探测、本地缓存与防重试机制。
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

SKILL_DIR = Path(__file__).resolve().parent.parent


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


class FigmaAPIClient:
    BASE_URL = "https://api.figma.com/v1"

    def __init__(self, token: Optional[str] = None, cache_dir: Optional[Path] = None):
        self.token = token or find_figma_token()
        if not self.token:
            raise ValueError(
                "❌ 未找到有效的 Figma Token。请在 ~/.zshrc 或 skill 的 .env 中设置 FIGMA_ACCESS_TOKEN=figd_..."
            )
        self.cache_dir = cache_dir or (Path("/tmp") / "figma_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None, use_cache: bool = True) -> Dict[str, Any]:
        """发起 HTTP 请求并自动处理缓存与重试"""
        query_str = ""
        if params:
            query_str = "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{self.BASE_URL}/{endpoint}{query_str}"

        clean_name = endpoint.replace('/', '_') + (f"_{urllib.parse.quote_plus(query_str)}" if query_str else "")
        if len(clean_name) > 120:
            clean_name = clean_name[:120]
        cache_file = self.cache_dir / f"{clean_name}.json"

        if use_cache and cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        req = urllib.request.Request(url)
        req.add_header("X-Figma-Token", self.token)
        req.add_header("User-Agent", "FigmaToIOSPro/2.0")

        max_retries = 5
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if use_cache:
                        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    return data
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait_time = (attempt + 1) * 4
                    print(f"⚠️ 收到 Figma 429 限流提示，等待 {wait_time} 秒后重试 (第 {attempt+1}/{max_retries} 次)...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                else:
                    err_msg = e.read().decode("utf-8", errors="ignore")
                    raise RuntimeError(f"Figma API 请求失败 [HTTP {e.code}]: {err_msg}")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)

        raise RuntimeError("Figma API 请求超时或超出重试上限")

    def get_file(self, file_key: str, depth: Optional[int] = None) -> Dict[str, Any]:
        """获取文件结构 (可通过 depth 限制层级以加速扫描)"""
        params = {}
        if depth is not None:
            params["depth"] = str(depth)
        return self._make_request(f"files/{file_key}", params=params if params else None)

    def get_styles(self, file_key: str) -> Dict[str, Any]:
        """获取文件中定义的所有全局样式 (Colors, Typography, Effects)"""
        return self._make_request(f"files/{file_key}/styles")

    def get_components(self, file_key: str) -> Dict[str, Any]:
        """获取文件中所有已发布的通用组件"""
        return self._make_request(f"files/{file_key}/components")

    def get_nodes(self, file_key: str, node_ids: List[str]) -> Dict[str, Any]:
        """批量获取指定 Node ID 的详细数据"""
        clean_ids = [nid.replace("-", ":") for nid in node_ids]
        return self._make_request(f"files/{file_key}/nodes", params={"ids": ",".join(clean_ids)})

    def get_images(self, file_key: str, node_ids: List[str], scale: int = 2, fmt: str = "png") -> Dict[str, str]:
        """渲染并获取指定 Node 的高清截图 URL 映射"""
        clean_ids = [nid.replace("-", ":") for nid in node_ids]
        res = self._make_request(f"images/{file_key}", params={"ids": ",".join(clean_ids), "scale": str(scale), "format": fmt})
        return res.get("images", {})

    def download_image(self, image_url: str, dest_path: Path) -> Path:
        """下载渲染图片到本地指定路径"""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(image_url, headers={"User-Agent": "FigmaToIOSPro/2.0"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        return dest_path


if __name__ == "__main__":
    client = FigmaAPIClient()
    print("✅ Figma API Client 初始化成功，已检测到有效 Token！")
