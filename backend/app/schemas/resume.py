"""
简历相关的 Schema 定义
"""
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class EducationInfo(BaseModel):
    """教育经历"""
    school: str
    degree: str
    major: str
    start_date: str
    end_date: str
    honors: Optional[str] = None


class ExperienceInfo(BaseModel):
    """工作经历（achievements 兼容字符串或条目列表，与种子数据/LLM 输出一致）"""
    company: str
    position: str
    start_date: str
    end_date: str
    achievements: Optional[Union[str, List[str]]] = None


class ProjectInfo(BaseModel):
    """项目经验"""
    name: str
    role: str
    description: str


class BasicInfo(BaseModel):
    """基本信息"""
    name: str
    email: str
    phone: str


class ResumeData(BaseModel):
    """简历数据结构"""
    basic_info: BasicInfo
    education: List[EducationInfo] = Field(default_factory=list)
    experience: List[ExperienceInfo] = Field(default_factory=list)
    projects: List[ProjectInfo] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    resume_id: Optional[int] = None


class OptimizedResumeData(BaseModel):
    """优化后的简历数据"""
    optimized_resume: ResumeData
    optimized_text: str


class GenerateResumeRequest(BaseModel):
    """生成简历请求"""
    name: str
    gender: Optional[str] = None
    email: str
    phone: Optional[str] = None
    job_target: Optional[str] = None
    experience_years: Optional[str] = None
    education: List[dict] = Field(default_factory=list)
    experience: List[dict] = Field(default_factory=list)
    projects: List[dict] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)


class ResumeHistoryItem(BaseModel):
    """简历历史项"""
    id: int
    file_name: str
    status: str
    basic_info: dict
    created_at: str
