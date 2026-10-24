"""独立临时环境验证core-only和可选适配；不安装全局工具、不获取凭证。"""

import argparse
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    subprocess.run(args, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    wheels = list(args.wheel_dir.glob("api_result_contracts-*-py3-none-any.whl"))
    if len(wheels) != 1:
        raise RuntimeError("需要目录中恰好一个本库轮包")
    wheel = wheels[0].resolve()
    for extra in (False, True):
        with tempfile.TemporaryDirectory(prefix="contracts-install-") as directory:
            venv = Path(directory) / "venv"
            run(["uv", "venv", str(venv)])
            python = venv / (
                "Scripts/python.exe" if __import__("os").name == "nt" else "bin/python"
            )
            run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(python),
                    str(wheel) + ("[fastapi,httpx,mcp]" if extra else ""),
                ]
            )
            code = """import importlib.util, importlib.metadata
from pathlib import Path
from api_result_contracts import Meta, Success, encode
assert importlib.metadata.version("api-result-contracts") == "VERSION_PLACEHOLDER"
assert b'"code":0' in encode(Success[int](data=12, meta=Meta(trace_id="probe")), Success[int])
dist = importlib.metadata.distribution("api-result-contracts")
files = [str(p) for p in dist.files]
assert any(p.endswith("LICENSE") for p in files) and any(p.endswith("NOTICE") for p in files)
""".replace("VERSION_PLACEHOLDER", (ROOT / "VERSION").read_text(encoding="utf-8").strip())
            if extra:
                code += "from api_result_contracts.integrations import fastapi, httpx, mcp\n"
            else:
                code += "assert all(importlib.util.find_spec(n) is None for n in ('fastapi', 'httpx', 'mcp'))\n"
            run([str(python), "-I", "-c", code])
            print("ISOLATED_INSTALL_OK", "all-extras" if extra else "core-only")


if __name__ == "__main__":
    main()
