from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# 用户信息响应模型
class UserInfoResponse(BaseModel):
    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    gender: Optional[str] = Field(None, description="性别")
    major: Optional[str] = Field(None, description="专业")
    signature: Optional[str] = Field(None, description="个性签名")
    avatar: Optional[str] = Field(None, description="头像 emoji")
    hobbies: Optional[str] = Field(None, description="兴趣爱好")
    account_type: str = Field("personal", description="账号类型：personal/enterprise")
    company_name: Optional[str] = Field(None, description="企业名称")
    company_code: Optional[str] = Field(None, description="企业编码")

    model_config = ConfigDict(
        from_attributes=True
    )


# 用户个人信息更新请求模型
class UserProfileUpdateRequest(BaseModel):
    email: Optional[str] = Field(None, description="邮箱")
    gender: Optional[str] = Field(None, description="性别")
    major: Optional[str] = Field(None, description="专业")
    signature: Optional[str] = Field(None, description="个性签名")
    password: Optional[str] = Field(None, description="新密码（可选）")
    avatar: Optional[str] = Field(None, description="头像 emoji")
    hobbies: Optional[str] = Field(None, description="兴趣爱好")
    company_name: Optional[str] = Field(None, description="企业名称")
    company_code: Optional[str] = Field(None, description="企业编码")


class UserRegisterRequest(BaseModel):
    """
    用户注册请求模型
    """
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    email: str = Field(..., description="邮箱")
    account_type: str = Field("personal", description="账号类型：personal/enterprise")
    company_name: Optional[str] = Field(None, description="企业名称")
    company_code: Optional[str] = Field(None, description="企业编码")


class UserRegisterResponse(BaseModel):
    """
    用户注册响应模型
    """
    token: str = Field(..., description="注册结果令牌")
    user_info: UserInfoResponse = Field(..., description="用户信息")
    model_config = ConfigDict(
        from_attributes=True
    )


class UserLoginRequest(BaseModel):
    """
    用户登录请求模型
    """
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserLoginResponse(BaseModel):
    """
    用户登录响应模型
    """
    token: str = Field(..., description="访问令牌")
    user_info: UserInfoResponse = Field(..., description="用户信息")
    model_config = ConfigDict(
        from_attributes=True
    )
