# Event Analytics API

Production-style event ingestion and analytics service built with FastAPI, PostgreSQL, Docker, and Alembic.

## Features
- Event ingestion (`POST /events`)
- Filtered queries with pagination (`GET /events`)
- Aggregations (`GET /analytics/counts`)
- Time-series analytics (`GET /analytics/timeseries`)
- Dockerized local development
- Alembic migrations
- Automated tests with pytest

## Run locally
```bash
docker compose up --build
docker compose exec api alembic upgrade head
