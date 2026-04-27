"""OpenAI tool schema formatting (arrays must include items)."""

from services.chat_service import _format_tools_for_openai


def test_format_tools_array_includes_string_items():
    defs = [
        {
            "name": "gmail_create_draft",
            "description": "x",
            "parameters": {
                "to": {"type": "list", "required": False, "description": "To addresses"},
            },
        }
    ]
    out = _format_tools_for_openai(defs)
    to_prop = out[0]["function"]["parameters"]["properties"]["to"]
    assert to_prop["type"] == "array"
    assert to_prop["items"] == {"type": "string"}


def test_format_tools_array_respects_explicit_items():
    defs = [
        {
            "name": "t",
            "description": "y",
            "parameters": {
                "ids": {
                    "type": "list",
                    "items": {"type": "int"},
                    "required": True,
                    "description": "ids",
                },
            },
        }
    ]
    out = _format_tools_for_openai(defs)
    assert out[0]["function"]["parameters"]["properties"]["ids"]["items"] == {"type": "integer"}
