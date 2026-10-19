from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from crud import users


async def get_current_user(
        authorization: str = Header(..., alias="Authorization"),
        db: AsyncSession = Depends(get_db)
):
    try:
        token = authorization.split(" ")[1]
        user = await users.get_user_by_token(db, token)
        if not user:
            raise HTTPException(status_code=401, detail="无效 token")
        return user
    except IndexError:
        raise HTTPException(status_code=401, detail="Authorization header 格式错误")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"认证失败：{e}")
