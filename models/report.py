from datetime import datetime

from pydantic import BaseModel


class Image(BaseModel):
    url: str
    description: str


class Plot(BaseModel):
    id: str
    name: str
    area: float
    growth_stage: str
    crop: str
    variety: str
    images: list[Image]
    additional_images: str | None
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
    plots: list[Plot]
