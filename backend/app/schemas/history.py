"""历史面试条目 Schema（旧命名空间）。新代码请优先使用 schemas.interview 中同名结构，避免重复定义。"""

from typing import List, Optional
from pydantic import BaseModel, Field

class InterviewHistoryItem(BaseModel):
    """
    单条面试历史记录响应模型

    Attributes:
        interview_id: 面试 ID
        position_name: 岗位名称
        difficulty: 难度等级
        start_time: 开始时间
        end_time: 结束时间（可选）
        status: 状态（进行中/已完成）
        total_score: 总分（仅已完成时有值）
    """
    interview_id: int
    position_name: str
    difficulty: str
    start_time: str
    end_time: Optional[str] = None
    status: str
    total_score: Optional[float] = None


class InterviewHistoryResponse(BaseModel):
    """
    面试历史记录响应模型

    Attributes:
        history_list: 面试记录列表
    """
    history_list: List[InterviewHistoryItem]

