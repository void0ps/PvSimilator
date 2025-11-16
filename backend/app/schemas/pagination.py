"""分页和聚合相关的Schema定义"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=50, ge=1, le=1000, description="每页数量")
    

class PaginatedResponse(BaseModel):
    """分页响应"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")
    data: List[Any] = Field(description="数据列表")


class TimeSeriesAggregationParams(BaseModel):
    """时间序列聚合参数"""
    start_time: Optional[datetime] = Field(None, description="起始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    aggregation: str = Field(default="hourly", description="聚合粒度：hourly, daily, weekly, monthly")
    metrics: List[str] = Field(default=["mean"], description="聚合指标：mean, max, min, sum, count")


class ShadingDataAggregation(BaseModel):
    """遮挡数据聚合结果"""
    timestamp: datetime
    mean_shading_factor: float
    min_shading_factor: float
    max_shading_factor: float
    mean_shading_margin: float
    sample_count: int


class BaySummary(BaseModel):
    """Bay摘要信息（轻量级）"""
    bay_id: str
    table_id: int
    module_count: int
    avg_shading_factor: Optional[float] = None
    

class DetailedShadingData(BaseModel):
    """详细遮挡数据（按需加载）"""
    bay_id: str
    timestamp: datetime
    rotation_angle: float
    shading_factor: float
    shading_margin: float
    poa: Optional[float] = None

















