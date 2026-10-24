"""显式构建和离线验证发布资产；不创建Tag、不上传、不部署。"""

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path

from check import EXCLUDED, ROOT, archive_path, git, sources, validate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive_check(path):
    if path.suffix in {".whl", ".zip"}:
        with zipfile.ZipFile(path) as archive:
            members = [
                (i.filename, i.file_size, (i.external_attr >> 16) & 0o170000 == 0o120000)
                for i in archive.infolist()
            ]
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            members = [
                (i.name, i.size, not (i.isfile() or i.isdir())) for i in archive.getmembers()
            ]
    else:
        return
    for name, size, special in members:
        p = archive_path(name)
        if special or size > 20 * 1024 * 1024:
            raise ValueError("归档存在危险成员")
        if (
            any(
                part in EXCLUDED | {"credentials", "secrets", "storage_data", "runs", "logs"}
                for part in p.parts
            )
            or (p.name.startswith(".env") and p.name != ".env.example")
            or p.suffix in {".pem", ".key", ".db", ".pyc", ".p12", ".pfx"}
        ):
            raise ValueError("归档包含运行或秘密文件")


def expected(name, version, kind):
    result = {
        f"{name}-source-{version}.zip",
        "RELEASE_NOTES.md",
        "release-manifest.json",
        "SHA256SUMS",
    }
    if kind == "library":
        package = name.replace("-", "_")
        result |= {f"{package}-{version}-py3-none-any.whl", f"{package}-{version}.tar.gz"}
    return result


def verify(folder, commit=None):
    if (
        folder.is_symlink()
        or not folder.is_dir()
        or any(p.is_symlink() or not p.is_file() for p in folder.iterdir())
    ):
        raise ValueError("资产目录无效")
    data = json.loads((folder / "release-manifest.json").read_text(encoding="utf-8"))
    name, version, kind = data["name"], data["version"], data["kind"]
    if (
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
        or kind not in {"library", "template"}
    ):
        raise ValueError("清单标识无效")
    if data.get("tag") != "v" + version:
        raise ValueError("Tag与版本不一致")
    if not re.fullmatch(r"[0-9a-f]{40}", data["source_commit"]) or (
        commit and commit != data["source_commit"]
    ):
        raise ValueError("来源提交不匹配")
    names = {p.name for p in folder.iterdir()}
    if names != expected(name, version, kind):
        raise ValueError("发布资产不符合白名单")
    checksums = {}
    for line in (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        value, filename = line.split("  ", 1)
        if filename in checksums or not re.fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("摘要清单无效")
        checksums[filename] = value
    if checksums.keys() != names - {"SHA256SUMS"}:
        raise ValueError("摘要覆盖不完整")
    for filename, value in checksums.items():
        if digest(folder / filename) != value:
            raise ValueError("制品摘要不匹配")
        archive_check(folder / filename)
    if data["artifacts"] != {
        n: checksums[n] for n in names - {"SHA256SUMS", "release-manifest.json"}
    }:
        raise ValueError("来源与摘要清单不一致")
    print("RELEASE_VERIFIED", name, version, data["source_commit"], len(names))
    return data


def build(folder):
    config, version = validate(dict(sources(staged=True)))
    if git("status", "--porcelain").strip():
        raise ValueError("发布源码必须已提交且干净")
    folder.mkdir(parents=True, exist_ok=False)
    sha = git("rev-parse", "HEAD").decode().strip()
    name, kind = config["name"], config["kind"]
    archive = git("archive", "--format=zip", "--prefix=" + name + "-" + version + "/", sha)
    (folder / f"{name}-source-{version}.zip").write_bytes(archive)
    if kind == "library":
        subprocess.run(["uv", "build", "--out-dir", str(folder)], cwd=ROOT, check=True)
    marker = folder / ".gitignore"
    if marker.exists():
        # uv build 自动生成的输出目录标记，不属于发行资产。
        if marker.read_bytes() not in {b"*", b"*\n"}:
            raise ValueError("构建产生了未知忽略标记")
        marker.unlink()
    (folder / "RELEASE_NOTES.md").write_bytes(
        (ROOT / "releases" / ("v" + version + ".md")).read_bytes()
    )
    files = {p.name: digest(p) for p in sorted(folder.iterdir())}
    manifest = {
        "name": name,
        "kind": kind,
        "version": version,
        "tag": "v" + version,
        "source_commit": sha,
        "artifacts": files,
    }
    (folder / "release-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (folder / "SHA256SUMS").write_text(
        "".join(f"{digest(p)}  {p.name}\n" for p in sorted(folder.iterdir())),
        encoding="utf-8",
        newline="\n",
    )
    verify(folder, sha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    make = actions.add_parser("build")
    make.add_argument("--output", type=Path, required=True)
    check = actions.add_parser("verify")
    check.add_argument("directory", type=Path)
    check.add_argument("--commit")
    args = parser.parse_args()
    if args.action == "build":
        build(args.output.resolve())
    else:
        verify(args.directory.resolve(), args.commit)


if __name__ == "__main__":
    main()
