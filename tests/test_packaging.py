"""发行检查的正负验证；合成wheel只在临时目录生成，不依赖网络构建。"""

import base64
import csv
import hashlib
import io
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check
from check_distributions import compare_wheels, inspect_wheel
from check_install import minimum_constraints


def wheel(path, *, metadata_version="2.5", dependency=None, missing=None, corrupt=False):
    root = check.ROOT
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    info = f"api_result_contracts-{version}.dist-info"
    lines = [
        f"Metadata-Version: {metadata_version}",
        "Name: api-result-contracts",
        f"Version: {version}",
        f"Requires-Python: {config['requires-python']}",
        "License-Expression: Apache-2.0",
    ]
    for d in config["dependencies"]:
        lines.append("Requires-Dist: " + (dependency or d))
    for extra, requirements in config["optional-dependencies"].items():
        lines.append("Provides-Extra: " + extra)
        lines.extend(f'Requires-Dist: {d}; extra == "{extra}"' for d in requirements)
    files = {
        p.relative_to(root / "src").as_posix(): p.read_bytes()
        for p in (root / "src/api_result_contracts").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    files.update(
        {
            f"{info}/METADATA": ("\n".join(lines) + "\n\nExample\n").encode(),
            f"{info}/WHEEL": f"Wheel-Version: 1.0\nGenerator: test {metadata_version}\nTag: py3-none-any\n".encode(),
            f"{info}/licenses/LICENSE": (root / "LICENSE").read_bytes(),
            f"{info}/licenses/NOTICE": (root / "NOTICE").read_bytes(),
        }
    )
    if missing:
        del files[missing]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name, data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + digest, len(data)])
    writer.writerow([f"{info}/RECORD", "", ""])
    files[f"{info}/RECORD"] = output.getvalue().encode()
    if corrupt:
        files["api_result_contracts/core_codes.json"] += b" "
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return path


def test_distribution_and_known_backend_metadata_difference(tmp_path):
    current = wheel(tmp_path / "current.whl")
    minimum = wheel(tmp_path / "minimum.whl", metadata_version="2.4")
    inspect_wheel(current)
    compare_wheels(current, minimum)


@pytest.mark.parametrize(
    "change",
    [
        {"dependency": "pydantic>=1"},
        {"missing": "api_result_contracts/py.typed"},
        {"corrupt": True},
        {"metadata_version": "9.0"},
    ],
)
def test_distribution_rejects_invalid_content(tmp_path, change):
    with pytest.raises((ValueError, KeyError)):
        inspect_wheel(wheel(tmp_path / "invalid.whl", **change))


def test_minimum_dependency_bounds():
    assert minimum_constraints(["example>=1.2,<2"]) == ["example==1.2"]
    for value in ["example", "example>1.2", "example>=2,<1", "example[other]>=1"]:
        with pytest.raises(ValueError):
            minimum_constraints([value])


def test_version_must_have_one_build_source():
    files = dict(check.sources())
    files["pyproject.toml"] = files["pyproject.toml"].replace(
        b'path = "VERSION"', b'path = "other"'
    )
    with pytest.raises(ValueError, match="单一版本"):
        check.validate(files)
