# API

REST API for the BlueHub platform, built with FastAPI.

## Versioning

- **v1/** - API version 1 (current)
  - Client endpoints
  - Admin endpoints
  - Webhook endpoints
  - Module-specific endpoints

## Design Principles

- All endpoints return JSON
- Authentication via JWT Bearer tokens
- Request/response validation with Pydantic
- Auto-generated OpenAPI documentation at `/docs`