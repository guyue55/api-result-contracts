"""隔离验收发行包：单独extras、实际功能／类型消费、最低依赖与sdist重建。"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from check_distributions import compare_wheels, inspect_wheel
from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "core": (),
    "fastapi": ("fastapi",),
    "httpx": ("httpx",),
    "mcp": ("mcp",),
    "all": ("fastapi", "httpx", "mcp"),
}

PROBES = {
    "fastapi": """
import asyncio
from fastapi import FastAPI
from api_result_contracts.integrations.fastapi import ContractRouter, install_fastapi
app = FastAPI()
registry = make_registry("probe")
router = ContractRouter(registry=registry, prefix="/api/v2")
@router.get("/probe", data_model=int)
async def endpoint(): return 12
app.include_router(router)
install_fastapi(app, registry=registry)
assert "/api/v2/probe" in app.openapi()["paths"]
async def exercise():
    events = []
    async def receive(): return {"type": "http.request", "body": b"", "more_body": False}
    async def send(event): events.append(event)
    await app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
               "method": "GET", "scheme": "http", "path": "/api/v2/probe",
               "raw_path": b"/api/v2/probe", "query_string": b"", "headers": [],
               "server": ("probe", 80), "client": ("probe", 1), "root_path": ""}, receive, send)
    assert events[0]["status"] == 200
    assert json.loads(b"".join(e.get("body", b"") for e in events))["data"] == 12
asyncio.run(exercise())
""",
    "httpx": """
import httpx
from api_result_contracts.integrations.httpx import request_json
body = encode(Success[int](data=12, meta=Meta(trace_id="probe")), Success[int])
with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body,
                  headers={"Content-Type": "application/json"}))) as client:
    assert request_json(client, "GET", "http://probe", int, registry=make_registry("probe")).data == 12
""",
    "mcp": """
from api_result_contracts.integrations.mcp import tool_success, output_schema
value = tool_success(12, int, Meta(trace_id="probe"))
assert value.structured_content["data"] == 12
assert json.loads(value.content[0].text) == value.structured_content
assert output_schema(int)["type"] == "object"
""",
}


def run(args, cwd):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def minimum_constraints(requirements):
    result = []
    for text in requirements:
        requirement = Requirement(text)
        # 当前元数据只有无标记的版本区间；复杂声明须先设计，不悄悄放过。
        if requirement.marker or requirement.url or requirement.extras:
            raise ValueError("最低依赖检查尚不接受标记、URL或嵌套extra")
        bounds = [s.version for s in requirement.specifier if s.operator in {">=", "=="}]
        if not bounds:
            raise ValueError("依赖需要明确下限：" + requirement.name)
        lower = max(bounds, key=Version)
        if not requirement.specifier.contains(lower):
            raise ValueError("最低依赖声明不一致")
        result.append(requirement.name + "==" + lower)
    return result


def probe(python, cwd, extras, version):
    code = f"""import importlib.metadata, importlib.resources, importlib.util, json, sys
from pathlib import Path
import api_result_contracts as package
from api_result_contracts import Meta, Success, encode, make_registry
assert importlib.metadata.version("api-result-contracts") == {version!r}
assert b'"code":0' in encode(Success[int](data=12, meta=Meta(trace_id="probe")), Success[int])
assert make_registry("probe").export()
assert json.loads(importlib.resources.files(package).joinpath("core_codes.json").read_text(encoding="utf-8"))
assert importlib.resources.files(package).joinpath("py.typed").is_file()
assert Path(package.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
"""
    if not extras:
        code += (
            "assert all(importlib.util.find_spec(n) is None for n in ('fastapi','httpx','mcp'))\n"
        )
    for extra in extras:
        code += f"from api_result_contracts.integrations import {extra}\n" + PROBES[extra]
    run([python, "-I", "-c", code], cwd)


def functional_tests(python, folder, constraints):
    # 仅拷贝测试／示例／类型消费者，不拷贝src或pyproject，杜绝源码遮蔽发行物。
    suite = folder / "consumer"
    suite.mkdir()
    (suite / "tests").mkdir()
    for source in (ROOT / "tests").glob("test_*.py"):
        if source.name not in {"test_repository.py", "test_packaging.py"}:
            shutil.copy2(source, suite / "tests" / source.name)
    shutil.copytree(
        ROOT / "examples", suite / "examples", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copy2(ROOT / "tests/typing/consumer.py", suite / "consumer.py")
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tools = [
        s
        for s in config["dependency-groups"]["dev"]
        if Requirement(s).name in {"pytest", "mypy", "uvicorn"}
    ]
    run(["uv", "pip", "install", "--python", python, *constraints, *tools], suite)
    run([python, "-m", "pytest", "--import-mode=importlib", "-q", "tests"], suite)
    run([python, "-m", "mypy", "consumer.py", "--check-untyped-defs"], suite)
    run(["uv", "pip", "check", "--python", python], suite)


def install_profile(wheel, name, minimum):
    extras = PROFILES[name]
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    with tempfile.TemporaryDirectory(prefix="contracts-install-") as directory:
        folder = Path(directory)
        venv = folder / "venv"
        run(["uv", "venv", "--python", sys.executable, venv], folder)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        constraints = []
        if minimum:
            requirements = config["dependencies"] + [
                r for e in extras for r in config["optional-dependencies"][e]
            ]
            path = folder / "minimum.txt"
            path.write_text("\n".join(minimum_constraints(requirements)) + "\n", encoding="utf-8")
            constraints = ["--constraint", str(path)]
        spec = str(wheel) + ("[" + ",".join(extras) + "]" if extras else "")
        run(["uv", "pip", "install", "--python", python, *constraints, spec], folder)
        probe(python, folder, extras, version)
        if name == "all":
            functional_tests(python, folder, constraints)
        print("ISOLATED_INSTALL_OK", name, "minimum" if minimum else "latest", flush=True)


def rebuild(sdist, wheel):
    with tempfile.TemporaryDirectory(prefix="contracts-sdist-") as directory:
        folder = Path(directory)
        # sdist输入由uv在临时目录解包并隔离构建，既无.git也无需开发工作区。
        constraints = folder / "build-constraints.txt"
        requirements = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
            "build-system"
        ]["requires"]
        constraints.write_text(
            "\n".join(minimum_constraints(requirements)) + "\n", encoding="utf-8"
        )
        run(
            [
                "uv",
                "build",
                "--wheel",
                sdist,
                "--build-constraints",
                constraints,
                "--python",
                sys.executable,
                "--out-dir",
                folder / "rebuilt",
            ],
            folder,
        )
        rebuilt = next((folder / "rebuilt").glob("*.whl"))
        compare_wheels(wheel, rebuilt)
        install_profile(rebuilt, "all", False)
        print("SDIST_MINIMUM_BACKEND_REBUILD_OK", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--profiles", choices=PROFILES, nargs="+", default=list(PROFILES))
    parser.add_argument("--minimum", action="store_true")
    parser.add_argument("--rebuild-sdist", action="store_true")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    wheel = args.wheel_dir.resolve() / f"api_result_contracts-{version}-py3-none-any.whl"
    inspect_wheel(wheel)
    for name in args.profiles:
        install_profile(wheel, name, args.minimum)
    if args.rebuild_sdist:
        rebuild(wheel.with_name(f"api_result_contracts-{version}.tar.gz"), wheel)


if __name__ == "__main__":
    main()
