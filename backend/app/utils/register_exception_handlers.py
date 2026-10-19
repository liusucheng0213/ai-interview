from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from utils.exception import http_exception_handler, integrity_error_handler, sqlalchemy_error_handler, \
    validation_exception_handler, general_exception_handler, starlette_http_exception_handler, BusinessException, \
    business_exception_handler, AuthenticationException, authentication_exception_handler, AuthorizationException, \
    authorization_exception_handler


def register_exception_handlers(app):
    """
    注册全局异常处理函数
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(AuthorizationException, authorization_exception_handler)