"""Gradio GUI for querying and inserting rows into a Notion Database."""

import os

import gradio as gr

from notion_db import NotionDB, _encode_property

# Pre-fill credentials from .env if available so users don't have to retype them
_DEFAULT_TOKEN = os.environ.get("NOTION_TOKEN", "")
_DEFAULT_DB_ID = os.environ.get("NOTION_DATABASE_ID", "")


def _make_db(token: str, db_id: str) -> NotionDB:
    if not token or not db_id:
        raise ValueError("請填入 Integration Token 與 Database ID。")
    return NotionDB(token.strip(), db_id.strip())


def on_connect(token: str, db_id: str):
    try:
        db = _make_db(token, db_id)
        schema = db.list_schema()
        rows = [[name, ptype] for name, ptype in schema.items()]
        status = f"✅ 連線成功，共 {len(schema)} 個欄位。"
        return status, rows, schema
    except Exception as e:
        return f"❌ 連線失敗：{e}", [], {}


def on_check(token: str, db_id: str, schema: dict, field: str, value: str):
    if not field:
        return "請選擇欄位。"
    if value is None:
        value = ""
    try:
        db = _make_db(token, db_id)
        exists = db.field_exists(field, value)
        if exists:
            return f"✅ EXISTS — '{field}' = '{value}' 存在於資料庫中。"
        return f"❌ NOT FOUND — '{field}' = '{value}' 不存在。"
    except Exception as e:
        return f"❌ 錯誤：{e}"


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Notion DB Manager", theme=gr.themes.Soft()) as demo:

        # ── Persistent state ────────────────────────────────────────────────
        token_state = gr.State(_DEFAULT_TOKEN)
        dbid_state = gr.State(_DEFAULT_DB_ID)
        schema_state = gr.State({})

        # ── Header ──────────────────────────────────────────────────────────
        gr.Markdown("# Notion Database Manager")
        gr.Markdown("輸入 Integration Token 與 Database ID 後點擊 **Connect**，即可查詢或新增資料。")

        # ── Connection bar ───────────────────────────────────────────────────
        with gr.Row():
            token_input = gr.Textbox(
                label="Integration Token",
                type="password",
                placeholder="ntn_...",
                value=_DEFAULT_TOKEN,
                scale=3,
            )
            dbid_input = gr.Textbox(
                label="Database ID",
                placeholder="32-character hex string",
                value=_DEFAULT_DB_ID,
                scale=3,
            )
            connect_btn = gr.Button("Connect", variant="primary", scale=1)

        connect_status = gr.Textbox(label="狀態", interactive=False)

        # ── Tabs ─────────────────────────────────────────────────────────────
        with gr.Tabs():

            # ── Tab 1: Schema ──────────────────────────────────────────────
            with gr.Tab("Schema"):
                gr.Markdown("連線後顯示資料庫所有欄位與型別。")
                schema_table = gr.Dataframe(
                    headers=["欄位名稱", "型別"],
                    datatype=["str", "str"],
                    interactive=False,
                    wrap=True,
                )

            # ── Tab 2: Check ───────────────────────────────────────────────
            with gr.Tab("Check — 查詢"):
                gr.Markdown("確認某欄位的值是否已存在於資料庫。")

                @gr.render(inputs=schema_state)
                def render_check(schema: dict):
                    if not schema:
                        gr.Markdown("*請先 Connect 連線。*")
                        return

                    field_choices = list(schema.keys())
                    field_dd = gr.Dropdown(label="欄位", choices=field_choices)
                    value_box = gr.Textbox(label="搜尋值")
                    check_btn = gr.Button("查詢", variant="primary")
                    check_result = gr.Textbox(label="結果", interactive=False)

                    check_btn.click(
                        on_check,
                        inputs=[token_state, dbid_state, schema_state, field_dd, value_box],
                        outputs=[check_result],
                    )

            # ── Tab 3: Add ─────────────────────────────────────────────────
            with gr.Tab("Add — 新增"):
                gr.Markdown("依照欄位型別填入值後點擊 **新增**。")
                gr.Markdown(
                    "> `multi_select` 欄位請以逗號分隔多個選項，例如：`Taigi, Mandarin`"
                )

                @gr.render(inputs=[schema_state, token_state, dbid_state])
                def render_add(schema: dict, token: str, db_id: str):
                    if not schema:
                        gr.Markdown("*請先 Connect 連線。*")
                        return

                    components: dict[str, gr.components.Component] = {}

                    for name, ptype in schema.items():
                        label = f"{name}  `{ptype}`"
                        match ptype:
                            case "checkbox":
                                components[name] = gr.Checkbox(label=label)
                            case "number":
                                components[name] = gr.Number(label=label)
                            case "multi_select":
                                components[name] = gr.Textbox(
                                    label=label,
                                    placeholder="選項A, 選項B",
                                )
                            case "date":
                                components[name] = gr.Textbox(
                                    label=label,
                                    placeholder="YYYY-MM-DD",
                                )
                            case _:
                                components[name] = gr.Textbox(label=label)

                    add_btn = gr.Button("新增", variant="primary")
                    add_result = gr.Textbox(label="結果", interactive=False)

                    def do_add(*values):
                        props: dict = {}
                        for (name, ptype), val in zip(schema.items(), values):
                            # Skip empty optional fields
                            if val is None or val == "" or val == []:
                                continue
                            if ptype == "multi_select" and isinstance(val, str):
                                items = [v.strip() for v in val.split(",") if v.strip()]
                                if items:
                                    props[name] = items
                            elif ptype == "number":
                                props[name] = val
                            elif ptype == "checkbox":
                                props[name] = bool(val)
                            else:
                                props[name] = str(val)

                        if not props:
                            return "請至少填入一個欄位。"
                        try:
                            db = _make_db(token, db_id)
                            page = db.add_page(props)
                            return f"✅ 新增成功：{page['url']}"
                        except Exception as e:
                            return f"❌ 錯誤：{e}"

                    add_btn.click(
                        do_add,
                        inputs=list(components.values()),
                        outputs=[add_result],
                    )

        # ── Connect wiring ───────────────────────────────────────────────────
        def _on_connect(token, db_id):
            status, rows, schema = on_connect(token, db_id)
            return status, rows, token, db_id, schema

        connect_btn.click(
            _on_connect,
            inputs=[token_input, dbid_input],
            outputs=[connect_status, schema_table, token_state, dbid_state, schema_state],
        )

    return demo


if __name__ == "__main__":
    build_app().launch()
