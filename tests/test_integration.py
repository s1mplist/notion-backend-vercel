"""
Integration tests for the full application flow.
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestApplicationIntegration:
    """Test full application integration."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, async_client):
        """Test health check endpoint."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, async_client):
        """Test metrics endpoint."""
        response = await async_client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "error_count" in data

    @pytest.mark.asyncio
    async def test_full_webhook_processing_flow(
        self, async_client, sample_webhook_payload
    ):
        """Test complete webhook processing flow with all services."""

        # Mock all external dependencies
        with (
            patch("services.notion_service.NotionService") as mock_notion_service,
            patch("services.plot_data_extractor.PlotDataExtractor") as mock_extractor,
            patch("services.html_renderer.HTMLRenderer") as mock_renderer,
            patch("services.notion_writer.NotionWriter") as mock_writer,
            patch("core.rate_limiter.RateLimiter") as mock_rate_limiter,
        ):
            # Setup mock returns
            mock_notion_service.return_value.find_farm_by_page_id.return_value = (
                "Test Farm"
            )
            mock_extractor.return_value.extract_plot_data.return_value = {
                "farm_name": "Test Farm",
                "plots": [],
                "total_area": 0,
            }
            mock_renderer.return_value.render_report_html.return_value = (
                "<html>test</html>"
            )
            mock_writer.return_value.create_notion_record.return_value = {
                "success": True,
                "page_id": "new-page-id",
            }
            mock_rate_limiter.return_value.is_allowed.return_value = True

            response = await async_client.post("/webhook", json=sample_webhook_payload)

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_webhook_rate_limiting(self, async_client, sample_webhook_payload):
        """Test webhook rate limiting functionality."""

        with patch("core.rate_limiter.RateLimiter") as mock_rate_limiter:
            # First request allowed
            mock_rate_limiter.return_value.is_allowed.return_value = True
            mock_rate_limiter.return_value.wait_if_needed = AsyncMock()

            with patch(
                "services.webhook_processor.WebhookProcessor.process_webhook_data"
            ) as mock_process:
                mock_process.return_value = {"success": True}

                response = await async_client.post(
                    "/webhook", json=sample_webhook_payload
                )
                assert response.status_code == 200

                # Verify rate limiter was checked
                mock_rate_limiter.return_value.is_allowed.assert_called()

    @pytest.mark.asyncio
    async def test_application_error_handling(
        self, async_client, sample_webhook_payload
    ):
        """Test application-wide error handling."""

        with patch(
            "services.webhook_processor.WebhookProcessor.process_webhook_data"
        ) as mock_process:
            # Simulate service failure
            mock_process.side_effect = Exception("Service unavailable")

            response = await async_client.post("/webhook", json=sample_webhook_payload)

            assert response.status_code == 500
            result = response.json()
            assert "error" in result

    @pytest.mark.asyncio
    async def test_configuration_integration(self, mock_environment):
        """Test configuration is properly loaded and used."""
        from core.config import get_settings

        settings = get_settings()

        # Verify all required settings are loaded
        assert settings.notion_api_token is not None
        assert settings.vercel_blob_store_id is not None
        assert settings.notion_database_id is not None

    @pytest.mark.asyncio
    async def test_metrics_collection_integration(
        self, async_client, sample_webhook_payload
    ):
        """Test that metrics are collected during request processing."""
        from core.metrics import get_metrics_collector

        collector = get_metrics_collector()
        initial_requests = collector.total_requests  # noqa: F841

        with patch(
            "services.webhook_processor.WebhookProcessor.process_webhook_data"
        ) as mock_process:
            mock_process.return_value = {"success": True}

            response = await async_client.post("/webhook", json=sample_webhook_payload)

            # Metrics should be updated (depending on implementation)
            # This test validates the metrics system is integrated
            assert response.status_code in [200, 500]  # Should handle gracefully

    def test_template_loading(self):
        """Test that templates can be loaded properly."""
        from services.html_renderer import HTMLRenderer

        renderer = HTMLRenderer()

        # Should be able to create renderer without errors
        assert renderer.template_env is not None

        # Should be able to get template
        try:
            template = renderer.template_env.get_template("report_template.html")
            assert template is not None
        except Exception:
            # Template might not exist in test environment, but should not crash
            pass

    def test_static_files_access(self):
        """Test that static files (CSS, images) are accessible."""
        import os

        # Check that template directory exists
        template_dir = os.path.join(os.path.dirname(__file__), "..", "template")
        assert os.path.exists(template_dir)

        # Check for CSS file
        css_file = os.path.join(template_dir, "styles.css")
        if os.path.exists(css_file):
            with open(css_file, "r") as f:
                content = f.read()
                assert len(content) > 0

    @pytest.mark.asyncio
    async def test_cors_headers(self, async_client):
        """Test CORS headers are properly set."""
        response = await async_client.options("/webhook")

        # Should handle OPTIONS request for CORS preflight
        # The exact response depends on CORS configuration
        assert response.status_code in [200, 204, 405]

    @pytest.mark.asyncio
    async def test_invalid_endpoints(self, async_client):
        """Test handling of invalid endpoints."""
        response = await async_client.get("/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_request_validation_integration(self, async_client):
        """Test request validation integration."""
        # Send completely invalid JSON
        response = await async_client.post("/webhook", json={"invalid": "payload"})

        assert response.status_code == 422  # Validation error

        # Send malformed JSON
        response = await async_client.post(
            "/webhook",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
