import os
import json
import base64
import tempfile
import datetime
import yaml
from pathlib import Path
from typing import AsyncGenerator, Any, Union
from openai import AsyncOpenAI

from connectors.tool_registry import get_user_tools
from connectors.tool_executor import execute_tool
from tasks.tools import execute_task_tool, TASK_TOOL_NAMES
from services.ai_factory import AIFactory

default_client = AsyncOpenAI(api_key=os.getenv("OPENAPI"))

def _get_async_client(user_id: str = None) -> AsyncOpenAI:
    if user_id:
        return AIFactory.get_async_openai_client(user_id)
    return default_client

def _get_user_model(user_id: str = None, default_model: str = "gpt-4o-mini") -> str:
    if user_id:
        settings = AIFactory.get_user_ai_settings(user_id)
        return settings.get("model", default_model)
    return default_model

async def transcribe_audio(audio_b64: str, user_id: str = None) -> str:
    """Decode base64 WAV -> call Whisper -> return transcript."""
    client = _get_async_client(user_id)
    audio_bytes = base64.b64decode(audio_b64)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _format_tools_for_openai(tools_def: list[dict]) -> list[dict]:
    """Convert our tool definitions to OpenAI's expected JSON format."""
    out = []
    for t in tools_def:
        props = {}
        required = []
        raw_params = t.get("parameters") or {}
        
        for p_name, p_def in raw_params.items():
            # Convert custom type names to JSON Schema
            p_type = p_def.get("type", "string")
            if p_type == "int":
                p_type = "integer"
            elif p_type == "bool":
                p_type = "boolean"
            elif p_type == "str":
                p_type = "string"
            elif p_type == "float":
                p_type = "number"
            elif p_type == "dict":
                p_type = "object"
            elif p_type == "list":
                p_type = "array"

            prop: dict[str, Any] = {
                "type": p_type,
                "description": p_def.get("description", ""),
            }
            # OpenAI requires JSON Schema "items" for array-valued parameters.
            if p_type == "array":
                raw_items = p_def.get("items")
                if isinstance(raw_items, dict) and raw_items.get("type"):
                    it = raw_items["type"]
                    if it == "int":
                        it = "integer"
                    elif it == "bool":
                        it = "boolean"
                    elif it == "str":
                        it = "string"
                    elif it == "float":
                        it = "number"
                    prop["items"] = {"type": it}
                else:
                    prop["items"] = {"type": "string"}

            props[p_name] = prop
            if p_def.get("required"):
                required.append(p_name)
                
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required
                }
            }
        })
    return out


