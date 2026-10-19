from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class User(Base):
    """
    用户信息表
    存储用户注册的账户信息，用于登录认证
    """
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名（唯一）")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希值（bcrypt 加密）")
    email: Mapped[Optional[str]] = mapped_column(String(255), comment="邮箱（可选）")
    gender: Mapped[Optional[str]] = mapped_column(String(10), comment="性别（男/女/未知）")
    major: Mapped[Optional[str]] = mapped_column(String(255), comment="专业（可选）")
    signature: Mapped[Optional[str]] = mapped_column(String(255), comment="个性签名（可选）")
    # 展示用：头像存单个 emoji 或短字符串（如 🦁）；兴趣爱好为自由文本
    avatar: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="头像 emoji")
    hobbies: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="兴趣爱好")
    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="personal",
        comment="账号类型：personal / enterprise",
    )
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="企业名称")
    company_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="企业编码（用于隔离）")
    enterprise_kf_disabled_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="求职者停用的企业 knowledge_file.id 列表（JSON 数组）",
    )


class UserToken(Base):
    """
    用户访问令牌表
    存储用户生成的访问令牌，用于用户登录认证
    """
    __tablename__ = "users_tokens"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="关联用户 ID")
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="用户访问令牌")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="令牌过期时间")
