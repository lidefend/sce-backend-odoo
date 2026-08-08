#!/usr/bin/env python3
"""Run the wutao oil-card browser acceptance with an in-memory password."""

from __future__ import annotations

import getpass
import json
import os
import re
import stat
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND_URL = "http://1.95.85.92:18081"
SECRET_FILE = Path("/home/lidefend/workspace/.secure/runtime-credentials/wutao-acceptance.password")


def stored_password(path: Path = SECRET_FILE) -> str:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return ""
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise SystemExit("凭据文件必须属于当前用户且为普通文件")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise SystemExit("凭据文件权限必须是 600")
    if info.st_size <= 0 or info.st_size > 512:
        raise SystemExit("凭据文件大小异常")
    payload = path.read_bytes()
    if b"\x00" in payload or b"\n" in payload or b"\r" in payload:
        raise SystemExit("凭据文件格式异常")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit("凭据文件编码异常") from exc


def locked_database(frontend_url: str) -> str:
    with urllib.request.urlopen(f"{frontend_url.rstrip('/')}/runtime-config.js", timeout=5) as response:
        source = response.read().decode("utf-8")
    match = re.search(r"Object\.freeze\((\{.*\})\)", source)
    if not match:
        raise SystemExit("运行时配置缺少锁定数据库")
    payload = json.loads(match.group(1))
    database = str(payload.get("odooDb") or "").strip()
    if not database or payload.get("odooDbLocked") is not True:
        raise SystemExit("验收入口没有锁定数据库")
    return database


def main() -> int:
    frontend_url = str(os.environ.get("FRONTEND_URL") or DEFAULT_FRONTEND_URL).rstrip("/")
    database = locked_database(frontend_url)
    password = stored_password() or getpass.getpass("请输入 wutao 正式密码（输入不回显）: ")
    if not password:
        raise SystemExit("密码不能为空")
    environment = os.environ.copy()
    environment.update(
        {
            "FRONTEND_URL": frontend_url,
            "DB_NAME": database,
            "E2E_LOGIN": "wutao",
            "E2E_PASSWORD": password,
        }
    )
    try:
        completed = subprocess.run(
            ["node", "scripts/verify/oil_card_menu_browser_acceptance.js"],
            cwd=ROOT,
            env=environment,
            check=False,
        )
        return completed.returncode
    finally:
        environment.pop("E2E_PASSWORD", None)
        password = ""


if __name__ == "__main__":
    raise SystemExit(main())
