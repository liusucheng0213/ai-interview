import asyncio
import logging
import traceback
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.env_util import env_str

logger = logging.getLogger(__name__)

# 从环境变量读取 DEBUG 模式（生产环境设为 False）
DEBUG_MODE = env_str("DEBUG_MODE", "False").lower() in ("true", "1", "yes")


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP 异常处理函数
    """
    logger.warning(f"HTTP 异常 [{exc.status_code}]: {exc.detail} - {request.method} {request.url}")
    if DEBUG_MODE:
        traceback.print_exc()

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "success": False,
            "data": None
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    IntegrityError 异常处理函数 - 处理数据库完整性约束错误
    """
    error_msg = str(exc.orig)
    detail = "数据库错误"

    # 根据不同的完整性错误类型返回具体的错误信息
    if "username_UNIQUE" in error_msg or "Duplicate entry" in error_msg or "UNIQUE constraint failed" in error_msg:
        detail = "用户名已存在"
    elif "FOREIGN KEY" in error_msg or "外键约束失败" in error_msg:
        detail = "关联数据不存在，请检查引用的资源"
    elif "NOT NULL" in error_msg or "空值约束" in error_msg:
        detail = "必填字段不能为空"
    else:
        detail = f"数据完整性错误: {error_msg[:100]}..."  # 截取前100个字符

    error_data = {
        "message": detail,
        "error_type": "IntegrityError",
        "path": str(request.url),
        "method": request.method
    }

    if DEBUG_MODE:
        error_data.update({
            "original_error": error_msg,
            "sql": str(exc.statement) if hasattr(exc, 'statement') else None,
            "params": str(exc.params) if hasattr(exc, 'params') else None
        })

    logger.error(f"IntegrityError at {request.url}: {error_msg}")

    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": detail,
            "success": False,
            "data": error_data
        }
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """
    SQLAlchemyError 错误处理函数 - 处理通用 SQLAlchemy 错误
    """
    if hasattr(exc, 'orig') and exc.orig:
        error_msg = str(exc.orig)
    else:
        error_msg = str(exc)

    logger.error(f"SQLAlchemy 错误 at {request.url}: {error_msg}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": f"数据库错误：{error_msg}",
            "data": None
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    """
    Pydantic 验证异常处理函数
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        })

    error_data = {
        "message": "请求参数验证失败",
        "errors": errors,
        "path": str(request.url),
        "method": request.method
    }

    if DEBUG_MODE:
        error_data["raw_validation_error"] = str(exc)

    logger.warning(f"Validation error at {request.url}: {errors}")

    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "请求参数无效",
            "success": False,
            "data": error_data
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    通用异常处理函数 - 捕获所有未处理的异常
    """
    if isinstance(exc, asyncio.CancelledError):
        raise exc

    error_msg = str(exc)

    # 特殊错误类型的处理
    if "JSONDecodeError" in str(type(exc)):
        detail = "JSON解析失败，请检查请求体格式"
        status_code = 400
    elif "TimeoutError" in str(type(exc)):
        detail = "请求超时，请稍后重试"
        status_code = 504
    elif "ConnectionError" in str(type(exc)):
        detail = "网络连接失败"
        status_code = 503
    else:
        detail = "服务器内部错误"
        status_code = 500

    error_data = {
        "message": detail,
        "error_type": type(exc).__name__,
        "path": str(request.url),
        "method": request.method
    }

    if DEBUG_MODE:
        error_data.update({
            "original_error": error_msg,
            "traceback": traceback.format_exc(),
            "args": str(exc.args)
        })

    logger.critical(f"Unhandled exception at {request.url}: {type(exc).__name__} - {error_msg}")

    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "message": detail,
            "success": False,
            "data": error_data
        }
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Starlette HTTP 异常处理函数
    """
    logger.warning(f"Starlette HTTP 异常 [{exc.status_code}]: {exc.detail} - {request.method} {request.url}")
    if DEBUG_MODE:
        traceback.print_exc()

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "success": False,
            "data": {
                "path": str(request.url),
                "method": request.method
            }
        }
    )


# 添加自定义业务异常类
class BusinessException(Exception):
    """业务逻辑异常"""

    def __init__(self, message: str, code: int = 400, data: Optional[dict] = None):
        self.message = message
        self.code = code
        self.data = data or {}


async def business_exception_handler(request: Request, exc: BusinessException):
    """
    业务异常处理函数
    """
    logger.warning(f"业务异常 at {request.url} [{exc.code}]: {exc.message}")

    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "success": False,
            "data": exc.data
        }
    )


# 添加认证相关的异常处理
class AuthenticationException(Exception):
    """认证异常"""

    def __init__(self, message: str = "认证失败", code: int = 401):
        self.message = message
        self.code = code


async def authentication_exception_handler(request: Request, exc: AuthenticationException):
    """
    认证异常处理函数
    """
    logger.warning(f"认证异常 at {request.url}: {exc.message}")
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "success": False,
            "data": {
                "path": str(request.url),
                "method": request.method
            }
        }
    )


class AuthorizationException(Exception):
    """授权异常"""

    def __init__(self, message: str = "无权限访问", code: int = 403):
        self.message = message
        self.code = code


async def authorization_exception_handler(request: Request, exc: AuthorizationException):
    """
    授权异常处理函数
    """
    logger.warning(f"授权异常 at {request.url}: {exc.message}")
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "success": False,
            "data": {
                "path": str(request.url),
                "method": request.method
            }
        }
    )
