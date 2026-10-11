#!/usr/bin/env python3
"""Store the local wutao acceptance password with owner-only permissions."""

from __future__ import annotations

import getpass
import os
import stat
import tempfile
from pathlib import Path


SECRET_DIRECTORY = Path("/home/lidefend/workspace/.secure/runtime-credentials")
SECRET_FILE = SECRET_DIRECTORY / "wutao-acceptance.password"


def assert_private_directory(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise SystemExit("凭据目录必须属于当前用户且为普通目录")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise SystemExit("凭据目录权限必须是 700")


def main() -> int:
    SECRET_DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert_private_directory(SECRET_DIRECTORY)
    first = getpass.getpass("请输入 wutao 正式密码（输入不回显）: ")
    second = getpass.getpass("请再次输入确认（输入不回显）: ")
    if not first or first != second:
        raise SystemExit("两次密码不一致，未写入")
    if "\x00" in first or "\n" in first or "\r" in first:
        raise SystemExit("密码包含不支持的控制字符，未写入")
    temporary_path = None
    try:
        descriptor, raw_path = tempfile.mkstemp(prefix=".wutao-acceptance.", dir=SECRET_DIRECTORY)
        temporary_path = Path(raw_path)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(first.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, SECRET_FILE)
        temporary_path = None
        os.chmod(SECRET_FILE, 0o600, follow_symlinks=False)
    finally:
        first = second = ""
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    print(f"凭据已安全保存：{SECRET_FILE}（内容不显示）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
