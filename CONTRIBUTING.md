# 开发与贡献

先阅读 [AI 与人类协作约定](AGENTS.md) 和 [安全政策](SECURITY.md)。首次贡献通过 Issue 对齐必要范围，修改应内聚，不带入企业专用数据。

## 环境与检查

需要 Python 3.13／3.14 和 uv。运行 `uv sync --frozen --all-extras`，依赖变更用 `uv lock` 后审阅差异。

```sh
uv run python scripts/check.py
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests/typing --check-untyped-defs
```

检查不能替代代码审查。新增行为应有有意义的正负验证；纯文字修改核对链接与说明，不为它启动无关服务。锁定依赖、源码测试、隔离安装、远程 CI 和目标环境证据分开。

## Git 约定

使用短分支（例如 `codex/feature-name`），main 通过 PR 和必需 CI 合并，不绕过保护。提交使用 `type(scope): 中文说明`；type 为 feat、fix、docs、test、refactor、perf、build、ci、chore、revert。GitHub 模板生成的根提交 `Initial commit` 是平台固定文本例外；人工提交仍必须符合中文格式。PR 标题同格式，说明问题、结果、验证及限制。

可选只针对本仓库启用 hooks：

```sh
git config --local core.hooksPath .githooks
```

hooks 不修改全局 Git；Windows 使用 Git for Windows 的 hooks 执行环境及 Python。缺 Python 时停止并提示安装，不绕过。启用后 pre-commit 检查暂存树，commit-msg 校验格式；本机 hooks 可被跳过，所以 CI 同样核查。请勿将合成秘密、日志或个人资料加入 Git。

发布和回退流程见 [操作手册](docs/OPERATIONS.md)。漏洞请私密报告，不在公共 Issue 张贴可用凭证或攻击数据。
