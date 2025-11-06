from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GenerationMetadata(BaseModel):
    webhook_timestamp: datetime = Field(
        description="ISO 8601 formatted time at which the event occurred. This field can be used to order events on your side"
    )
    entity_id: UUID = Field(description="The entity ID where the event originated from")
    generation_started_at: datetime | None = Field(
        description="Timestamp when PDF generation started"
    )
    generation_completed_at: datetime | None = Field(
        default=None, description="Timestamp when PDF generation completed"
    )
    generation_status: str | None = Field(
        default=None, description="Status of the PDF generation process"
    )
    generation_error: str | None = Field(
        default=None, description="Error message if PDF generation failed"
    )
