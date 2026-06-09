"""Notion Database query and upsert utilities."""

import os
from typing import Any

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

# notion-client v3 defaults to 2025-09-03 which dropped /databases/{id}/query.
# Pin to the stable 2022-06-28 API that still exposes properties + query.
_NOTION_VERSION = "2022-06-28"


class NotionDB:
    """Client bound to a specific Notion integration token and database."""

    def __init__(self, token: str, database_id: str):
        self._client = Client(auth=token, notion_version=_NOTION_VERSION)
        self._db_id = database_id

    def list_schema(self) -> dict[str, str]:
        """Return a mapping of property names → types."""
        db_meta = self._client.databases.retrieve(database_id=self._db_id)
        return {name: meta["type"] for name, meta in db_meta["properties"].items()}

    def field_exists(self, field_key: str, field_value: Any) -> bool:
        """Return True if at least one row has field_key equal to field_value."""
        schema = self.list_schema()
        if field_key not in schema:
            raise ValueError(f"Property '{field_key}' not found in database schema.")

        prop_type = schema[field_key]
        filter_obj = self._build_filter(field_key, prop_type, field_value)
        pages = self._query(filter_obj)
        return len(pages) > 0

    def add_page(self, properties: dict[str, Any]) -> dict:
        """Insert a new row and return the created Notion page object."""
        schema = self.list_schema()
        notion_props: dict[str, Any] = {}
        for key, value in properties.items():
            if key not in schema:
                raise ValueError(f"Property '{key}' not found in database schema.")
            notion_props[key] = _encode_property(schema[key], value)

        return self._client.pages.create(
            parent={"database_id": self._db_id},
            properties=notion_props,
        )

    def _query(self, filter_obj: dict | None = None) -> list[dict]:
        body: dict[str, Any] = {}
        if filter_obj:
            body["filter"] = filter_obj
        result = self._client.request(
            path=f"databases/{self._db_id}/query",
            method="POST",
            body=body,
        )
        return result.get("results", [])

    @staticmethod
    def _build_filter(field_key: str, prop_type: str, field_value: Any) -> dict:
        match prop_type:
            case "title":
                return {"property": field_key, "title": {"equals": str(field_value)}}
            case "rich_text":
                return {"property": field_key, "rich_text": {"equals": str(field_value)}}
            case "number":
                return {"property": field_key, "number": {"equals": field_value}}
            case "checkbox":
                return {"property": field_key, "checkbox": {"equals": bool(field_value)}}
            case "select":
                return {"property": field_key, "select": {"equals": str(field_value)}}
            case "url":
                return {"property": field_key, "url": {"equals": str(field_value)}}
            case "email":
                return {"property": field_key, "email": {"equals": str(field_value)}}
            case "phone_number":
                return {"property": field_key, "phone_number": {"equals": str(field_value)}}
            case _:
                raise ValueError(f"field_exists does not support property type '{prop_type}'.")


def _encode_property(prop_type: str, value: Any) -> dict:
    """Convert a plain Python value to a Notion property object."""
    match prop_type:
        case "title":
            return {"title": [{"text": {"content": str(value)}}]}
        case "rich_text":
            return {"rich_text": [{"text": {"content": str(value)}}]}
        case "number":
            return {"number": value}
        case "checkbox":
            return {"checkbox": bool(value)}
        case "select":
            return {"select": {"name": str(value)}}
        case "multi_select":
            items = value if isinstance(value, list) else [value]
            return {"multi_select": [{"name": str(v)} for v in items]}
        case "email":
            return {"email": str(value)}
        case "url":
            return {"url": str(value)}
        case "phone_number":
            return {"phone_number": str(value)}
        case "date":
            if isinstance(value, dict):
                return {"date": value}
            return {"date": {"start": str(value)}}
        case _:
            raise ValueError(f"Unsupported property type: '{prop_type}'")


# ---------------------------------------------------------------------------
# Module-level helpers — read credentials from .env (used by the CLI)
# ---------------------------------------------------------------------------

def _env_db() -> NotionDB:
    return NotionDB(
        token=os.environ["NOTION_TOKEN"],
        database_id=os.environ["NOTION_DATABASE_ID"],
    )


def list_schema() -> dict[str, str]:
    return _env_db().list_schema()


def field_exists(field_key: str, field_value: Any) -> bool:
    return _env_db().field_exists(field_key, field_value)


def add_page(properties: dict[str, Any]) -> dict:
    return _env_db().add_page(properties)
