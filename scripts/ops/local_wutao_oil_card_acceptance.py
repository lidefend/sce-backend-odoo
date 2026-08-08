#!/usr/bin/env python3
"""Run the wutao oil-card browser acceptance with an in-memory password."""

from __future__ import annotations

import getpass
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND_URL = "http://1.95.85.92:18081"


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
    password = getpass.getpass("请输入 wutao 正式密码（输入不回显）: ")
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
