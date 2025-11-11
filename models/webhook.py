from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WebhookRequest(BaseModel):
    id: UUID = Field(..., description="The unique ID of the webhook event")
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 formatted time at which the event occurred. This field can be used to order events on your side",
    )
    workspace_id: UUID = Field(
        ..., description="The workspace ID where the event originated from"
    )
    workspace_name: str | None = Field(
        None,
        description="The workspace name where the event originated from",
        max_length=255,
    )
    subscription_id: UUID = Field(..., description="The ID of the webhook subscription")
    integration_id: UUID = Field(
        ..., description="Associated integration ID the subscription is set up with"
    )
    type: str = Field(
        ...,
        description="Type of the event, e.g. page.created",
        min_length=1,
        max_length=100,
    )
    authors: list[dict[str, Any]] = Field(
        ...,
        description="Array of JSON objects with the ID (id) and type (type) of the author who performed the action that caused this webhook. type can be 'person', 'bot', or 'agent'.",
        min_length=1,
    )
    accessible_by: list[dict[str, Any]] | None = Field(
        default=None,
        description="Array of JSON objects with the ID (id) and type (type) of each accessible bot and user who owns the bot connection to the integration_id and has access to the webhook's entity.",
    )
    attempt_number: int = Field(
        ...,
        description="A number ranged from 1 - 8 that indicates the attempt number of the current event delivery",
        ge=1,
        le=8,
    )
    entity: dict[str, Any] = Field(
        ...,
        description="ID (id) and type (type) of the object that triggered the event. The type can be 'page', 'block', or 'database'.",
    )
    data: dict[str, Any] = Field(
        default_factory=dict, description="Additional, event-specific data."
    )

    def get_entity_type(self) -> str:
        """Get entity type safely."""
        return self.entity.get("type", "")
