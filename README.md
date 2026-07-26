# GeoMessages

Backend-сервис для работы с географическими метками и сообщениями.
Django REST Framework + PostGIS. Позволяет создавать точки на карте,
привязывать к ним сообщения и искать контент (точки и сообщения) в
заданном радиусе от пользователя с помощью эффективных пространственных
запросов PostGIS (`ST_DWithin` через ORM-lookup `distance_lte` на
`geography`-поле + GiST-индекс).

## Стек

- Python 3.12, Django 5
- Django REST Framework + django-filter
- GeoDjango + djangorestframework-gis
- PostgreSQL 16 + PostGIS 3.4
- Docker / docker-compose

## Модель данных

- **GeoPoint** — географическая метка: `name`, `description`,
  `location` (`PointField(geography=True, srid=4326)`, с GiST-индексом),
  `created_by`, `created_at`, `updated_at`.
- **Message** — сообщение, привязанное к метке (`FK point`): `text`,
  `author`, `created_at`.

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose up --build
```

После старта:

```bash
docker compose exec web python manage.py createsuperuser
```

API будет доступно на `http://localhost:8000/api/`,
админка — на `http://localhost:8000/admin/`.

## Запуск без Docker

Нужны системные библиотеки GDAL/GEOS/PROJ и запущенный PostgreSQL с
расширением PostGIS.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # указать параметры своей БД
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

В самой базе один раз выполнить (миграция Django это не делает
автоматически, если PostGIS расширение ещё не установлено в БД):

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

## Аутентификация

Используется `TokenAuthentication` + `SessionAuthentication`. Чтение
(`GET`) доступно всем, запись (`POST/PUT/PATCH/DELETE`) — только
аутентифицированным пользователям (`IsAuthenticatedOrReadOnly`).

Получить токен:

```bash
curl -X POST http://localhost:8000/api-auth/login/ ...
# либо создать токен вручную:
python manage.py drf_create_token <username>
```

Дальше передавать заголовок:

```
Authorization: Token <ваш_токен>
```

## API

### Геометки

| Метод | URL                          | Описание                                   |
|-------|------------------------------|---------------------------------------------|
| GET   | `/api/points/`               | Список меток (пагинация, `?search=`)        |
| POST  | `/api/points/`                | Создать метку                              |
| GET   | `/api/points/{id}/`          | Детали метки + вложенные сообщения         |
| PUT/PATCH | `/api/points/{id}/`       | Обновить метку                             |
| DELETE | `/api/points/{id}/`         | Удалить метку                              |
| GET   | `/api/points/{id}/messages/` | Список сообщений метки                     |
| POST  | `/api/points/{id}/messages/` | Добавить сообщение к метке                 |

Создание метки:

```bash
curl -X POST http://localhost:8000/api/points/ \
  -H "Authorization: Token <token>" -H "Content-Type: application/json" \
  -d '{"name": "Кремль", "description": "Достопримечательность", "lat": 55.7520, "lon": 37.6175}'
```

Добавление сообщения к метке:

```bash
curl -X POST http://localhost:8000/api/points/1/messages/ \
  -H "Authorization: Token <token>" -H "Content-Type: application/json" \
  -d '{"text": "Отличное место для фото!"}'
```

### Сообщения (плоский доступ)

| Метод | URL                              | Описание                                  |
|-------|-----------------------------------|--------------------------------------------|
| GET   | `/api/messages/?point={id}`      | Список сообщений, опц. фильтр по метке    |
| POST  | `/api/messages/`                 | Создать сообщение (обязательно поле `point`)|
| GET/PUT/DELETE | `/api/messages/{id}/`   | Просмотр/изменение/удаление                |

### Поиск в радиусе от пользователя

```
GET /api/search/?lat=55.7522&lon=37.6156&radius_m=2000&q=фото&limit=50
```

Параметры:

- `lat`, `lon` — координаты пользователя (обязательны)
- `radius_m` — радиус поиска в метрах (по умолчанию 1000, максимум 100000,
  настраивается через `GEO_SEARCH_DEFAULT_RADIUS_M` /
  `GEO_SEARCH_MAX_RADIUS_M`)
- `q` — необязательный текстовый фильтр (по названию/описанию метки и
  тексту сообщений)
- `limit` — максимум объектов в каждом списке (по умолчанию 50, максимум 200)

Ответ:

```json
{
  "query": {"lat": 55.7522, "lon": 37.6156, "radius_m": 2000, "q": null},
  "points": [
    {"id": 1, "name": "Кремль", "latitude": 55.752, "longitude": 37.6175,
     "distance_m": 120.96, "messages_count": 1, ...}
  ],
  "messages": [
    {"id": 1, "point": 1, "text": "Отличное место для фото!",
     "distance_m": 120.96, ...}
  ]
}
```

Точки и сообщения отсортированы по возрастанию расстояния от заданных
координат. Поиск выполняется через `ST_DWithin` на geography-поле с
GiST-индексом, поэтому остаётся быстрым даже на больших объёмах данных.

## Проверка проекта

Код проверен: `python manage.py check`, `makemigrations`/`migrate` и
сквозной прогон всех эндпоинтов (создание точек, сообщений, вложенные
и плоские маршруты, поиск по радиусу с текстовым фильтром и валидацией
границ параметров) — на SQLite+SpatiaLite в качестве временного бэкенда
для локальной проверки без поднятия PostgreSQL. В `docker-compose.yml`
используется полноценный `postgis/postgis:16-3.4`.

## Возможные доработки

- Пагинация/кэширование геопоиска для очень больших наборов данных.
- Полнотекстовый поиск (`SearchVector`) вместо `icontains` для `q`.
- Права на редактирование/удаление только автору метки/сообщения.
- Rate limiting на `/api/search/`.
