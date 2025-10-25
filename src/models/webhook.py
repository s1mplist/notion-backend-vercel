from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Any, List, Dict, Optional


class WebhookRequest(BaseModel):
    id: UUID = Field(description="The unique ID of the webhook event")
    timestamp: datetime = Field(
        description="ISO 8601 formatted time at which the event occurred. This field can be used to order events on your side"
    )
    workspace_id: UUID = Field(
        description="The workspace ID where the event originated from"
    )
    workspace_name: Optional[str] = Field(
        description="The workspace name where the event originated from"
    )
    subscription_id: UUID = Field(description="The ID of the webhook subscription")
    integration_id: UUID = Field(
        description="Associated integration ID the subscription is set up with"
    )
    type: str = Field(description="Type of the event, e.g. page.created")
    authors: List[Dict] = Field(
        description="Array of JSON objects with the ID (id) and type (type) of the author who performed the action that caused this webhook. type can be 'person', 'bot', or 'agent'."
    )
    accessible_by: Optional[List[Dict]] = Field(
        default=None,
        description="Array of JSON objects with the ID (id) and type (type) of each accessible bot and user who owns the bot connection to the integration_id and has access to the webhook's entity.",
    )
    attempt_number: int = Field(
        description="A number ranged from 1 - 8 that indicates the attempt number of the current event delivery"
    )
    entity: Dict[str, Any] = Field(
        description="ID (id) and type (type) of the object that triggered the event. The type can be 'page', 'block', or 'database'."
    )
    data: Dict[str, Any] = Field(description="Additional, event-specific data.")
