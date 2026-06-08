# notion-db-upsert

![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Notion](https://img.shields.io/badge/Notion-API-black?logo=notion&logoColor=white)
![Poetry](https://img.shields.io/badge/poetry-managed-60A5FA?logo=poetry&logoColor=white)

A lightweight Python CLI and library for querying and inserting rows into a [Notion](https://notion.so) Database via the official Notion API.

## Features

- Check whether a specific field value already exists in the database
- Insert a new row with arbitrary property values
- Inspect the database schema (property names and types) at any time
- Usable both as a **CLI tool** and as a **Python library**

## Requirements

- Python 3.11+
- [Poetry](https://python-poetry.org/) 2.x
- A Notion integration token with access to the target database

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:hungshinlee/notion-db-upsert.git
cd notion-db-upsert
```

### 2. Install dependencies

```bash
poetry install
```

### 3. Configure environment variables

Copy the example below into a `.env` file in the project root:

```dotenv
NOTION_TOKEN=your_integration_token_here
NOTION_DATABASE_ID=your_database_id_here
```

> **How to get these values**
>
> - **`NOTION_TOKEN`** — Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations), create an integration, and copy the *Internal Integration Token*.
> - **`NOTION_DATABASE_ID`** — Open the target database in Notion. The ID is the 32-character hex string in the page URL:  
>   `https://www.notion.so/<workspace>/<DATABASE_ID>?v=...`  
>   Make sure the integration has been added to the database via **Share → Invite**.

---

## CLI Usage

All commands are run with `poetry run python main.py <subcommand>`.

### `schema` — List database properties

```bash
poetry run python main.py schema
```

Example output:

```
  id: title
  playlist_name: rich_text
  channel_name: select
  genre: select
  spoken_language: multi_select
  caption_language: multi_select
  caption_kind: select
  url: url
  note: rich_text
```

---

### `check` — Check if a value exists

```bash
poetry run python main.py check <property_name> <value>
```

- Exits with code **`0`** if the value exists.
- Exits with code **`1`** if it does not.

This makes it easy to use in shell scripts:

```bash
# Example: check before inserting
if poetry run python main.py check id "PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK"; then
  echo "Already in database, skipping."
else
  echo "Not found, inserting..."
fi
```

Supported property types for `check`: `title`, `rich_text`, `number`, `checkbox`, `select`, `url`, `email`, `phone_number`.

---

### `add` — Insert a new row

```bash
poetry run python main.py add '<JSON object>'
```

Pass all property values as a single JSON object. Property names must match exactly what `schema` shows.

```bash
poetry run python main.py add '{
  "id": "PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK",
  "playlist_name": "市井豪門",
  "channel_name": "民視戲劇館 Formosa TV Dramas",
  "genre": "drama",
  "spoken_language": ["Taigi"],
  "caption_language": ["Mandarin"],
  "caption_kind": "CC",
  "url": "https://youtube.com/playlist?list=PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK",
  "note": ""
}'
```

On success, the URL of the newly created Notion page is printed:

```
Created page: https://app.notion.com/p/...
```

#### Value format by property type

| Notion type    | Expected Python value              | Example                          |
|----------------|------------------------------------|----------------------------------|
| `title`        | `str`                              | `"PL02zpjjwMEjp_..."`           |
| `rich_text`    | `str`                              | `"Some notes"`                  |
| `number`       | `int` or `float`                   | `42`                             |
| `checkbox`     | `bool`                             | `true`                           |
| `select`       | `str` (option name)                | `"drama"`                        |
| `multi_select` | `list[str]` (option names)         | `["Taigi", "Mandarin"]`         |
| `url`          | `str`                              | `"https://..."`                  |
| `email`        | `str`                              | `"user@example.com"`            |
| `phone_number` | `str`                              | `"+886912345678"`               |
| `date`         | `str` (ISO 8601) or `dict`         | `"2026-06-09"` or `{"start": "2026-06-09", "end": null}` |

---

## Library Usage

`notion_db.py` can be imported directly into your own scripts.

### Upsert pattern (check → add)

The most common use case: insert a row only if it does not already exist,
and report the outcome either way.

```python
from notion_db import field_exists, add_page

PLAYLIST = {
    "id": "PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK",
    "playlist_name": "市井豪門",
    "channel_name": "民視戲劇館 Formosa TV Dramas",
    "genre": "drama",
    "spoken_language": ["Taigi"],
    "caption_language": ["Mandarin"],
    "caption_kind": "CC",
    "url": "https://youtube.com/playlist?list=PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK",
}

if field_exists("id", PLAYLIST["id"]):
    print(f"[SKIP] '{PLAYLIST['id']}' already exists in the database.")
else:
    page = add_page(PLAYLIST)
    print(f"[ADDED] {page['url']}")
```

#### Batch upsert

When you have a list of items to sync, iterate and upsert each one:

```python
from notion_db import field_exists, add_page

playlists = [
    {
        "id": "PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK",
        "playlist_name": "市井豪門",
        "channel_name": "民視戲劇館 Formosa TV Dramas",
        "genre": "drama",
        "spoken_language": ["Taigi"],
        "caption_language": ["Mandarin"],
        "caption_kind": "CC",
        "url": "https://youtube.com/playlist?list=PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK",
    },
    {
        "id": "PLдругой",
        "playlist_name": "另一部劇",
        "channel_name": "台視",
        "genre": "drama",
        "spoken_language": ["Mandarin"],
        "caption_language": ["Mandarin"],
        "caption_kind": "CC",
        "url": "https://youtube.com/playlist?list=PLдругой",
    },
    # ... more items
]

added, skipped = 0, 0
for item in playlists:
    if field_exists("id", item["id"]):
        print(f"[SKIP]  {item['id']}")
        skipped += 1
    else:
        page = add_page(item)
        print(f"[ADDED] {item['id']} → {page['url']}")
        added += 1

print(f"\nDone — {added} added, {skipped} skipped.")
```

### Inspect schema programmatically

```python
from notion_db import list_schema

schema = list_schema()
# {"id": "title", "playlist_name": "rich_text", "genre": "select", ...}
for name, ptype in schema.items():
    print(f"{name}: {ptype}")
```

### API Reference

#### `field_exists(field_key, field_value) -> bool`

Returns `True` if at least one row in the database has the given property value.

| Parameter | Type  | Description |
|-----------|-------|-------------|
| `field_key` | `str` | Property name as shown in the schema |
| `field_value` | `Any` | Value to match |

Raises `ValueError` if the property name is not in the schema, or if the property type is not supported for querying.

#### `add_page(properties) -> dict`

Inserts a new row into the database and returns the raw Notion page object.

| Parameter | Type | Description |
|-----------|------|-------------|
| `properties` | `dict[str, Any]` | Property name → plain Python value pairs |

Raises `ValueError` if a property name is not found in the schema.

#### `list_schema() -> dict[str, str]`

Returns a `{property_name: property_type}` mapping for the configured database.

---

## Notes

- **Notion API version**: `notion-client` v3 defaults to the `2025-09-03` API, which removed the `databases/{id}/query` endpoint. This project pins to `2022-06-28` to retain full query support.
- **`.env` security**: The `.env` file is listed in `.gitignore` and will never be committed. Never share your `NOTION_TOKEN` publicly.
- **`select` / `multi_select` options**: If you specify an option name that does not yet exist in Notion, Notion will create it automatically.

## Project Structure

```
notion-db-upsert/
├── .env               # Local secrets (not committed)
├── .gitignore
├── pyproject.toml     # Poetry project definition
├── poetry.lock        # Pinned dependency versions
├── notion_db.py       # Core library: field_exists, add_page, list_schema
└── main.py            # CLI entry point
```

## License

MIT
