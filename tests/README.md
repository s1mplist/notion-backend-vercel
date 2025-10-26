# Test Files

This directory contains comprehensive tests for the Notion Backend Vercel project.

## Test Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_webhook.py` - Webhook model validation and processing tests
- `test_core.py` - Core functionality tests (config, rate limiting, metrics)
- `test_services.py` - Service layer tests (Notion, HTML rendering, etc.)
- `test_integration.py` - Full application integration tests
- `run_tests.py` - Test runner script

## Running Tests

### Run all tests:
```bash
uv run python tests/run_tests.py
```

### Run specific test file:
```bash
uv run pytest tests/test_webhook.py -v
```

### Run with coverage:
```bash
uv run pytest --cov=src --cov-report=term-missing tests/
```

### Run tests in specific group:
```bash
uv run --group tests pytest tests/ -v
```

## Test Coverage

The test suite aims for >80% code coverage and includes:

- ✅ Model validation tests
- ✅ Service layer unit tests
- ✅ Integration tests
- ✅ Error handling tests
- ✅ Configuration tests
- ✅ Rate limiting tests
- ✅ Metrics collection tests

## Fixtures

The `conftest.py` file provides several useful fixtures:

- `test_client` - FastAPI test client
- `async_client` - Async HTTP client
- `mock_notion_client` - Mocked Notion API client
- `sample_webhook_payload` - Valid webhook data for testing
- `sample_plot_data` - Sample plot data structure
- `mock_environment` - Mocked environment variables

## Test Environment

Tests automatically mock external dependencies and environment variables to ensure they run reliably in any environment.

The tests use the following environment variables (automatically mocked):
- `NOTION_API_TOKEN`
- `VERCEL_BLOB_STORE_ID`
- `VERCEL_BLOB_TOKEN`
- `NOTION_DATABASE_ID`