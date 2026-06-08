"""Notion Database query and upsert utilities."""

import os
from typing import Any

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

# notion-client v3 defaults to 2025-09-03 which dropped /databases/{id}/query.
# Pin to the stable 2022-06-28 API that still exposes properties + query.
_NOTION_VERSION = "2022-06-28"

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        token = os.environ["NOTION_TOKEN"]
        _client = Client(auth=token, notion_version=_NOTION_VERSION)
    return _client


def _get_database_id() -> str:
    return os.environ["NOTION_DATABASE_ID"]


def _query_database(filter_obj: dict | None = None) -> list[dict]:
    """Run a database query and return all matching page objects."""
    client = _get_client()
    db_id = _get_database_id()
    body: dict[str, Any] = {}
    if filter_obj:
        body["filter"] = filter_obj

    result = client.request(
        path=f"databases/{db_id}/query",
        method="POST",
        body=body,
    )
    return result.get("results", [])


def field_exists(field_key: str, field_value: Any) -> bool:
    """Check if a row exists where field_key equals field_value.

    Args:
        field_key: The property name to search (e.g. "id", "url").
        field_value: The value to match against.

    Returns:
        True if at least one matching row exists, False otherwise.
    """
    schema = list_schema()
    if field_key not in schema:
        raise ValueError(f"Property '{field_key}' not found in database schema.")

    prop_type = schema[field_key]

    if prop_type == "title":
        filter_obj = {"property": field_key, "title": {"equals": str(field_value)}}
    elif prop_type == "rich_text":
        filter_obj = {"property": field_key, "rich_text": {"equals": str(field_value)}}
    elif prop_type == "number":
        filter_obj = {"property": field_key, "number": {"equals": field_value}}
    elif prop_type == "checkbox":
        filter_obj = {"property": field_key, "checkbox": {"equals": bool(field_value)}}
    elif prop_type == "select":
        filter_obj = {"property": field_key, "select": {"equals": str(field_value)}}
    elif prop_type == "url":
        filter_obj = {"property": field_key, "url": {"equals": str(field_value)}}
    elif prop_type == "email":
        filter_obj = {"property": field_key, "email": {"equals": str(field_value)}}
    elif prop_type == "phone_number":
        filter_obj = {"property": field_key, "phone_number": {"equals": str(field_value)}}
    else:
        raise ValueError(f"field_exists does not support property type '{prop_type}'.")

    pages = _query_database(filter_obj)
    return len(pages) > 0


def add_page(properties: dict[str, Any]) -> dict:
    """Add a new page (row) to the database.

    Args:
        properties: A dict mapping property names to plain Python values.
                    Strings, numbers, booleans, and lists of strings (for
                    multi_select) are all supported.

    Returns:
        The created page object from the Notion API.

    Example:
        add_page({
            "id": "PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK",
            "playlist_name": "市井豪門",
            "genre": "drama",
            "spoken_language": ["Taigi"],
            "caption_language": ["Mandarin"],
            "caption_kind": "CC",
            "url": "https://youtube.com/playlist?list=PL02zpjjwMEjp_X-66jIMYOtgdgK46rNsK",
        })
    """
    client = _get_client()
    db_id = _get_database_id()
    schema = list_schema()

    notion_props: dict[str, Any] = {}
    for key, value in properties.items():
        if key not in schema:
            raise ValueError(f"Property '{key}' not found in database schema.")
        notion_props[key] = _encode_property(schema[key], value)

    response = client.pages.create(
        parent={"database_id": db_id},
        properties=notion_props,
    )
    return response


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


def list_schema() -> dict[str, str]:
    """Return a mapping of property names → types for the configured database."""
    client = _get_client()
    db_meta = client.databases.retrieve(database_id=_get_database_id())
    return {name: meta["type"] for name, meta in db_meta["properties"].items()}
