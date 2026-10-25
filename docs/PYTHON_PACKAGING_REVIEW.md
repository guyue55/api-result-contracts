# Python 第三方库规范与工程评审

核查日期：2026-10-25。对象为已发布 v1.0.0，提交 `fa94ecba8b1ef4384f64b3a2f62d838c13c3d7df`。本轮仅研究与文档，不修改发行物、运行代码或启用注册表上传。

## 1. 定位与结论

本项目是可安装、供其他 Python 项目导入的第三方库。GitHub Release 是有效分发渠道；发布到 PyPI 不是成为库的必要条件，但有助于标准依赖安装。仓库、包格式合规、测试通过、注册表上架是不同结论。

现有 src 布局、pyproject、Hatchling、wheel/sdist、依赖分层、SPDX 许可与 py.typed 已形成合适基础。需要改进的是消费方兼容策略及持续发布门禁，无需换后端、引入大框架或照搬 SDK 模板。

## 2. 标准与惯例分开

| 范围 | 依据 | 适用判断 |
|---|---|---|
| 构建入口与元数据 | [pyproject 指南](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)、[现代构建](https://packaging.python.org/en/latest/guides/modernize-setup-py-project/) | 保留 PEP 517/518/621 方式；无需为现代库补 setup.py 或 setup.cfg |
| 许可 | 同上，PEP 639 | SPDX 表达式及 license-files；实际发行物中须含对应许可与 NOTICE |
| 目录与安装 | [src 布局](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) | src 是适合本库的工程选择，不是所有 Python 项目的强制规则 |
| 版本 | [版本单一来源](https://packaging.python.org/en/latest/discussions/single-source-version/) | 单源优先；多个来源加一致性断言也被官方指南认可，并非天然违规 |
| 类型分发 | [类型规范](https://typing.python.org/en/latest/spec/distributing.html) | 内联类型库携带 py.typed；稳定公共入口与内部模块的边界需明确 |
| 依赖 | [库依赖与环境要求](https://packaging.python.org/en/latest/discussions/install-requires-vs-requirements/) | 发行元数据描述运行需求；uv.lock 重现开发环境，不强制下游使用相同锁文件 |
| Python 支持 | [Python 版本声明](https://packaging.python.org/en/latest/guides/dropping-older-python-versions/) | 下限基于真实需求；避免仅因未来版本未测试就增加上限 |
| 测试 | [pytest 建议](https://pytest.org/en/stable/explanation/goodpractices.html) | 推荐 importlib 模式；安装发行包后测试，避免路径遮蔽 |
| README 发布检查 | [Twine check](https://twine.readthedocs.io/en/stable/internal/twine.commands.check.html) | 检查说明文档渲染，strict 将警告视为错误；不能替代功能、完整结构或安全检查 |
| 注册表发布 | [PyPI 发布](https://docs.pypi.org/publishing/publishing-to-pypi/)、[信任配置](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)、[安全模型](https://docs.pypi.org/trusted-publishers/security-model/) | 优先 OIDC，构建和发布隔离，发布环境保护；可信身份不等于代码安全 |

## 3. 当前库逐项核查

| 项目 | 已有事实 | 判断与建议 |
|---|---|---|
| 布局与后端 | src/api_result_contracts，Hatchling | 保留；setuptools 也合法，无需因模板不同迁移 |
| 元数据 | name/version/description/readme/requires-python/URLs/license | 基本完整；增加有意义的 keywords、classifiers、维护者名称；不虚构邮箱、稳定性认证或平台支持 |
| 版本来源 | VERSION 与 pyproject 各保存一次，check.py 强校验 | 当前有效；后续可由 Hatchling 从 VERSION 读取，减少重复；不得因改为动态版本破坏 check.py 或 sdist 离线构建 |
| Python 范围 | >=3.13,<3.15；CI 3.13/3.14 | 建议无已知不兼容时移除预测性上限；最低支持版本暂不降低，测试承诺与可安装范围分别说明 |
| 运行依赖 | 核心 Pydantic，三个可选 extras | 合理；不要将开发工具变成普通消费者依赖 |
| 依赖范围 | Pydantic、FastAPI、HTTPX、MCP 设置边界 | 不机械放开或封顶；确认最低版本是否由 API 需要决定，并验证最低直接依赖与最新可解析组合；锁定 CI 通过不证明所有允许组合通过 |
| 类型与资源 | py.typed、公共 __all__、core_codes.json | 已打包；后续将安装后的资源读取及类型消费检查固化为 CI |
| pytest 导入 | pythonpath=["."]，默认导入模式，示例从根目录导入 | 目前不等于 src 包直接遮蔽，但可采用 importlib；调整前处理 examples 与治理脚本的测试导入，不能直接删路径配置求简洁 |
| 功能测试 | 51 项源码测试；发布 wheel 独立运行 44 项功能测试通过 | 后者已人工验收，尚未作为完整功能门禁固化到每次 CI；应该补入持续检查 |
| extras 测试 | core-only 与 all-extras 安装探针 | 补三个单独 extra，确认各自可安装、可导入、不会依赖其他 extra 偶然存在 |
| CI 平台 | Linux/Windows × Python3.13/3.14 | 保留；macOS 可补定向任务；未验证的平台不写成已验收 |
| 发行检查 | 资产白名单、摘要、来源、归档路径、隔离安装 | 保留；增加 Twine strict；从 sdist 独立重建/安装、wheel 功能验证及元数据断言 |
| 许可与来源 | LICENSE/NOTICE 实际入包，上游来源保留 | 保留；不要以去品牌为由删除合法署名 |
| 副作用 | 核心未配置 root logger、无 print 输出或主动网络调用 | 保持；没有日志时不必为形式添加 NullHandler；将来记录日志应交由使用方控制 |
| 发布状态 | GitHub v1.0.0，未配置 PyPI 上传 | 不能向用户提供尚未成立的 PyPI 安装承诺；保留轮包与 GitHub 安装说明 |

`__version__`、setup.py、MANIFEST.in、tox/nox、pre-commit 并非每个库必备。运行时版本可使用 importlib.metadata；Hatchling 管理文件选择不需要 setuptools 专属 MANIFEST.in；已有 hooks 与 CI 时不应再无目的重复一套规则。

## 4. 对照账号中的示例

实际仓库为 [guyue55/py_example](https://github.com/guyue55/py_example)，不是 python-example。研究固定到提交 `440e74e87b5967edebc53b82136f2104d8973e8b`。定位是 requests HTTP SDK 模板，并非本库应完整复用的上游契约实现。

值得借鉴：src 布局、发行元数据展示、单一版本来源、开发指南、标准构建命令及 OIDC 发布示例。

不能照搬：

- requests 认证、重试属于 SDK 功能；本库保留可选 HTTPX 适配，不新增请求重试或账号体系。
- 模板 Python3.9 下限源于其自身目标，不能直接作为本库兼容承诺。
- 模板 setuptools>=61 配合字符串 SPDX 许可，最低后端范围过宽；官方说明 setuptools 77.0.0 才引入相关 PEP 639 支持。当前解析出新后端不等于声明的最低后端也成立。
- 模板发布由 Tag 单独触发，流程中未建立依赖质量检查的发布门禁；不能因为它有 publish.yml 就认为更完整。
- 模板的 Twine 描述夸大了验证范围；以官方 Twine check 定义为准。
- PyPI 的 GitHub Trusted Publisher 配置是 owner/repository/workflow/可选 environment；Tag 限制应落实 GitHub 触发规则和环境保护，不能假定 PyPI 配置表单有任意 Tag 通配字段。
- 不沿用“私有仓库必需改为长期 token”这一概括；按提供方实际 OIDC 支持和权限核验，私有与否本身不能代替该判断。
- 模板使用浮动 Action 标签，当前库的完整 SHA 固定和跨平台质量检查值得继续保留。

参考 [setuptools 配置文档](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)。本轮不修改示例仓库。

## 5. 分阶段改进方案

1. 下一次维护：完善有价值的元数据；明确 Python 与依赖支持策略；将 Twine、单独 extras、wheel 功能测试、sdist 重建和资源/类型检查加入门禁。先实施相关验证再扩大版本范围。
2. 简化版本来源可与上述维护一起评估：优先本地静态来源，要求源码压缩包脱离 Git 仍能构建。不为一个版本号额外引入 VCS 插件或运行时读取仓库文件。
3. 如决定上架 PyPI，再建立独立注册表发布流程：main 质量检查通过 → 从最终提交构建并验包 → 同源资产 → 受保护环境审批 → OIDC 上传 → 匿名索引安装复验。构建任务没有上传身份，上传任务不运行项目构建脚本。
4. TestPyPI 只验证上传/元数据/索引安装流程，不能代替正式索引的依赖解析和全链路测试。不要随意混用多个索引让依赖解析越界。
5. 已发布 v1.0.0 不覆盖、不移动 Tag。代码、元数据或构建结果变化应评估新版本；文档研究可以单独 PR，不伪装成现有发行包内容。

## 6. 本轮真实验证和限制

已对正式 v1.0.0 wheel 与 sdist 运行 `uvx --python 3.13 --from twine==7.0.0 twine check --strict <wheel> <sdist>`，二者 PASSED。该命令没有上传包、写入项目依赖或修改全局工具。

前轮独立验收确认 51 项源码测试、独立 wheel 44 项功能测试、隔离安装与远程跨平台 CI；这些是既有版本证据，不是本轮新增门禁已实现的证据。

本轮未执行最低依赖组合、单独 extras 全功能、macOS 远程任务、PyPI 注册/授权/上传。上述标为建议或待验证，不声称已经完成。

## 7. v1.0.1 实施入口

以上为 v1.0.0 基线研究，不随实施抹去历史发现。v1.0.1 已将版本单源、元数据、无预测性Python上限、单独extras、最低直接依赖、发行物内容/摘要、安装后功能和类型消费、最低后端sdist重建纳入代码；Linux/Windows/macOS检查由同一CI执行。实际支持与验收以对应提交CI和 [维护规范](PACKAGING.md) 为准，工作流已配置不等于远程已通过。PyPI上传仍未配置或执行。
