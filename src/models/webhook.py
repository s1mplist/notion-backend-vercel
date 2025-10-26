from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Any, List, Dict, Optional


class WebhookRequest(BaseModel):
    id: UUID = Field(..., description="The unique ID of the webhook event")
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 formatted time at which the event occurred. This field can be used to order events on your side",
    )
    workspace_id: UUID = Field(
        ..., description="The workspace ID where the event originated from"
    )
    workspace_name: Optional[str] = Field(
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
    authors: List[Dict[str, Any]] = Field(
        ...,
        description="Array of JSON objects with the ID (id) and type (type) of the author who performed the action that caused this webhook. type can be 'person', 'bot', or 'agent'.",
        min_length=1,
    )
    accessible_by: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Array of JSON objects with the ID (id) and type (type) of each accessible bot and user who owns the bot connection to the integration_id and has access to the webhook's entity.",
    )
    attempt_number: int = Field(
        ...,
        description="A number ranged from 1 - 8 that indicates the attempt number of the current event delivery",
        ge=1,
        le=8,
    )
    entity: Dict[str, Any] = Field(
        ...,
        description="ID (id) and type (type) of the object that triggered the event. The type can be 'page', 'block', or 'database'.",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Additional, event-specific data."
    )

    @field_validator("type")
    @classmethod
    def validate_event_type(cls, v):
        """Validate event type format."""
        if not v or "." not in v:
            raise ValueError(
                'Event type must be in format "object.action" (e.g., "page.created")'
            )

        valid_objects = ["page", "block", "database"]
        valid_actions = ["created", "updated", "deleted"]

        parts = v.split(".")
        if len(parts) != 2:
            raise ValueError("Event type must have exactly one dot separator")

        obj_type, action = parts
        if obj_type not in valid_objects:
            raise ValueError(f"Object type must be one of: {valid_objects}")
        if action not in valid_actions:
            raise ValueError(f"Action must be one of: {valid_actions}")

        return v

    @field_validator("entity")
    @classmethod
    def validate_entity(cls, v):
        """Validate entity structure."""
        if not isinstance(v, dict):
            raise ValueError("Entity must be a dictionary")

        required_fields = ["id", "type"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f'Entity must contain "{field}" field')

        if not v["id"]:
            raise ValueError("Entity ID cannot be empty")

        valid_entity_types = ["page", "block", "database"]
        if v["type"] not in valid_entity_types:
            raise ValueError(f"Entity type must be one of: {valid_entity_types}")

        return v

    @field_validator("authors")
    @classmethod
    def validate_authors(cls, v):
        """Validate authors structure."""
        if not isinstance(v, list) or not v:
            raise ValueError("Authors must be a non-empty list")

        for author in v:
            if not isinstance(author, dict):
                raise ValueError("Each author must be a dictionary")

            required_fields = ["id", "type"]
            for field in required_fields:
                if field not in author:
                    raise ValueError(f'Author must contain "{field}" field')

            valid_author_types = ["person", "bot", "agent"]
            if author["type"] not in valid_author_types:
                raise ValueError(f"Author type must be one of: {valid_author_types}")

        return v

    def get_entity_id(self) -> str:
        """Get entity ID safely."""
        return self.entity.get("id", "")

    def get_entity_type(self) -> str:
        """Get entity type safely."""
        return self.entity.get("type", "")

    def is_page_event(self) -> bool:
        """Check if this is a page-related event."""
        return self.get_entity_type() == "page"

    def is_create_event(self) -> bool:
        """Check if this is a creation event."""
        return self.type.endswith(".created")

    def is_update_event(self) -> bool:
        """Check if this is an update event."""
        return self.type.endswith(".updated")
