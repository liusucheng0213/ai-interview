"""自检：调用 vms2d_start（需网络与 backend/.env）。可选参数：形象 ID，如 python tools/iflytek_vms_smoke.py 118801001"""
from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_ROOT, ".env"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if len(sys.argv) > 1 and sys.argv[1].strip():
    os.environ["IFLYTEK_VH_AVATAR_ID"] = sys.argv[1].strip()

from services import iflytek_virtual_human as vh  # noqa: E402


async def main() -> None:
    try:
        r = await vh.vms_start(99999)
        sess = (r.get("session") or "")[:40]
        url = (r.get("stream_url") or "")[:80]
        print("vms_start OK session_prefix=", sess, "stream=", url)
    except Exception as e:
        print("vms_start FAIL:", e)


if __name__ == "__main__":
    asyncio.run(main())
