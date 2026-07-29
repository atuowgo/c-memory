# 构建 c-memory 发布包到 dist/c-memory/：包含运行所需配置、脚本依赖的源码/依赖清单、
# 以及首次使用时执行的 install.sh。不打包 memory/ 下积累的实际数据（instincts/
# memories/rules 是本项目自己的运行痕迹，不属于"发布包"）、不打包 .env（含真实密钥）、
# tests/、docs/（开发态内容，运行不需要）。
#
# 产物已经是自包含的部署单元 dist/c-memory/：部署时直接把这一个目录整体拷进目标项目
# 根目录即可（cp -R dist/c-memory target-project/），不需要用户手动改名/加子目录——
# 这样 hooks/memory_lib/memory/.venv 都留在同一个子目录里，不会跟目标项目自己的
# 文件混在一起。目标项目根目录只多一个文件：.claude/settings.json（由 install.sh
# 调用 merge_settings.py 合并写入，自动带上子目录路径前缀，见 scripts/install.sh）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

DIST_DIR="$REPO_ROOT/dist"
PACKAGE_NAME="c-memory"
PACKAGE_DIR="$DIST_DIR/$PACKAGE_NAME"

echo "== 构建 c-memory 发布包 -> $PACKAGE_DIR =="
rm -rf "$DIST_DIR"
mkdir -p "$PACKAGE_DIR"

echo "-- 拷贝源码：hooks/、memory_lib/"
mkdir -p "$PACKAGE_DIR/hooks" "$PACKAGE_DIR/memory_lib"
cp -R hooks/. "$PACKAGE_DIR/hooks/"
cp -R memory_lib/. "$PACKAGE_DIR/memory_lib/"
find "$PACKAGE_DIR" -type d -name "__pycache__" -exec rm -rf {} +
find "$PACKAGE_DIR" -type f -name "*.pyc" -delete

echo "-- 拷贝运行配置：settings.template.json、.env.example"
# 注意：不叫 .claude/settings.json，也不放进 .claude/ 目录——如果目标项目已经有
# 自己的 .claude/settings.json（比如配了其他 hooks），整体拷贝 c-memory/ 时
# 同名文件会被直接覆盖，等 install.sh 跑起来才发现已经来不及了。这里保留成一份
# 独立的模板文件，实际写入 .claude/settings.json 的动作由 install.sh 调用
# merge_settings.py 做真正的合并，而不是覆盖。
cp .claude/settings.json "$PACKAGE_DIR/settings.template.json"
cp .env.example "$PACKAGE_DIR/.env.example"
cp scripts/merge_settings.py "$PACKAGE_DIR/merge_settings.py"

echo "-- 拷贝依赖清单：requirements.txt"
cp requirements.txt "$PACKAGE_DIR/requirements.txt"

echo "-- 拷贝说明文档：README.md"
cp README.md "$PACKAGE_DIR/README.md"

echo "-- 拷贝首次使用安装脚本：install.sh"
cp scripts/install.sh "$PACKAGE_DIR/install.sh"
chmod +x "$PACKAGE_DIR/install.sh"

echo "== 构建完成，产物清单 =="
find "$PACKAGE_DIR" -type f | sort
