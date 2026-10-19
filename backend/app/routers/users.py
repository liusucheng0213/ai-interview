import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from crud.users import get_user_by_username, create_user, authenticate_user, create_or_update_token
from models.users import User
from schemas.users import UserRegisterRequest, UserLoginRequest, UserRegisterResponse, UserInfoResponse, \
    UserLoginResponse, UserProfileUpdateRequest
from utils.auth import get_current_user
from utils.response import success_response
from utils.enterprise_kb import parse_enterprise_kf_disabled
from utils.security import get_hash_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/user", tags=["users"])


@router.post("/register", summary="用户注册")
async def register(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户已存在")
    user = await create_user(db, request)
    token = await create_or_update_token(db, user.id)
    response = UserRegisterResponse(
        token=token,
        user_info=UserInfoResponse.model_validate(user))
    return success_response(message="注册成功", data=response)


@router.post("/login", summary="用户登录")
async def login(request: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = await create_or_update_token(db, user.id)
    response = UserLoginResponse(
        token=token,
        user_info=UserInfoResponse.model_validate(user))
    return success_response(message="登录成功", data=response)


@router.get("/info", summary="获取用户个人信息")
async def get_user_info(user: User = Depends(get_current_user)):
    info = UserInfoResponse.model_validate(user)
    data = info.model_dump()
    data["enterprise_knowledge_file_disabled_ids"] = sorted(parse_enterprise_kf_disabled(user))
    return success_response(message="查询成功", data=data)


@router.put("/profile", summary="保存用户个人信息")
async def save_user_profile(
    request: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    update_values = {}
    if request.email is not None:
        update_values["email"] = request.email
    if request.gender is not None:
        update_values["gender"] = request.gender
    if request.major is not None:
        update_values["major"] = request.major
    if request.signature is not None:
        update_values["signature"] = request.signature
    if request.avatar is not None:
        update_values["avatar"] = (request.avatar or "")[:32] or None
    if request.hobbies is not None:
        update_values["hobbies"] = (request.hobbies or "")[:500] or None
    if request.company_name is not None:
        update_values["company_name"] = (request.company_name or "")[:255] or None
    if request.company_code is not None:
        update_values["company_code"] = (request.company_code or "")[:100] or None
    if request.password:
        update_values["password"] = get_hash_password(request.password)

    if update_values:
        await db.execute(update(User).where(User.id == user.id).values(**update_values))

    result = await db.execute(select(User).where(User.id == user.id))
    updated_user = result.scalar_one()
    return success_response(message="保存成功", data=UserInfoResponse.model_validate(updated_user))
