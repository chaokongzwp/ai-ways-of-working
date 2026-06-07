#!/usr/bin/env bash
# 把 docs/ 文档站发布到阿里云 OSS + 刷 CDN（纯静态，无构建步骤）
#
# 用法：
#   export ALIYUN_ACCESS_KEY_ID=xxx ALIYUN_ACCESS_KEY_SECRET=xxx
#   export OSS_BUCKET=your-doc-bucket
#   export CDN_DOMAIN=docs.example.com   # 可选；留空只传 OSS 不刷 CDN
#   bash scripts/deploy-oss-cdn.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── 配置（export 这些环境变量后再跑）──
DOCS_DIR="${DOCS_DIR:-${ROOT_DIR}/docs}"                        # 文档站目录
OSS_ENDPOINT="${OSS_ENDPOINT:-oss-ap-southeast-5.aliyuncs.com}" # 你的 OSS region endpoint
OSS_BUCKET="${OSS_BUCKET:?请设置 OSS_BUCKET（文档站的 OSS bucket 名）}"
OSS_BUCKET_ACL="${OSS_BUCKET_ACL:-private}"                     # CDN 回源用 private 即可
CDN_DOMAIN="${CDN_DOMAIN-}"                                     # 文档站域名；留空=只传 OSS、不刷 CDN
CDN_SCHEME="${CDN_SCHEME:-https}"
# ALIYUN_ACCESS_KEY_ID / ALIYUN_ACCESS_KEY_SECRET 必填（需有 OSS 读写 + CDN 刷新权限）

require_env() { [[ -n "${!1:-}" ]] || { echo "缺少环境变量: $1" >&2; exit 2; }; }
require_env ALIYUN_ACCESS_KEY_ID
require_env ALIYUN_ACCESS_KEY_SECRET
[[ -f "${DOCS_DIR}/index.html" ]] || { echo "找不到 ${DOCS_DIR}/index.html" >&2; exit 2; }

# ── 找 ossutil（未装则提示）──
OSSUTIL_BIN="${OSSUTIL_BIN:-}"
if [[ -z "$OSSUTIL_BIN" ]]; then
  if command -v ossutil64 >/dev/null 2>&1; then OSSUTIL_BIN="$(command -v ossutil64)"
  elif command -v ossutil  >/dev/null 2>&1; then OSSUTIL_BIN="$(command -v ossutil)"
  else echo "未找到 ossutil，请先安装（https://help.aliyun.com/zh/oss/developer-reference/ossutil）或设 OSSUTIL_BIN" >&2; exit 2; fi
fi

# ── 临时凭证配置（结束自动删）──
CFG="$(mktemp)"; trap 'rm -f "$CFG"' EXIT; chmod 600 "$CFG"
printf '[Credentials]\nlanguage=EN\nendpoint=%s\naccessKeyID=%s\naccessKeySecret=%s\n' \
  "$OSS_ENDPOINT" "$ALIYUN_ACCESS_KEY_ID" "$ALIYUN_ACCESS_KEY_SECRET" > "$CFG"

run() { "$OSSUTIL_BIN" --config-file "$CFG" -e "$OSS_ENDPOINT" "$@"; }

echo "发布 ${DOCS_DIR} → oss://${OSS_BUCKET}"
run mb "oss://${OSS_BUCKET}" --acl="$OSS_BUCKET_ACL" >/dev/null 2>&1 || true   # bucket 已存在则忽略

# 1) assets/ 长缓存（mermaid 等不常变；如需更新换文件名或单独刷）
if [[ -d "${DOCS_DIR}/assets" ]]; then
  run cp "${DOCS_DIR}/assets" "oss://${OSS_BUCKET}/assets" -r -f \
    --meta='Cache-Control:public,max-age=31536000'
fi

# 2) 其余文件（*.html / *.js / ...）no-cache —— 改了即时生效（配合 CDN 回源）
find "${DOCS_DIR}" -type f -not -path "${DOCS_DIR}/assets/*" -print0 | while IFS= read -r -d '' f; do
  rel="${f#"${DOCS_DIR}"/}"
  run cp "$f" "oss://${OSS_BUCKET}/${rel}" -f --meta='Cache-Control:no-cache'
done

# 3) 刷 CDN（可选）
if [[ -n "$CDN_DOMAIN" ]]; then
  if [[ -f "${SCRIPT_DIR}/refresh-cdn.py" ]]; then
    echo "刷新阿里云 CDN：${CDN_SCHEME}://${CDN_DOMAIN}/"
    CDN_DOMAIN="$CDN_DOMAIN" CDN_SCHEME="$CDN_SCHEME" python3 "${SCRIPT_DIR}/refresh-cdn.py" \
      || echo "⚠️ CDN 刷新失败（若用七牛云/其他 CDN，请去控制台手动刷新缓存）" >&2
  else
    echo "（CDN_DOMAIN 已设，但用的不是阿里云 CDN —— 请去对应 CDN 控制台刷新缓存）"
  fi
fi
echo "✅ 发布完成。"
