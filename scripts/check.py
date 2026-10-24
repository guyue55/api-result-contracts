"""仓库卫生与中文提交校验；只读，无全局配置、网络或自动修复。"""

import argparse
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "runtime",
    "dist",
    "build",
    "node_modules",
    ".idea",
    ".vscode",
}
REQUIRED = {
    "README.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "LICENSE",
    "NOTICE",
    "VERSION",
    "project.toml",
    "CHANGELOG.md",
    "docs/OPERATIONS.md",
    ".github/workflows/ci.yml",
}
MESSAGE = re.compile(
    r"^(feat|fix|docs|test|refactor|perf|build|ci|chore|revert)\([a-z0-9][a-z0-9_.-]*\)!?: [^\r\n]+$"
)


def archive_path(name):
    # 归档名称是POSIX路径；同时拒绝Windows驱动器与保留名，不依赖执行宿主。
    path = PurePosixPath(name)
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)
    }
    if (
        not path.parts
        or path.is_absolute()
        or PureWindowsPath(name).drive
        or ".." in path.parts
        or "\\" in name
    ):
        raise ValueError("归档存在危险路径")
    if any(
        part.rstrip(" .") != part or ":" in part or part.split(".")[0].upper() in reserved
        for part in path.parts
    ):
        raise ValueError("归档路径不兼容Windows")
    return path


def message_valid(value):
    first = value.splitlines()[0] if value.splitlines() else ""
    return bool(MESSAGE.fullmatch(first) and re.search(r"[\u4e00-\u9fff]", first))


def check_event(event):
    # 只读取PR标题作为数据，不把它插入Shell或执行；推送／手动任务无此字段。
    if "pull_request" in event and not message_valid(event["pull_request"].get("title", "")):
        raise ValueError("PR标题须为type(scope): 中文说明，避免squash产生不合规提交")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sources(staged=False):
    if staged:
        for entry in git("ls-files", "--stage", "-z").split(b"\0"):
            if not entry:
                continue
            meta, name = entry.split(b"\t", 1)
            mode, _, stage = meta.split()
            if mode not in {b"100644", b"100755"} or stage != b"0":
                raise ValueError("暂存树含链接、子模块或未合并项")
            key = name.decode("utf-8")
            yield key, git("show", ":" + key)
    else:
        for folder, directories, filenames in os.walk(ROOT, followlinks=False):
            directories[:] = sorted(
                d for d in directories if d not in EXCLUDED and not d.endswith(".egg-info")
            )
            for name in directories + sorted(filenames):
                path = Path(folder) / name
                if path.is_symlink():
                    raise ValueError("源码不允许本机软链")
                if path.is_file():
                    yield path.relative_to(ROOT).as_posix(), path.read_bytes()


def validate(files):
    missing = REQUIRED - files.keys()
    if missing:
        raise ValueError("缺少必要文件：" + ", ".join(sorted(missing)))
    config = tomllib.loads(files["project.toml"].decode())["project"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", config["name"]):
        raise ValueError("项目名须使用小写kebab-case")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", config["owner"]):
        raise ValueError("GitHub所有者格式无效")
    if config["kind"] not in {"library", "template"}:
        raise ValueError("项目类型无效")
    version = files["VERSION"].decode().strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("VERSION须为稳定语义版本")
    if "releases/v" + version + ".md" not in files:
        raise ValueError("缺少当前版本发布说明")
    if config["kind"] == "library":
        project = tomllib.loads(files["pyproject.toml"].decode())["project"]
        if project["version"] != version or project["name"] != config["name"]:
            raise ValueError("Python包与仓库版本／名称不一致")
    for name, data in files.items():
        p = Path(name)
        if p.name.startswith(".env") and p.name != ".env.example":
            raise ValueError("源码包含环境秘密文件")
        if p.suffix in {".pem", ".key", ".p12", ".pfx", ".db", ".sqlite", ".pyc"} or any(
            part in EXCLUDED | {"credentials", "secrets", "storage_data", "runs", "logs"}
            for part in p.parts
        ):
            raise ValueError("源码包含禁止交付的文件：" + name)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError("源码文件过大，请明确必要性后设计交付")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".pdf"}:
                continue
            raise ValueError("未经允许的二进制源码文件：" + name) from None
        if "\ufffd" in text or re.search(r"/(?:Users|home)/[A-Za-z0-9_.-]+", text):
            raise ValueError("源码含损坏字符或本机个人路径：" + name)
        if p.suffix in {".md", ".py", ".toml", ".sh", ".yml", ".yaml"} and (
            not data.endswith(b"\n")
            or b"\r\n" in data
            or any(line.rstrip() != line for line in text.splitlines())
        ):
            raise ValueError("文件应LF结尾、末尾换行且无行尾空白：" + name)
        if p.suffix == ".md":
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in link or link.startswith(("#", "mailto:")):
                    continue
                target = link.split("#", 1)[0]
                # 相对路径只验证文件，不请求网络；不解析复杂Markdown语法。
                resolved = (ROOT / p.parent / target).resolve()
                if target and (
                    not resolved.is_relative_to(ROOT.resolve())
                    or resolved.relative_to(ROOT.resolve()).as_posix() not in files
                ):
                    raise ValueError("文档文件链接不存在：" + name + " -> " + target)
    return config, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--message-file", type=Path)
    mode.add_argument("--commit-range")
    mode.add_argument("--github-event", action="store_true")
    args = parser.parse_args()
    if args.github_event:
        check_event(json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8")))
    elif args.message_file:
        if not message_valid(args.message_file.read_text(encoding="utf-8")):
            raise ValueError("提交须为type(scope): 中文说明")
    elif args.commit_range:
        for sha in git("rev-list", "--no-merges", args.commit_range).decode().splitlines():
            message = git("show", "-s", "--format=%B", sha).decode()
            # GitHub Use this template 的根提交由平台生成；仅此固定文本例外。
            parents = git("show", "-s", "--format=%P", sha).strip()
            if not parents and message.strip() == "Initial commit":
                continue
            if not message_valid(message):
                raise ValueError("提交不符合中文格式：" + sha[:12])
    else:
        files = dict(sources(args.staged))
        config, version = validate(files)
        print(f"REPOSITORY_CHECK_OK {config['name']} {version} files={len(files)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from None
