"""核查实际发行物的元数据、类型与资源、文件摘要及源码包重建结果。"""

import base64
import csv
import hashlib
import io
import tomllib
import zipfile
from email.parser import BytesParser

from check import ROOT
from packaging.requirements import Requirement
from release import archive_check


def inspect_wheel(path):
    archive_check(path)
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    prefix = "api_result_contracts"
    info = f"{prefix}-{version}.dist-info"
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("wheel含重复成员")
        metadata = BytesParser().parsebytes(archive.read(f"{info}/METADATA"))
        if (
            metadata["Name"] != config["name"]
            or metadata["Version"] != version
            or metadata["Requires-Python"] != config["requires-python"]
            or metadata["License-Expression"] != config["license"]
            or set(metadata.get_all("Provides-Extra", [])) != set(config["optional-dependencies"])
        ):
            raise ValueError("发行元数据与项目声明不一致")
        expected_dependencies = {str(Requirement(d)) for d in config["dependencies"]}
        expected_dependencies.update(
            str(Requirement(d + f'; extra == "{extra}"'))
            for extra, dependencies in config["optional-dependencies"].items()
            for d in dependencies
        )
        if (
            metadata["Metadata-Version"] not in {"2.4", "2.5"}
            or {str(Requirement(d)) for d in metadata.get_all("Requires-Dist", [])}
            != expected_dependencies
        ):
            raise ValueError("发行依赖或元数据格式与声明不一致")
        required = {
            f"{prefix}/py.typed",
            f"{prefix}/core_codes.json",
            f"{info}/licenses/LICENSE",
            f"{info}/licenses/NOTICE",
            f"{info}/WHEEL",
            f"{info}/RECORD",
        }
        if not required.issubset(names):
            raise ValueError("wheel缺少类型、资源或许可文件")
        if any(not n.startswith((prefix + "/", info + "/")) for n in names):
            raise ValueError("wheel混入无关顶层文件")
        for source in (ROOT / "src" / prefix).rglob("*"):
            if source.is_file() and "__pycache__" not in source.parts:
                name = source.relative_to(ROOT / "src").as_posix()
                if archive.read(name) != source.read_bytes():
                    raise ValueError("wheel与源码不一致：" + name)
        rows = list(csv.reader(io.StringIO(archive.read(f"{info}/RECORD").decode())))
        if len(rows) != len(names) or {row[0] for row in rows} != set(names):
            raise ValueError("RECORD未完整覆盖wheel")
        for name, digest, size in rows:
            if name == f"{info}/RECORD":
                if digest or size:
                    raise ValueError("RECORD不能自签名")
                continue
            data = archive.read(name)
            expected = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
            if digest != "sha256=" + expected.decode() or size != str(len(data)):
                raise ValueError("wheel成员摘要不符：" + name)
        return {name: archive.read(name) for name in names}


def compare_wheels(first, second):
    # 各自先完整验证RECORD。仅容许已知后端差异，不忽略业务源码或依赖。
    def normalized(path):
        result = inspect_wheel(path)
        for name in list(result):
            if name.endswith(".dist-info/RECORD"):
                del result[name]
            elif name.endswith(".dist-info/WHEEL"):
                result[name] = b"\n".join(
                    line for line in result[name].splitlines() if not line.startswith(b"Generator:")
                )
            elif name.endswith(".dist-info/METADATA"):
                # 只归一化首行版本声明，README正文中的同名文本仍必须一致。
                header, separator, body = result[name].partition(b"\n")
                if not separator or not header.startswith(b"Metadata-Version:"):
                    raise ValueError("METADATA首行不是已知格式")
                result[name] = body
        return result

    if normalized(first) != normalized(second):
        raise ValueError("sdist重建wheel与原wheel内容不一致")
