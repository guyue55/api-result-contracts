# 规范依据与取舍

核验日期：2026-10-25。只采用适用规范，不把工具文件数量当作成熟度。

| 依据 | 采用 | 边界 |
|---|---|---|
| [GitHub 模板仓库](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository) | 新项目获得文件结构和独立历史 | 不会自动继承远程设置或验收 |
| [AGENTS.md 开放格式](https://agents.md/) | 一处明确上下文、命令、风格与安全约束 | 不保证所有宿主发现，不是沙箱 |
| [GitHub Actions 安全](https://docs.github.com/en/actions/reference/security/secure-use) | 最小权限、完整 SHA 固定、无特权 PR 源码执行 | 仍需核验依赖来源和维护更新 |
| [Python 打包指南](https://packaging.python.org/en/latest/tutorials/packaging-projects/) | 库采用 src 布局、pyproject、SPDX 许可、隔离构建与安装 | 通用仓库模板不强制应用语言 |
| [安全政策](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/add-security-policy) | 支持版本、私密报告与披露边界 | 不虚构响应 SLA 或赏金 |
| [GitHub 发布不可变性](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes) | 不移已发布 Tag、不覆盖资产，下载核对摘要和来源 | 文档规则与远端保护分别核验 |

借鉴原通用办公模板的已验证工作流经验；不复制原有服务、数据、身份系统、业务配置或历史。Apache-2.0 来源与 NOTICE 保留。统一包装是本库的设计契约，不声称是 RFC 定义的唯一标准；HTTP 状态、JSON 和上游协议语义仍各自遵守。
