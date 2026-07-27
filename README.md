# GeoMessages

A backend service for working with geographic points and messages.

Built with Django REST Framework and PostGIS, it allows users to create map points, attach messages to them, and search for nearby points and messages within a specified radius using efficient PostGIS spatial queries (`ST_DWithin` via the ORM `distance_lte` lookup on a `geography` field with a GiST index).

## Tech Stack

- Python 3.12
- Django 5
- Django REST Framework + django-filter
- GeoDjango + djangorestframework-gis
- PostgreSQL 16 + PostGIS 3.4
- Docker / Docker Compose

## Data Model

- **GeoPoint** — a geographic point containing:
  - `name`
  - `description`
  - `location` (`PointField(geography=True, srid=4326)` with a GiST index)
  - `created_by`
  - `created_at`
  - `updated_at`

- **Message** — a message associated with a point (`ForeignKey` to `GeoPoint`):
  - `text`
  - `author`
  - `created_at`

## Quick Start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

After the containers are running:

```bash
docker compose exec web python manage.py createsuperuser
```

The API will be available at:

- `http://localhost:8000/api/`

The Django admin interface will be available at:

- `http://localhost:8000/admin/`

## Running Without Docker

You'll need the GDAL, GEOS, and PROJ system libraries installed, along with a running PostgreSQL instance with the PostGIS extension enabled.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure your database credentials
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

If the PostGIS extension has not yet been installed in your database, execute the following SQL command once:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

> **Note:** Django migrations do not automatically install the PostGIS extension.

## Authentication

The project uses both `TokenAuthentication` and `SessionAuthentication`.

- Read operations (`GET`) are available to everyone.
- Write operations (`POST`, `PUT`, `PATCH`, `DELETE`) require authentication via `IsAuthenticatedOrReadOnly`.

To obtain an authentication token:

```bash
curl -X POST http://localhost:8000/api-auth/login/ ...
```

Or create one manually:

```bash
python manage.py drf_create_token <username>
```

Include the token in subsequent requests:

```
Authorization: Token <your_token>
```

## API

### Geo Points

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/points/` | List all points (pagination, `?search=` supported) |
| POST | `/api/points/` | Create a new point |
| GET | `/api/points/{id}/` | Retrieve point details with nested messages |
| PUT/PATCH | `/api/points/{id}/` | Update a point |
| DELETE | `/api/points/{id}/` | Delete a point |
| GET | `/api/points/{id}/messages/` | List messages for a point |
| POST | `/api/points/{id}/messages/` | Add a message to a point |

### Create a Point

```bash
curl -X POST http://localhost:8000/api/points/ \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Kremlin",
        "description": "Tourist attraction",
        "lat": 55.7520,
        "lon": 37.6175
      }'
```

### Add a Message to a Point

```bash
curl -X POST http://localhost:8000/api/points/1/messages/ \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{
        "text": "Great place for taking photos!"
      }'
```

### Messages (Flat Access)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/messages/?point={id}` | List messages (optionally filtered by point) |
| POST | `/api/messages/` | Create a message (`point` field is required) |
| GET/PUT/DELETE | `/api/messages/{id}/` | Retrieve, update, or delete a message |

### Search Within a Radius

```
GET /api/search/?lat=55.7522&lon=37.6156&radius_m=2000&q=photo&limit=50
```

#### Query Parameters

- `lat`, `lon` — user's coordinates (**required**)
- `radius_m` — search radius in meters (default: `1000`, maximum: `100000`; configurable via `GEO_SEARCH_DEFAULT_RADIUS_M` and `GEO_SEARCH_MAX_RADIUS_M`)
- `q` — optional text filter matching point names, descriptions, and message text
- `limit` — maximum number of results returned in each list (default: `50`, maximum: `200`)

### Example Response

```json
{
  "query": {
    "lat": 55.7522,
    "lon": 37.6156,
    "radius_m": 2000,
    "q": null
  },
  "points": [
    {
      "id": 1,
      "name": "Kremlin",
      "latitude": 55.752,
      "longitude": 37.6175,
      "distance_m": 120.96,
      "messages_count": 1
    }
  ],
  "messages": [
    {
      "id": 1,
      "point": 1,
      "text": "Great place for taking photos!",
      "distance_m": 120.96
    }
  ]
}
```

Both points and messages are sorted by their distance from the specified coordinates.

Spatial filtering is performed using PostGIS `ST_DWithin` on a `geography` field backed by a GiST index, ensuring fast query performance even with large datasets.

## Project Verification

The project has been verified using:

- `python manage.py check`
- `makemigrations`
- `migrate`

All API endpoints have been tested end-to-end, including:

- Creating points
- Creating messages
- Nested and flat endpoints
- Radius-based search
- Text filtering
- Query parameter validation

For local testing without PostgreSQL, SQLite with SpatiaLite was used as a temporary spatial backend. The production Docker configuration uses the full `postgis/postgis:16-3.4` image.

## Possible Improvements

- Pagination and caching for large-scale geospatial searches.
- PostgreSQL full-text search (`SearchVector`) instead of `icontains` for the `q` parameter.
- Restrict editing and deletion so that only the author of a point or message can modify it.
- Rate limiting for the `/api/search/` endpoint.
