from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class Image(BaseModel):
    url: str
    description: str


class Plot(BaseModel):
    id: str
    area: float
    growth_stage: str
    crop: str
    variety: str
    images: List[Image]
    additional_images: Optional[str]
    assessment: str


class Report(BaseModel):
    farm_name: str
    consultant_name: str
    report_month: str
    owner_name: str
    farm_city: str
    harvest_period: str
    general_info: str
    next_visit_date: datetime
    current_visit_date: datetime
    operations_schedule: str
    plots: List[Plot]
