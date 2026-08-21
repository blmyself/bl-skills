#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage:
  run_audit.sh \
    --design-spec /tmp/design_spec.json \
    --xib /absolute/path/View.xib \
    --swift /absolute/path/View.swift \
    [--presenter /absolute/path/Presenter.swift] \
    [--repo-root /absolute/path/repo] \
    [--out-dir /tmp/figma-uikit-audit] \
    [--donor-limit 5]
EOF
}

DESIGN_SPEC=""
XIB_PATH=""
SWIFT_PATH=""
PRESENTER_PATH=""
REPO_ROOT=""
OUT_DIR="/tmp/figma-uikit-audit"
DONOR_LIMIT="5"
RUNTIME_RISK_REPORT="$OUT_DIR/xib_runtime_risks.md"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-spec)
      DESIGN_SPEC="$2"; shift 2 ;;
    --xib)
      XIB_PATH="$2"; shift 2 ;;
    --swift)
      SWIFT_PATH="$2"; shift 2 ;;
    --presenter)
      PRESENTER_PATH="$2"; shift 2 ;;
    --repo-root)
      REPO_ROOT="$2"; shift 2 ;;
    --out-dir)
      OUT_DIR="$2"; shift 2 ;;
    --donor-limit)
      DONOR_LIMIT="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1 ;;
  esac
done

if [[ -z "$DESIGN_SPEC" || -z "$XIB_PATH" || -z "$SWIFT_PATH" ]]; then
  echo "ERROR: --design-spec, --xib, and --swift are required." >&2
  usage
  exit 2
fi

mkdir -p "$OUT_DIR"
IMPL_SNAPSHOT="$OUT_DIR/impl_snapshot.json"
ANALYSIS_REPORT="$OUT_DIR/analysis_report.md"
PATCH_HINTS="$OUT_DIR/patch_hints.md"
DONOR_REPORT="$OUT_DIR/donor_xib_candidates.md"

EXTRACT_CMD=(
  python3 "$SCRIPT_DIR/extract_uikit_impl_snapshot.py"
  --xib "$XIB_PATH"
  --swift "$SWIFT_PATH"
  --out "$IMPL_SNAPSHOT"
)

if [[ -n "$PRESENTER_PATH" ]]; then
  EXTRACT_CMD+=(--presenter "$PRESENTER_PATH")
fi

"${EXTRACT_CMD[@]}"

AUDIT_CMD=(
  python3 "$SCRIPT_DIR/figma_uikit_audit.py"
  --design-spec "$DESIGN_SPEC"
  --impl-snapshot "$IMPL_SNAPSHOT"
  --report-out "$ANALYSIS_REPORT"
  --patch-hints-out "$PATCH_HINTS"
)

if [[ -n "$REPO_ROOT" ]]; then
  AUDIT_CMD+=(
    --repo-root "$REPO_ROOT"
    --donor-out "$DONOR_REPORT"
    --donor-limit "$DONOR_LIMIT"
  )
fi

"${AUDIT_CMD[@]}"

python3 "$SCRIPT_DIR/xib_runtime_risk_scan.py" \
  --xib "$XIB_PATH" \
  --out "$RUNTIME_RISK_REPORT"

echo "Audit completed."
echo "- Snapshot: $IMPL_SNAPSHOT"
echo "- Analysis: $ANALYSIS_REPORT"
echo "- Patch hints: $PATCH_HINTS"
echo "- Runtime risks: $RUNTIME_RISK_REPORT"
if [[ -n "$REPO_ROOT" ]]; then
  echo "- Donors: $DONOR_REPORT"
fi
