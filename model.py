from pydantic import BaseModel, Field
from typing import Optional


class SiteInfo(BaseModel):
    """文物保护单位信息结构化输出Schema（严格JSON格式）"""

    # Optional 表示可选，未找到时返回 None
    site_name: Optional[str] = Field(
        description="文物保护单位的完整名称，必须和文档原文完全一致",
        examples=["清真寺"],
    )
    detailed_address: Optional[str] = Field(
        description="文物保护单位的详细地点", examples=["哈尔滨市双城区拉林镇"]
    )
