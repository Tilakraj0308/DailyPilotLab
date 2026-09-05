# import asyncio
# from services.chat_service import get_user_tools, _format_tools_for_openai
# import json

# def main():
#     tools = [
#         {
#             "name": "create_google_task",
#             "description": "Create a new task",
#             "crud_type": "create",
#             "parameters": {
#                 "title": {"type": "str", "required": True, "description": "Title"},
#                 "notes": {"type": "str", "required": False, "description": "Notes"}
#             }
#         }
#     ]
#     formatted = _format_tools_for_openai(tools)
#     print(json.dumps(formatted, indent=2))

# if __name__ == "__main__":
#     main()