async def stream_chat(messages: list[dict], user_id: str) -> AsyncGenerator[Union[str, list[dict], dict], None]:
    """
    Stream GPT-4o-mini tokens.
    Dynamically injects tools the user has connected and authorized.
    If the LLM calls a tool, handles the execution locally, appends the result,
    and resumes streaming the response.
    Includes complete token traceability tracking per request.
    """
    from tokens import TokenTracker
    import time
    
    client = _get_async_client(user_id)
    model_name_default = _get_user_model(user_id, "gpt-4o-mini")
    
    request_start_time = time.time()
    system_tools = get_user_tools(user_id)
    openai_tools = _format_tools_for_openai(system_tools) if system_tools else None
    
    current_messages = list(messages)  # Copy to allow appending during loop
    
    # Load and format system prompt
    prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "system_prompt.yaml"
    if prompt_path.exists():
        with open(prompt_path, "r") as f:
            prompt_data = yaml.safe_load(f)
        
        # Retrieve user's personal state context
        from services.user_service import get_personal_state
        personal_state_dict = get_personal_state(user_id) if user_id else {}
        personal_state_str = json.dumps(personal_state_dict, indent=2) if personal_state_dict else "Not provided"

        now_local = datetime.datetime.now().astimezone()
        tz_str = now_local.strftime("%Y-%m-%d %H:%M:%S %z")
        tz_name = now_local.tzname()
        formatted_date = f"{tz_str} ({tz_name})" if tz_name else tz_str

        system_prompt_text = prompt_data.get("template", "").format(
            current_date=formatted_date,
            user_profile=personal_state_str
        )
        if current_messages and current_messages[0].get("role") == "system":
            current_messages[0]["content"] += f"\n\n{system_prompt_text}"
        else:
            current_messages.insert(0, {"role": "system", "content": system_prompt_text})

    # Start Token Traceability Record
    first_user_msg = next((m.get("content", "") for m in reversed(current_messages) if m.get("role") == "user"), "")
    trace_id = TokenTracker.start_trace(
        user_id=user_id,
        request_type="chat",
        model=model_name_default,
        metadata={"user_prompt_snippet": first_user_msg[:120]}
    )
    
    iteration_count = 0
    MAX_ITERATIONS = 5
    timeline_step_counter = 0

    try:
        while True:
            iteration_count += 1
            if iteration_count > MAX_ITERATIONS:
                error_msg = "\n\n*(System: Maximum tool execution iterations reached to prevent token exhaustion.)*"
                yield error_msg
                current_messages.append({"role": "assistant", "content": error_msg})
                break
                
            model_name = model_name_default
            kwargs: dict[str, Any] = {
                "model": model_name,
                "messages": current_messages,
                "stream": True,
                "stream_options": {"include_usage": True},
                "max_tokens": 1024,
            }
            if openai_tools:
                kwargs["tools"] = openai_tools

            iter_start_time = time.time()
            stream = await client.chat.completions.create(**kwargs)
            
            # Accumulators for tool calls
            tool_calls_accumulator = {}
            assistant_content = ""
            usage_info = None
            
            async for chunk in stream:
                # Check for usage stats chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    usage_info = chunk.usage
                    
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # 1. Normal text stream
                if delta.content:
                    assistant_content += delta.content
                    yield delta.content
                    
                # 2. Tool call arguments stream
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_accumulator:
                            tool_calls_accumulator[idx] = {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.function.name, "arguments": ""}
                            }
                        if tc.function.arguments:
                            tool_calls_accumulator[idx]["function"]["arguments"] += tc.function.arguments

            iter_duration_ms = int((time.time() - iter_start_time) * 1000)
            finish_reason = chunk.choices[0].finish_reason if (chunk and chunk.choices) else None

            # Extract token counts
            cached_tokens = 0
            if usage_info:
                p_tokens = getattr(usage_info, "prompt_tokens", 0)
                c_tokens = getattr(usage_info, "completion_tokens", 0)
                prompt_details = getattr(usage_info, "prompt_tokens_details", None)
                if prompt_details:
                    # In python sdk, it might be a pydantic model or dict
                    cached_tokens = getattr(prompt_details, "cached_tokens", 0) if hasattr(prompt_details, "cached_tokens") else (prompt_details.get("cached_tokens", 0) if isinstance(prompt_details, dict) else 0)
            else:
                # Fallback estimation if stream usage missing
                p_tokens = sum(len(str(m.get("content", ""))) // 4 for m in current_messages)
                c_tokens = len(assistant_content) // 4
                
            timeline_step_counter += 1
            TokenTracker.add_timeline_step(
                trace_id=trace_id,
                step_number=timeline_step_counter,
                name=f"LLM Iteration {iteration_count} ({model_name})",
                event_type="llm_call",
                model=model_name,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                duration_ms=iter_duration_ms,
                details={
                    "finish_reason": finish_reason,
                    "has_tool_calls": bool(tool_calls_accumulator),
                    "assistant_text_len": len(assistant_content)
                }
            )

            # If the LLM did not call any tools, we are completely done.
            if finish_reason != "tool_calls" and not tool_calls_accumulator:
                if assistant_content:
                    current_messages.append({
                        "role": "assistant",
                        "content": assistant_content,
                        "metadata": {
                            "model_name": model_name,
                            "prompt_tokens": p_tokens,
                            "cached_tokens": cached_tokens,
                            "completion_tokens": c_tokens
                        }
                    })
                break
                
            # The LLM wants to execute tools. Let's process them.
            final_tool_calls = [v for k, v in sorted(tool_calls_accumulator.items())]
            
            # Append the assistant's intention to call tools to the history
            assistant_msg = {
                "role": "assistant",
                "tool_calls": final_tool_calls,
                "metadata": {
                    "model_name": model_name,
                    "prompt_tokens": p_tokens,
                    "cached_tokens": cached_tokens,
                    "completion_tokens": c_tokens
                }
            }
            if assistant_content:
                assistant_msg["content"] = assistant_content
            current_messages.append(assistant_msg)
            
            # Execute each tool and append the result
            executed_calls_cache = {}  # Cache to prevent duplicate simultaneous executions
            for tc in final_tool_calls:
                tool_name = tc["function"]["name"]
                tool_args_str = tc["function"]["arguments"]
                call_signature = f"{tool_name}:{tool_args_str}"
                
                tool_start_time = time.time()
                
                if call_signature not in executed_calls_cache:
                    # Send a notification to the UI about the tool action only for the first unique call
                    yield {"type": "tool_call", "tool_name": tool_name, "tool_args": tool_args_str}
                
                if call_signature in executed_calls_cache:
                    result_str = executed_calls_cache[call_signature]
                else:
                    try:
                        args = json.loads(tool_args_str)
                        # Route: first-party task tools bypass the connector executor
                        if tool_name in TASK_TOOL_NAMES:
                            result = execute_task_tool(user_id, tool_name, args)
                        else:
                            result = execute_tool(user_id, tool_name, args, triggered_by="ai_agent")
                            if isinstance(result, dict) and result.get("error_type") == "requires_reauth":
                                yield {
                                    "type": "reauth_required",
                                    "provider": result.get("provider"),
                                    "auth_url": result.get("auth_url"),
                                    "tool_name": tool_name,
                                }
                                TokenTracker.finalize_trace(trace_id=trace_id, status="interrupted")
                                return
                        result_str = json.dumps(result, default=str)
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})

                    executed_calls_cache[call_signature] = result_str
                
                tool_duration_ms = int((time.time() - tool_start_time) * 1000)
                timeline_step_counter += 1
                TokenTracker.add_timeline_step(
                    trace_id=trace_id,
                    step_number=timeline_step_counter,
                    name=f"Tool Execution: {tool_name}",
                    event_type="tool_execution",
                    model=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    duration_ms=tool_duration_ms,
                    details={
                        "tool_name": tool_name,
                        "tool_args": tool_args_str[:200],
                        "result_length": len(result_str)
                    }
                )

                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tool_name,
                    "content": result_str,
                })
                
            # Loop restarts with the tool results appended, sending it back to OpenAI

        total_duration_ms = int((time.time() - request_start_time) * 1000)
        TokenTracker.finalize_trace(trace_id=trace_id, duration_ms=total_duration_ms, status="completed")
    except Exception as e:
        total_duration_ms = int((time.time() - request_start_time) * 1000)
        TokenTracker.finalize_trace(trace_id=trace_id, duration_ms=total_duration_ms, status="error", metadata_update={"error": str(e)})
        raise e

    # Yield the full message history so it can be saved in the database
    yield current_messages

