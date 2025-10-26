"""
Test webhook processing functionality.
"""

import pytest
from unittest.mock import patch
from uuid import UUID
from datetime import datetime

from models.webhook import WebhookRequest


class TestWebhookModel:
    """Test webhook model validation."""

    def test_valid_webhook_request(self, sample_webhook_payload):
        """Test creating a valid webhook request."""
        webhook = WebhookRequest(**sample_webhook_payload)

        assert webhook.id == UUID("01234567-89ab-cdef-0123-456789abcdef")
        assert webhook.type == "page.created"
        assert webhook.get_entity_id() == "page-456"
        assert webhook.get_entity_type() == "page"
        assert webhook.is_page_event() is True
        assert webhook.is_create_event() is True
        assert webhook.is_update_event() is False

    def test_invalid_event_type(self, sample_webhook_payload):
        """Test validation of invalid event types."""
        # Invalid format - no dot
        sample_webhook_payload["type"] = "invalid"
        with pytest.raises(ValueError, match="Event type must be in format"):
            WebhookRequest(**sample_webhook_payload)

        # Invalid object type
        sample_webhook_payload["type"] = "invalid.created"
        with pytest.raises(ValueError, match="Object type must be one of"):
            WebhookRequest(**sample_webhook_payload)

        # Invalid action
        sample_webhook_payload["type"] = "page.invalid"
        with pytest.raises(ValueError, match="Action must be one of"):
            WebhookRequest(**sample_webhook_payload)

    def test_invalid_entity(self, sample_webhook_payload):
        """Test validation of invalid entity."""
        # Missing required fields
        sample_webhook_payload["entity"] = {"id": "test"}
        with pytest.raises(ValueError, match='Entity must contain "type" field'):
            WebhookRequest(**sample_webhook_payload)

        # Empty ID
        sample_webhook_payload["entity"] = {"id": "", "type": "page"}
        with pytest.raises(ValueError, match="Entity ID cannot be empty"):
            WebhookRequest(**sample_webhook_payload)

        # Invalid entity type
        sample_webhook_payload["entity"] = {"id": "test", "type": "invalid"}
        with pytest.raises(ValueError, match="Entity type must be one of"):
            WebhookRequest(**sample_webhook_payload)

    def test_invalid_authors(self, sample_webhook_payload):
        """Test validation of invalid authors."""
        # Empty authors list
        sample_webhook_payload["authors"] = []
        with pytest.raises(ValueError, match="List should have at least 1 item"):
            WebhookRequest(**sample_webhook_payload)

        # Invalid author structure
        sample_webhook_payload["authors"] = [{"id": "test"}]
        with pytest.raises(ValueError, match='Author must contain "type" field'):
            WebhookRequest(**sample_webhook_payload)

        # Invalid author type
        sample_webhook_payload["authors"] = [{"id": "test", "type": "invalid"}]
        with pytest.raises(ValueError, match="Author type must be one of"):
            WebhookRequest(**sample_webhook_payload)

    def test_attempt_number_validation(self, sample_webhook_payload):
        """Test attempt number validation."""
        # Too low
        sample_webhook_payload["attempt_number"] = 0
        with pytest.raises(ValueError):
            WebhookRequest(**sample_webhook_payload)

        # Too high
        sample_webhook_payload["attempt_number"] = 9
        with pytest.raises(ValueError):
            WebhookRequest(**sample_webhook_payload)

        # Valid range
        for num in range(1, 9):
            sample_webhook_payload["attempt_number"] = num
            webhook = WebhookRequest(**sample_webhook_payload)
            assert webhook.attempt_number == num


class TestWebhookProcessing:
    """Test webhook processing end-to-end."""

    @pytest.mark.asyncio
    async def test_webhook_endpoint_success(self, async_client, sample_webhook_payload):
        """Test successful webhook processing."""
        with patch(
            "services.webhook_processor.WebhookProcessor.process_webhook_data"
        ) as mock_process:
            mock_process.return_value = {
                "success": True,
                "page_id": "test-page-id",
                "message": "Successfully processed webhook",
            }

            response = await async_client.post("/webhook", json=sample_webhook_payload)

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "page_id" in result

    @pytest.mark.asyncio
    async def test_webhook_endpoint_invalid_payload(self, async_client):
        """Test webhook endpoint with invalid payload."""
        invalid_payload = {"invalid": "data"}

        response = await async_client.post("/webhook", json=invalid_payload)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_webhook_processing_error(self, async_client, sample_webhook_payload):
        """Test webhook processing with service error."""
        with patch(
            "services.webhook_processor.WebhookProcessor.process_webhook_data"
        ) as mock_process:
            mock_process.side_effect = Exception("Service error")

            response = await async_client.post("/webhook", json=sample_webhook_payload)

            assert response.status_code == 500
            result = response.json()
            assert "error" in result

    @pytest.mark.asyncio
    async def test_webhook_processor_farm_name_resolution(
        self, mock_notion_client, sample_webhook_payload
    ):
        """Test farm name resolution in webhook processor."""
        from services.webhook_processor import WebhookProcessor
        from models.webhook import WebhookRequest

        processor = WebhookProcessor()
        webhook_data = WebhookRequest(**sample_webhook_payload)

        with patch.object(processor, "notion_service") as mock_service:
            mock_service.get_database_title.return_value = "Test Farm"

            farm_name = await processor._resolve_farm_name(
                webhook_data, {"parent": {"database_id": "test-db-id"}}
            )
            assert farm_name == "Test Farm"

    @pytest.mark.asyncio
    async def test_webhook_processor_full_flow(self, sample_webhook_payload):
        """Test complete webhook processing flow."""
        from services.webhook_processor import WebhookProcessor
        from models.webhook import WebhookRequest

        processor = WebhookProcessor()
        webhook_data = WebhookRequest(**sample_webhook_payload)

        with (
            patch.object(processor, "notion_service") as mock_notion,
            patch.object(processor, "plot_extractor") as mock_extractor,
            patch.object(processor, "data_mapper") as mock_mapper,
        ):
            # Setup mocks to match actual method signatures
            mock_notion.get_page.return_value = {
                "id": "test-page-id",
                "parent": {"database_id": "test-db-id"},
            }
            mock_notion.get_database_title.return_value = "Test Farm"
            mock_extractor.extract_plots_data.return_value = {"plots": []}
            mock_mapper.map_to_report.return_value = {
                "farm_name": "Test Farm",
                "plots": [],
            }

            # Mock generation metadata
            from models.generation import GenerationMetadata

            gen_meta = GenerationMetadata(
                webhook_id=webhook_data.id,
                webhook_timestamp=webhook_data.timestamp,
                entity_id=webhook_data.entity.get("id"),
                generation_started_at=datetime.now(),
                generation_status="started",
            )

            result = await processor.process_webhook_data(gen_meta, webhook_data)

            # Verify the result structure
            assert isinstance(result, dict)

            # Verify services were called
            mock_notion.get_page.assert_called_once()
            mock_extractor.extract_plots_data.assert_called_once()
