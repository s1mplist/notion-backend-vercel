from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class GenerationMetadata(BaseModel):
    webhook_id: UUID = Field(description="The unique ID of the webhook event")
    webhook_timestamp: datetime = Field(
        description="ISO 8601 formatted time at which the event occurred. This field can be used to order events on your side"
    )
    entity_id: UUID = Field(description="The entity ID where the event originated from")
    generation_started_at: Optional[datetime] = Field(
        description="Timestamp when PDF generation started"
    )
    generation_completed_at: Optional[datetime] = Field(
        default=None, description="Timestamp when PDF generation completed"
    )
    generation_status: Optional[str] = Field(
        default=None, description="Status of the PDF generation process"
    )
    generation_error: Optional[str] = Field(
        default=None, description="Error message if PDF generation failed"
    )
