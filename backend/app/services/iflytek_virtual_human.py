"""
讯飞 AI 虚拟人（2D）服务端代理：鉴权 + 启动会话 + 文本驱动。

说明：官方接口主要面向服务端调用（浏览器跨域受限），故由后端代签并转发。
拉流地址多为 RTMP，浏览器内嵌播放通常需转封装或 WebRTC（xrtc）；前端可先展示会话信息与占位。
文档：https://www.xfyun.cn/doc/tts/virtual_human/API.html
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

IFLYTEK_APP_ID = os.getenv("IFLYTEK_APP_ID", "").strip()
IFLYTEK_API_KEY = os.getenv("IFLYTEK_API_KEY", "").strip()
IFLYTEK_API_SECRET = os.getenv("IFLYTEK_API_SECRET", "").strip()
IFLYTEK_VH_AVATAR_ID = os.getenv("IFLYTEK_VH_AVATAR_ID", "111204007").strip()
IFLYTEK_VH_WIDTH = int(os.getenv("IFLYTEK_VH_WIDTH", "720") or 720)
IFLYTEK_VH_HEIGHT = int(os.getenv("IFLYTEK_VH_HEIGHT", "1280") or 1280)
IFLYTEK_VH_PROTOCOL = os.getenv("IFLYTEK_VH_STREAM_PROTOCOL", "rtmp").strip()  # 或 xrtc
IFLYTEK_VH_TTS_VCN = os.getenv("IFLYTEK_VH_TTS_VCN", "x4_yezi").strip()
IFLYTEK_VH_TTS_AUE = os.getenv("IFLYTEK_VH_TTS_AUE", "lame").strip()  # lame/mp3 或 raw
IFLYTEK_VH_TTS_AUDIO_ENCODING = os.getenv("IFLYTEK_VH_TTS_AUDIO_ENCODING", "mp3").strip()
IFLYTEK_VH_BG_RES_KEY = os.getenv("IFLYTEK_VH_BG_RES_KEY", "").strip()
IFLYTEK_VH_HOST = os.getenv("IFLYTEK_VH_HOST", "vms.cn-huadong-1.xf-yun.com").strip()
IFLYTEK_VH_SCENE_ID = os.getenv("IFLYTEK_VH_SCENE_ID", "2").strip()
IFLYTEK_VH_INTERACT_SERVER_URL = os.getenv(
    "IFLYTEK_VH_INTERACT_SERVER_URL", "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact"
).strip()
IFLYTEK_VH_SYNC_MODE = int(os.getenv("IFLYTEK_VH_SYNC_MODE", "1") or 1)  # 1=音频驱动口型
IFLYTEK_VH_HAS_AUDIO = (os.getenv("IFLYTEK_VH_HAS_AUDIO", "true").strip().lower() in ("1", "true", "yes"))
IFLYTEK_VH_VIDEO_TYPE = os.getenv("IFLYTEK_VH_VIDEO_TYPE", "lip_sync").strip()
# vms2d_* 协议头 uid：须为讯飞「用户服务」返回的 uid；无则留空。传业务库 user_id 会触发 SUBID_xxx_数字 校验失败（11203）。
IFLYTEK_VH_REQUEST_UID = os.getenv("IFLYTEK_VH_REQUEST_UID", "").strip()

# 内存会话：user_id -> { session, stream_hint }
_vh_sessions: Dict[int, Dict[str, Any]] = {}


def is_iflytek_virtual_human_configured() -> bool:
    return bool(IFLYTEK_APP_ID and IFLYTEK_API_KEY and IFLYTEK_API_SECRET)


def is_iflytek_websdk_configured() -> bool:
    """前端 WebSDK（xrtc/webrtc）所需最小配置。"""
    return bool(
        IFLYTEK_APP_ID
        and IFLYTEK_API_KEY
        and IFLYTEK_API_SECRET
        and IFLYTEK_VH_SCENE_ID
        and IFLYTEK_VH_INTERACT_SERVER_URL
    )


def build_signed_url(path: str, method: str = "POST") -> str:
    host = IFLYTEK_VH_HOST
    date = format_datetime(datetime.now(timezone.utc), usegmt=True)
    request_line = f"{method} {path} HTTP/1.1"
    signature_origin = f"host: {host}\ndate: {date}\n{request_line}"
    signature_sha = hmac.new(
        IFLYTEK_API_SECRET.encode("utf-8"),
        signature_origin.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode()
    authorization_origin = (
        f'api_key="{IFLYTEK_API_KEY}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode()).decode()
    q = {"host": host, "date": date, "authorization": authorization}
    return f"https://{host}{path}?{urlencode(q)}"


def _decode_stream_url(payload: dict) -> Optional[str]:
    try:
        b64 = payload.get("stream_url", {}).get("text")
        if not b64:
            return None
        raw = base64.b64decode(b64)
        return raw.decode("utf-8", errors="replace")
    except (binascii.Error, TypeError, AttributeError):
        return None


def _tts_vcn_for_vms_http(vcn: str) -> str:
    """HTTP vms2d_ctrl 文档列出的发音人与 WebSDK 部分产品线命名不完全一致，做轻量兼容。"""
    v = (vcn or "").strip()
    if v.lower() == "x4_yezi":
        return "x3_yezi"
    return v or "x3_yezi"


async def vms_start(user_id: int) -> Dict[str, Any]:
    """调用 vms2d_start，建立虚拟人会话。"""
    if not is_iflytek_virtual_human_configured():
        raise RuntimeError("IFLYTEK_APP_ID / IFLYTEK_API_KEY / IFLYTEK_API_SECRET 未配置")

    path = "/v1/private/vms2d_start"
    url = build_signed_url(path)
    # 严格按官方文档：vmr 仅 stream.protocol（可选）、avatar_id、width、height。
    # 曾扩展的 has_audio/sync_mode/video_type、vmr.audio 等会触发 10163 unknown field。
    body = {
        "header": {"app_id": IFLYTEK_APP_ID, "uid": IFLYTEK_VH_REQUEST_UID},
        "parameter": {
            "vmr": {
                "stream": {"protocol": IFLYTEK_VH_PROTOCOL},
                "avatar_id": IFLYTEK_VH_AVATAR_ID,
                "width": IFLYTEK_VH_WIDTH,
                "height": IFLYTEK_VH_HEIGHT,
            }
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=body, headers={"Content-Type": "application/json"})

    try:
        data = resp.json()
    except Exception:
        logger.error("[讯飞虚拟人] start 非 JSON：%s", resp.text[:500])
        raise RuntimeError(f"讯飞虚拟人 start 响应异常：HTTP {resp.status_code}")

    header = data.get("header") or {}
    if header.get("code") != 0:
        logger.error("[讯飞虚拟人] start 失败：%s", data)
        code = header.get("code")
        raw = header.get("message") or "讯飞虚拟人启动失败"
        # 11203：服务端返回的内部串里常见 avatar_id.xxx，表示形象与当前应用/订阅不匹配或未开通
        if code == 11203 or (isinstance(raw, str) and "avatar_id." in raw and "vms" in raw):
            msg = (
                "虚拟人 HTTP 拉流（vms2d_start）被拒绝（11203）。常见原因：① 请求头 uid 误填了业务用户 ID（应留空或填讯飞用户服务 uid，见 IFLYTEK_VH_REQUEST_UID）；"
                "② 开放平台未开通「AI虚拟人技术」或形象未对该应用授权；③ WebSDK 的 IFLYTEK_VH_SCENE_ID 须为控制台「接口服务ID」。"
                f" 当前 avatar_id={IFLYTEK_VH_AVATAR_ID}。"
            )
        elif code == 20015 or "avatarId" in str(raw).lower():
            msg = (
                f"{raw}；请设置环境变量 IFLYTEK_VH_AVATAR_ID 为控制台「AI虚拟人」可用形象 ID"
                "（文档示例：110017006、110023005、110018008、118801001、110022010、110005018）"
            )
        else:
            msg = raw
        raise RuntimeError(msg)

    session = header.get("session")
    stream_url = header.get("stream_url") or _decode_stream_url(data.get("payload") or {})
    _vh_sessions[user_id] = {"session": session, "stream_url": stream_url}
    logger.info("[讯飞虚拟人] 会话已建立 user=%s sid=%s", user_id, header.get("sid"))

    return {
        "session": session,
        "sid": header.get("sid"),
        "stream_url": stream_url,
        "avatar_id": IFLYTEK_VH_AVATAR_ID,
        "note": "RTMP 多为 SRS；HTTP-FLV 同路径 .flv 可由前端 flv.js + 反向代理播放（见项目 frontend/vite 配置）",
    }


async def vms_text_drive(user_id: int, text: str) -> Dict[str, Any]:
    """文本驱动虚拟人播报（需已有 session）。"""
    if not is_iflytek_virtual_human_configured():
        raise RuntimeError("讯飞虚拟人未配置")

    info = _vh_sessions.get(user_id)
    session = info.get("session") if info else None
    if not session:
        raise RuntimeError("请先调用 start 建立虚拟人会话")

    path = "/v1/private/vms2d_ctrl"
    url = build_signed_url(path)
    text_b64 = base64.b64encode(text.encode("utf-8")).decode()

    body = {
        "header": {"app_id": IFLYTEK_APP_ID, "session": session, "uid": IFLYTEK_VH_REQUEST_UID},
        "parameter": {
            # 文档仅列 volume/vcn/speed/pitch；aue、audio_encoding 会触发 schema 报错
            "tts": {
                "vcn": _tts_vcn_for_vms_http(IFLYTEK_VH_TTS_VCN),
                "speed": 50,
                "pitch": 50,
                "volume": 50,
            }
        },
        "payload": {
            "text": {"encoding": "utf8", "status": 3, "text": text_b64},
            # 与官方示例一致的最小 ctrl_w；扩展字段易 10163
            "ctrl_w": {"encoding": "utf8", "format": "json", "status": 3},
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=body, headers={"Content-Type": "application/json"})

    data = resp.json()
    header = data.get("header") or {}
    if header.get("code") != 0:
        logger.warning("[讯飞虚拟人] ctrl 失败：%s", data)
        code = header.get("code")
        raw = header.get("message") or "文本驱动失败"
        if code == 11203 or (isinstance(raw, str) and "avatar_id." in raw and "vms" in raw):
            raise RuntimeError(
                "虚拟人文本驱动失败：形象或服务授权异常（11203）。请先成功建立会话（start），并检查形象 ID 与控制台授权。"
            )
        raise RuntimeError(raw)

    if header.get("session"):
        _vh_sessions[user_id]["session"] = header["session"]
    return {"ok": True, "sid": header.get("sid")}


async def vms_stop(user_id: int) -> None:
    if not is_iflytek_virtual_human_configured():
        return
    info = _vh_sessions.get(user_id)
    session = info.get("session") if info else None
    if not session:
        _vh_sessions.pop(user_id, None)
        return
    path = "/v1/private/vms2d_stop"
    url = build_signed_url(path)
    body = {"header": {"app_id": IFLYTEK_APP_ID, "uid": IFLYTEK_VH_REQUEST_UID, "session": session}}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(url, json=body, headers={"Content-Type": "application/json"})
    except Exception as e:
        logger.warning("[讯飞虚拟人] stop 异常：%s", e)
    finally:
        _vh_sessions.pop(user_id, None)


def get_cached_session(user_id: int) -> Optional[Dict[str, Any]]:
    return _vh_sessions.get(user_id)
