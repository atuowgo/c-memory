#!/usr/bin/env bash
# c-memory 首次使用安装脚本：建 venv、装依赖、建数据目录、生成 .env、
# 把 hooks 配置合并进目标项目的 .claude/settings.json（不覆盖已有配置）。
#
# 用法：把整个 dist/ 目录（改名不改名都行，比如改成 c-memory/）当**一个子目录**
# 放进目标项目根目录下，例如 target-project/c-memory/，然后在这个子目录里执行：
#   ./install.sh
# 本脚本会自动识别自己所在的子目录名，把 .claude/settings.json 写到上一级
# （目标项目根目录），hook 命令里自动带上子目录路径前缀（例如
# ${CLAUDE_PROJECT_DIR}/c-memory/.venv/bin/python3），这样整个 c-memory 相关的
# 文件（hooks/、memory_lib/、memory/、.venv/、.env）都自包含在这一个子目录里，
# 不会跟目标项目自己的文件混在一起，可以整体删除/更新/加进 .gitignore。
# 目标项目根目录下只多一个文件：.claude/settings.json（合并写入，不覆盖已有配置）。
#
# sqlite-vec 需要 Python 的 sqlite3 模块在编译时开启 loadable extension，
# 系统自带的 /usr/bin/python3（macOS）通常不支持，可用 PYTHON_BIN 指定替代解释器：
#   PYTHON_BIN=/opt/homebrew/bin/python3 ./install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SUBDIR_NAME="$(basename "$SCRIPT_DIR")"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "== c-memory 首次安装（子目录：${SCRIPT_DIR}，目标项目根目录：${PROJECT_ROOT}） =="

if [ ! -d ".venv" ]; then
  if ! "$PYTHON_BIN" -c "import sqlite3; sqlite3.connect(':memory:').enable_load_extension(True)" 2>/dev/null; then
    echo "错误：$PYTHON_BIN 的 sqlite3 模块不支持 loadable extension（memory_lib/vector_cache.py 依赖的" >&2
    echo "sqlite-vec 需要这个能力），macOS 系统自带的 /usr/bin/python3 通常不支持。" >&2
    echo "请改用 conda/homebrew 等提供的 Python 重跑，例如：" >&2
    echo "  PYTHON_BIN=/opt/homebrew/bin/python3 ./install.sh" >&2
    exit 1
  fi
  echo "-- 创建虚拟环境 .venv"
  "$PYTHON_BIN" -m venv --copies .venv
else
  echo "-- .venv 已存在，跳过创建"
fi

echo "-- 安装依赖"
.venv/bin/pip install -q -r requirements.txt

echo "-- 初始化数据目录"
mkdir -p memory/instincts/archive memory/memories memory/rules

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "-- 已生成 .env（全部变量可选，不填自动降级为规则匹配 + TF-IDF 模式）"
else
  echo "-- .env 已存在，跳过"
fi

mkdir -p "$PROJECT_ROOT/.claude"
echo "-- 合并 hooks 配置到 ${PROJECT_ROOT}/.claude/settings.json（不覆盖已有配置）"
.venv/bin/python3 merge_settings.py settings.template.json "$PROJECT_ROOT/.claude/settings.json" "$SUBDIR_NAME"

echo "== 安装完成 =="
echo "Hook 命令统一指向 \${CLAUDE_PROJECT_DIR}/${SUBDIR_NAME}/.venv/bin/python3，即本子目录下的 .venv。"
echo "c-memory 相关文件都自包含在 ${SCRIPT_DIR} 这一个子目录里。"
echo "需要更精确的语义分析/召回时，去 .env 里填 DEEPSEEK_API_KEY / ARK_API_KEY。"
