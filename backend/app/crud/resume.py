"""
简历相关的数据库 CRUD 操作
"""
import logging
from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.resume import Resume

logger = logging.getLogger(__name__)


async def create_resume(
    db: AsyncSession,
    user_id: int,
    file_name: str,
    file_path: str
):
    """创建简历记录（上传阶段）"""
    logger.info(f"创建简历记录 - 用户 ID: {user_id}, 文件名：{file_name}")
    
    resume = Resume(
        user_id=user_id,
        file_name=file_name,
        file_path=file_path,
        status="uploaded"
    )
    
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    
    logger.info(f"✅ 简历记录创建成功，ID: {resume.id}")
    return resume


async def update_resume_analysis(
    db: AsyncSession,
    resume_id: int,
    resume_data: dict
):
    """更新简历分析结果"""
    logger.info(f"更新简历分析结果 - 简历 ID: {resume_id}")
    
    resume = await get_resume_by_id(db, resume_id)
    if not resume:
        logger.error(f"❌ 简历不存在：{resume_id}")
        return None
    
    resume.basic_info = resume_data.get('basic_info', {})
    resume.education = resume_data.get('education', [])
    resume.experience = resume_data.get('experience', [])
    resume.projects = resume_data.get('projects', [])
    resume.skills = resume_data.get('skills', [])
    resume.status = "analyzed"
    
    await db.commit()
    await db.refresh(resume)
    
    logger.info(f"✅ 简历分析结果已更新")
    return resume


async def update_resume_optimization(
    db: AsyncSession,
    resume_id: int,
    optimized_data: dict
):
    """更新简历优化结果"""
    logger.info(f"更新简历优化结果 - 简历 ID: {resume_id}")
    
    resume = await get_resume_by_id(db, resume_id)
    if not resume:
        logger.error(f"❌ 简历不存在：{resume_id}")
        return None
    
    resume.optimized_basic_info = optimized_data.get('basic_info', {})
    resume.optimized_education = optimized_data.get('education', [])
    resume.optimized_experience = optimized_data.get('experience', [])
    resume.optimized_projects = optimized_data.get('projects', [])
    resume.optimized_skills = optimized_data.get('skills', [])
    resume.status = "optimized"
    
    await db.commit()
    await db.refresh(resume)
    
    logger.info(f"✅ 简历优化结果已更新")
    return resume


async def get_resume_by_id(db: AsyncSession, resume_id: int):
    """根据 ID 获取简历"""
    query = await db.execute(select(Resume).where(Resume.id == resume_id))
    return query.scalar_one_or_none()


async def get_user_resumes(db: AsyncSession, user_id: int):
    """获取用户的所有简历"""
    logger.info(f"获取用户 {user_id} 的简历列表")
    query = await db.execute(select(Resume).where(Resume.user_id == user_id).order_by(Resume.id.desc()))
    return query.scalars().all()


async def delete_resume(db: AsyncSession, resume_id: int):
    """删除简历"""
    logger.info(f"删除简历 - 简历 ID: {resume_id}")
    
    resume = await get_resume_by_id(db, resume_id)
    if not resume:
        logger.error(f"❌ 简历不存在：{resume_id}")
        return False
    
    await db.execute(sql_delete(Resume).where(Resume.id == resume_id))
    await db.commit()
    
    logger.info(f"✅ 简历已删除")
    return True
