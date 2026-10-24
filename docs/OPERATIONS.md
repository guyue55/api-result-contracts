# 常用操作与发版

## 日常

检查工作目录、Git 状态与 remote；阅读相关文档，做内聚修改。运行 CONTRIBUTING.md 的门禁，核对暂存清单和中文提交格式。main 走 PR；分支保护设置在 GitHub，不会因复制模板自动继承。

## v1.0.0 及后续发布

1. 明确版本与兼容范围，更新 VERSION、CHANGELOG、pyproject.toml 和 uv.lock；releases/v版本.md。版本、协议版本与数据结构版本分别评估。
2. 本地完整检查；提交源代码，审查并合并 main。核对最终 main SHA 的远程 CI，不使用合并前旧制品。
3. 在干净且已提交的源码执行 `uv run python scripts/release.py build --output dist/v版本`。候选与 source_commit、版本、SHA256SUMS 一致，目录必须不存在。
4. 检查来源、许可、白名单、包内容和安装／生成体验。脚本不自动创建 Tag 或发布。
5. 对同一 SHA 创建附注 Tag：`git tag -a v版本 <SHA> -m 'release(版本): 中文说明'`，仅推确切 Tag。发布权限须覆盖本次范围。
6. 用 `gh release create v版本 --verify-tag --draft --notes-file releases/v版本.md` 创建草稿，按明确白名单上传候选；不要使用未经核验的 dist 通配符或覆盖上传。
7. 审核草稿后正式发布；从公开 Release 下载到新目录，运行 `python3 scripts/release.py verify <目录> --commit <SHA>`；校验来源与每个资产摘要。

CI 只运行检查和构建，不自动部署或向 PyPI 传包。当前交付 Python wheel／sdist 和源码，不需要运行镜像。PyPI 发布需另设可信发布者与环境审批，不能声称已经上架。 Tag push 不触发未经批准的部署。

已发布版本不能移动 Tag／覆盖同名资产，修复发补丁。代码回退用审核后的 revert 和检查；不对共享 main 使用 reset／force push，数据回滚另行验证。

## 创建新项目／依赖升级

独立库保持语义版本和导入路径稳定。可选适配更新需同时验证 core-only 和 all-extras 安装；引入破坏性协议变更前先明确迁移。原办公模板仍固定自己的源码副本，未自动切换为本仓库发行包，避免影响已发布模板。

依赖升级应读取上游变更并审阅 lock 差异，先验证再合并。不要为了审计绿灯忽略漏洞；不适用项需有依据。
