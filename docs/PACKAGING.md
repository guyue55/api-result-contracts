# Python 库维护与发行验收

## 范围与兼容

本库以 PEP 517/518 构建、PEP 621 元数据、PEP 639 许可、内联类型和 py.typed 分发。Hatchling 是构建后端；普通消费者使用 pip 等工具即可安装，不要求 uv、Git、开发锁文件或项目脚本。元数据的关键字与分类用于发现，不代替安装范围。

唯一手写版本源是 VERSION，Hatchling 正则读取，源码与安装元数据均需一致；sdist 包含 VERSION，不读取 Git 或在构建时导入运行库。运行时查询 `importlib.metadata.version("api-result-contracts")`，不强制另加 __version__。

Python 下限 3.13；持续验证 CPython3.13/3.14 的 Linux、Windows、macOS。没有已知不兼容时不增加预测性版本上限；允许解析未来版本不表示已经测试。未承诺其他解释器或所有未来平台。

核心只依赖 Pydantic；FastAPI、HTTPX、MCP 是独立 extras。依赖下限为支持承诺的一部分，调整前需真实测试；不无依据降低下限。uv.lock 用于开发/CI 重现，发行物使用依赖范围，应用自行锁定。

## 持续检查

源码门禁：仓库与暂存树卫生、提交规范、Ruff、格式、Mypy、pytest importlib 模式。保留根路径供示例使用，未将 src 加入测试搜索路径绕过安装。

构建门禁：uv build 生成 sdist 并从其构建 wheel；Twine strict 检查说明渲染。check_distributions.py 检查实际wheel元数据及依赖、独立extras声明、类型标记、通用码表、源码一致性、许可、成员路径、重复成员及RECORD逐文件摘要。

scripts/check_install.py 默认验证 core、fastapi、httpx、mcp、all 五个隔离环境。先验证发行元数据、类型标记和资源可读，单独extra执行适配行为探针；core确认未安装框架。all 环境只复制功能测试、示例与类型消费者，绝不复制src或开发项目配置，然后运行完整功能测试、Mypy消费检查和pip check。真实HTTP回环属于功能测试；HTTPX单项探针使用MockTransport，仅证明独立适配逻辑，不冒称远程网络验收。

`--minimum` 按元数据各直接依赖下限生成精确约束，对相同五种安装组合验证，并在安装测试工具时继续保留约束，防止测试工具悄悄升级被测依赖。传递依赖仍由解析器选择兼容版本；这不叫“所有传递依赖的历史最低组合”。当前函数不支持复杂条件/URL/嵌套extra，遇到时显式失败，维护者应扩展测试逻辑而不是跳过。

`--rebuild-sdist` 在临时目录用 sdist 和声明最低 Hatchling 构建，既不依赖.git也不依赖开发安装，然后检查重建物并再次安装运行 all 功能与类型测试。两份wheel各自完整验证RECORD；源码、资源、许可、依赖和业务元数据必须一致。仅允许生成器版本、已知 Metadata-Version 2.4/2.5 声明和据此变化的RECORD不同，不要求不同后端生成字节级相同ZIP。

CI 在三平台两Python版本执行源码、最新可解析安装及sdist检查；Linux同时执行最低直接依赖。源码与正式发布物的验收结果分别记录；CI中执行的是候选，不能冒称注册表生产安装。

## 本地与发布候选

完整命令见 [贡献指南](../CONTRIBUTING.md)。候选构建要求源码已提交且干净；使用 scripts/release.py build。然后：

```sh
uv run twine check --strict <候选wheel> <候选sdist>
uv run python scripts/check_install.py --wheel-dir <候选目录> --rebuild-sdist
uv run python scripts/check_install.py --wheel-dir <候选目录> --minimum
uv run python scripts/release.py verify <候选目录> --commit <最终main提交>
```

最终main对应CI通过后才准备Tag与发布；不重用合并前提交的来源清单。已发布v1.0.0不改动，v1.0.1依流程另发。候选检查通过不等于已发布；具体流程见 [操作手册](OPERATIONS.md)。

## PyPI 边界

本轮交付 GitHub 发行候选，不上传 PyPI/TestPyPI，不引入长期token或无审批Tag上传流程。若后续授权上架，需配置PyPI项目与GitHub环境；采用OIDC，构建任务无上传身份，上传任务只接收已验证制品。先验证TestPyPI流程，再验证正式索引匿名安装；不得声称GitHub发版等于pip install包名已经可用。

标准依据与对照结论见 [专项评审](PYTHON_PACKAGING_REVIEW.md)。不添加setup.py、setuptools专属MANIFEST.in、第二套hooks或不必要的发布框架。
