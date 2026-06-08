"""CLI entry point for Notion DB operations."""

import argparse
import json
import sys

from notion_db import add_page, field_exists, list_schema


def cmd_check(args: argparse.Namespace) -> None:
    exists = field_exists(args.key, args.value)
    status = "EXISTS" if exists else "NOT FOUND"
    print(f"[{status}] '{args.key}' = '{args.value}'")
    sys.exit(0 if exists else 1)


def cmd_add(args: argparse.Namespace) -> None:
    try:
        properties = json.loads(args.properties)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON for properties — {e}", file=sys.stderr)
        sys.exit(2)

    page = add_page(properties)
    print(f"Created page: {page['url']}")


def cmd_schema(_args: argparse.Namespace) -> None:
    schema = list_schema()
    for name, ptype in schema.items():
        print(f"  {name}: {ptype}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="notion-db",
        description="Query and upsert a Notion Database",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # check subcommand
    p_check = sub.add_parser("check", help="Check if a field value exists")
    p_check.add_argument("key", help="Property name (e.g. Name)")
    p_check.add_argument("value", help="Value to look for")
    p_check.set_defaults(func=cmd_check)

    # add subcommand
    p_add = sub.add_parser("add", help="Add a new row to the database")
    p_add.add_argument(
        "properties",
        help='JSON object of property name→value pairs, e.g. \'{"Name":"Alice","Age":30}\'',
    )
    p_add.set_defaults(func=cmd_add)

    # schema subcommand
    p_schema = sub.add_parser("schema", help="List database property names and types")
    p_schema.set_defaults(func=cmd_schema)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
