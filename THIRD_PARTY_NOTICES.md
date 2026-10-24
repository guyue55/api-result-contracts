# 第三方许可

自有代码按 Apache-2.0 提供；不替代第三方许可。实际依赖版本以 uv.lock 为准；安装分发包中的 dist-info/licenses 等材料保留各上游原文。

- 核心依赖 Pydantic 及 pydantic-core 声明 MIT。
- 可选 FastAPI 和 MCP SDK 声明 MIT；HTTPX、HTTP Core、Starlette 声明 BSD 类许可。
- 依赖中的 certifi 声明 MPL-2.0，不能由本库许可证替代；其他传递依赖与构建工具分别按上游条款使用。

本仓库不分发数据库、身份产品、浏览器或办公服务容器。wheel／sdist 不打包第三方依赖二进制；实际将依赖组合交付时应核查各分发包许可。本清单不构成完整法律认证。
