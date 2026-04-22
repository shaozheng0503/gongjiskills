#!/usr/bin/env bash
# 共绩算力 Skills 一键安装脚本
#
# 用法:
#   curl -fsSL https://raw.githubusercontent.com/shaozheng0503/gongjiskills/main/install.sh | bash
#   或: bash install.sh
#
# 可选环境变量:
#   GONGJI_TOKEN   安装后自动运行 gongji init --force 写入配置
#   GONGJI_REF     指定 pip 安装的 git ref (默认 main)

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { printf "${BLUE}==>${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}✓${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}!${NC}  %s\n" "$*"; }
fail()  { printf "${RED}✗${NC}  %s\n" "$*" >&2; exit 1; }

# ── 1. 环境检测 ───────────────────────────────────────────────────────────
info "检测运行环境..."

PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        PY="$cand"
        break
    fi
done
[ -z "$PY" ] && fail "未检测到 Python，请先安装 Python 3.8+"

PY_VER=$("$PY" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_OK=$("$PY" -c "import sys; print(1 if sys.version_info >= (3,8) else 0)")
[ "$PY_OK" = "1" ] || fail "需要 Python >=3.8，当前 $PY_VER"
ok "Python $PY_VER"

command -v "$PY" >/dev/null && "$PY" -m pip --version >/dev/null 2>&1 \
    || fail "pip 不可用，请先安装: $PY -m ensurepip --upgrade"
ok "pip 可用"

command -v openssl >/dev/null 2>&1 \
    || fail "未检测到 openssl，macOS: brew install openssl；Debian/Ubuntu: apt install openssl"
ok "openssl $(openssl version | awk '{print $2}')"

# ── 2. 安装 ────────────────────────────────────────────────────────────────
REF="${GONGJI_REF:-main}"
info "安装 gongjiskills ($REF) ..."

# 优先使用当前目录源码（如果在项目根）
if [ -f "$(dirname "$0")/pyproject.toml" ]; then
    "$PY" -m pip install --user --upgrade "$(dirname "$0")" >/tmp/gongji_install.log 2>&1 \
        || { cat /tmp/gongji_install.log; fail "pip install 失败"; }
    ok "已从本地源码安装"
else
    "$PY" -m pip install --user --upgrade \
        "git+https://github.com/shaozheng0503/gongjiskills.git@${REF}" >/tmp/gongji_install.log 2>&1 \
        || { cat /tmp/gongji_install.log; fail "pip install 失败，日志见 /tmp/gongji_install.log"; }
    ok "已从 GitHub 安装"
fi

# ── 3. PATH 提示 ───────────────────────────────────────────────────────────
if ! command -v gongji >/dev/null 2>&1; then
    USER_BIN="$("$PY" -c 'import site,sys; print(site.getuserbase()+"/bin")')"
    warn "gongji 不在 PATH 中，请将以下加入你的 shell 配置："
    printf "  export PATH=\"%s:\$PATH\"\n" "$USER_BIN"
else
    ok "gongji 已在 PATH: $(command -v gongji)"
fi

# ── 4. 可选：自动 init ─────────────────────────────────────────────────────
if [ -n "${GONGJI_TOKEN:-}" ]; then
    info "检测到 GONGJI_TOKEN，自动运行 init..."
    GONGJI_TOKEN="$GONGJI_TOKEN" gongji init --force || warn "init 未完成，请手动重试"
fi

# ── 5. 完成提示 ────────────────────────────────────────────────────────────
cat <<EOF

${GREEN}✓ 安装完成${NC}

下一步：
  1. 初始化：gongji init
     或非交互：GONGJI_TOKEN=xxx gongji init --force
  2. 查看 GPU： gongji resources
  3. 帮助文档： gongji --help

EOF
