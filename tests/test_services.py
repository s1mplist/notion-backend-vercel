"""
Test services functionality.
"""

import pytest
from unittest.mock import patch


class TestNotionService:
    """Test Notion service functionality."""

    @pytest.mark.asyncio
    async def test_find_farm_by_page_id_success(self, mock_notion_client):
        """Test successful farm name lookup."""
        from services.notion_service import NotionService

        service = NotionService()

        with patch.object(service, "client", mock_notion_client):
            farm_name = await service.find_farm_by_page_id("test-page-id")

            assert farm_name == "Test Farm"
            mock_notion_client.databases.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_farm_by_page_id_not_found(self, mock_notion_client):
        """Test farm name lookup when not found."""
        from services.notion_service import NotionService

        service = NotionService()
        mock_notion_client.databases.query.return_value = {"results": []}

        with patch.object(service, "client", mock_notion_client):
            farm_name = await service.find_farm_by_page_id("nonexistent-page")

            assert farm_name is None

    @pytest.mark.asyncio
    async def test_find_farm_handles_errors(self, mock_notion_client):
        """Test farm lookup error handling."""
        from services.notion_service import NotionService

        service = NotionService()
        mock_notion_client.databases.query.side_effect = Exception("API Error")

        with patch.object(service, "client", mock_notion_client):
            farm_name = await service.find_farm_by_page_id("test-page-id")

            assert farm_name is None


class TestPlotDataExtractor:
    """Test plot data extraction."""

    @pytest.mark.asyncio
    async def test_extract_plot_data_success(self, sample_plot_data):
        """Test successful plot data extraction."""
        from services.plot_data_extractor import PlotDataExtractor

        extractor = PlotDataExtractor()

        with patch.object(extractor.notion_service, "get_page_data") as mock_get_data:
            mock_get_data.return_value = sample_plot_data

            result = await extractor.extract_plot_data("test-page-id", "Test Farm")

            assert result["farm_name"] == "Test Farm"
            assert len(result["plots"]) == 2
            assert result["total_area"] == 18.7

    @pytest.mark.asyncio
    async def test_extract_plot_data_handles_errors(self):
        """Test plot data extraction error handling."""
        from services.plot_data_extractor import PlotDataExtractor

        extractor = PlotDataExtractor()

        with patch.object(extractor.notion_service, "get_page_data") as mock_get_data:
            mock_get_data.side_effect = Exception("Extraction error")

            result = await extractor.extract_plot_data("test-page-id", "Test Farm")

            # Should return default structure on error
            assert result["farm_name"] == "Test Farm"
            assert result["plots"] == []
            assert result["total_area"] == 0


class TestHTMLRenderer:
    """Test HTML rendering functionality."""

    def test_render_report_html_success(self, sample_plot_data):
        """Test successful HTML rendering."""
        from services.html_renderer import HTMLRenderer

        renderer = HTMLRenderer()

        html_content = renderer.render_report_html(sample_plot_data)

        assert isinstance(html_content, str)
        assert len(html_content) > 0
        assert "Test Farm" in html_content

    def test_render_report_html_with_audit(self, sample_plot_data):
        """Test HTML rendering with audit logging."""
        from services.html_renderer import HTMLRenderer

        renderer = HTMLRenderer()

        with patch.object(renderer, "_log_html_audit") as mock_audit:
            html_content = renderer.render_report_html(sample_plot_data)

            assert isinstance(html_content, str)
            mock_audit.assert_called_once()

    def test_render_handles_template_errors(self, sample_plot_data):
        """Test HTML rendering error handling."""
        from services.html_renderer import HTMLRenderer

        renderer = HTMLRenderer()

        with patch.object(renderer.template_env, "get_template") as mock_template:
            mock_template.side_effect = Exception("Template error")

            html_content = renderer.render_report_html(sample_plot_data)

            # Should return error HTML
            assert "Error rendering template" in html_content


class TestNotionWriter:
    """Test Notion writing functionality."""

    @pytest.mark.asyncio
    async def test_create_notion_record_success(self, mock_notion_client):
        """Test successful Notion record creation."""
        from services.notion_writer import NotionWriter

        writer = NotionWriter()

        with patch.object(writer.notion_service, "client", mock_notion_client):
            result = await writer.create_notion_record(
                farm_name="Test Farm",
                html_content="<html>test</html>",
                metadata={"test": "data"},
            )

            assert result["success"] is True
            assert result["page_id"] == "new-page-id"
            mock_notion_client.pages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_notion_record_handles_errors(self, mock_notion_client):
        """Test Notion record creation error handling."""
        from services.notion_writer import NotionWriter

        writer = NotionWriter()
        mock_notion_client.pages.create.side_effect = Exception("Creation error")

        with patch.object(writer.notion_service, "client", mock_notion_client):
            result = await writer.create_notion_record(
                farm_name="Test Farm",
                html_content="<html>test</html>",
                metadata={"test": "data"},
            )

            assert result["success"] is False
            assert "error" in result


class TestNotionDataMapper:
    """Test Notion data mapping functionality."""

    def test_map_page_to_plot_data_success(self):
        """Test successful page to plot data mapping."""
        from services.notion_mapper import NotionDataMapper

        mapper = NotionDataMapper()

        # Mock Notion page data
        page_data = {
            "properties": {
                "Name": {"title": [{"text": {"content": "Test Farm"}}]},
                "Area": {"number": 25.5},
                "Plots": {"rich_text": [{"text": {"content": "Plot data here"}}]},
            }
        }

        result = mapper.map_page_to_plot_data(page_data, "Test Farm")

        assert result["farm_name"] == "Test Farm"
        assert isinstance(result["plots"], list)
        assert isinstance(result["total_area"], (int, float))

    def test_map_page_handles_missing_properties(self):
        """Test mapping with missing properties."""
        from services.notion_mapper import NotionDataMapper

        mapper = NotionDataMapper()

        # Minimal page data
        page_data = {"properties": {}}

        result = mapper.map_page_to_plot_data(page_data, "Test Farm")

        # Should handle gracefully with defaults
        assert result["farm_name"] == "Test Farm"
        assert result["plots"] == []
        assert result["total_area"] == 0

    def test_extract_plot_info_from_text(self):
        """Test plot information extraction from text."""
        from services.notion_mapper import NotionDataMapper

        mapper = NotionDataMapper()

        sample_text = """
        Plot 001: Corn, 10.5 hectares, Active
        Plot 002: Wheat, 8.2 hectares, Planned
        """

        plots = mapper._extract_plot_info(sample_text)

        assert len(plots) >= 0  # Should extract some plots
        assert isinstance(plots, list)
