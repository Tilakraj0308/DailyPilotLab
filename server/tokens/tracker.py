"""
Token Usage Tracker Service.
Handles request trace creation, timeline step logging, total aggregation,
and database persistence.
"""

import uuid
import json
import time
from typing import Optional, Dict, Any, List
from db.dbConnection import get_dict_cursor
from .cost_engine import calculate_token_cost

class TokenTracker:
    @staticmethod
    def start_trace(
        user_id: str,
        request_type: str = "chat",
        model: str = "gpt-4o-mini",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Initialize a new token usage request trace.
        Returns trace_id (UUID string).
        """
        trace_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata or {})
        
        try:
            with get_dict_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.token_usage_traces 
                    (id, user_id, session_id, request_type, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd, status, metadata)
                    VALUES (%s, %s, %s, %s, %s, 0, 0, 0, 0.000000, 'in_progress', %s)
                    """,
                    (trace_id, user_id, session_id, request_type, model, metadata_json)
                )
        except Exception as e:
            print(f"[TokenTracker] Error starting trace {trace_id}: {e}")
            
        return trace_id

    @staticmethod
    def add_timeline_step(
        trace_id: str,
        step_number: int,
        name: str,
        event_type: str = "llm_call",
        model: Optional[str] = "gpt-4o-mini",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        duration_ms: int = 0,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Record a timeline event step for a trace (e.g. LLM iteration, tool call, prompt assembly).
        Calculates step cost and updates cumulative trace totals.
        """
        total_tokens = prompt_tokens + completion_tokens
        step_cost = calculate_token_cost(model or "gpt-4o-mini", prompt_tokens, completion_tokens)
        details_json = json.dumps(details or {})
        
        try:
            with get_dict_cursor() as cur:
                # 1. Insert timeline step
                cur.execute(
                    """
                    INSERT INTO public.token_usage_timeline 
                    (trace_id, step_number, event_type, name, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd, duration_ms, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        trace_id, step_number, event_type, name, model,
                        prompt_tokens, completion_tokens, total_tokens,
                        step_cost, duration_ms, details_json
                    )
                )
                
                # 2. Increment trace totals
                cur.execute(
                    """
                    UPDATE public.token_usage_traces
                    SET prompt_tokens = prompt_tokens + %s,
                        completion_tokens = completion_tokens + %s,
                        total_tokens = total_tokens + %s,
                        estimated_cost_usd = estimated_cost_usd + %s,
                        duration_ms = duration_ms + %s
                    WHERE id = %s
                    """,
                    (prompt_tokens, completion_tokens, total_tokens, step_cost, duration_ms, trace_id)
                )
        except Exception as e:
            print(f"[TokenTracker] Error logging step for trace {trace_id}: {e}")

    @staticmethod
    def finalize_trace(
        trace_id: str,
        duration_ms: Optional[int] = None,
        status: str = "completed",
        metadata_update: Optional[Dict[str, Any]] = None
    ):
        """
        Finalize a trace, updating final duration and status.
        """
        try:
            with get_dict_cursor() as cur:
                if duration_ms is not None and duration_ms > 0:
                    cur.execute(
                        """
                        UPDATE public.token_usage_traces
                        SET status = %s, duration_ms = %s
                        WHERE id = %s
                        """,
                        (status, duration_ms, trace_id)
                    )
                else:
                    cur.execute(
                        """
                        UPDATE public.token_usage_traces
                        SET status = %s
                        WHERE id = %s
                        """,
                        (status, trace_id)
                    )
                
                if metadata_update:
                    cur.execute(
                        """
                        UPDATE public.token_usage_traces
                        SET metadata = metadata || %s::jsonb
                        WHERE id = %s
                        """,
                        (json.dumps(metadata_update), trace_id)
                    )
        except Exception as e:
            print(f"[TokenTracker] Error finalizing trace {trace_id}: {e}")

    @staticmethod
    def get_user_stats(user_id: str) -> Dict[str, Any]:
        """
        Retrieve aggregate stats for user token usage including overall,
        today, yesterday, past 7 days, past 30 days, and daily breakdown history.
        """
        with get_dict_cursor() as cur:
            # 1. Overall stats
            cur.execute(
                """
                SELECT 
                    COUNT(id) as total_requests,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0.0) as total_cost_usd,
                    COALESCE(AVG(duration_ms), 0) as avg_duration_ms
                FROM public.token_usage_traces
                WHERE user_id = %s
                """,
                (user_id,)
            )
            overview = cur.fetchone() or {}

            # 2. Today stats (since 00:00:00 UTC)
            cur.execute(
                """
                SELECT 
                    COUNT(id) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0.0) as cost_usd
                FROM public.token_usage_traces
                WHERE user_id = %s AND created_at >= CURRENT_DATE AT TIME ZONE 'UTC'
                """,
                (user_id,)
            )
            today_stats = cur.fetchone() or {}

            # 3. Yesterday stats
            cur.execute(
                """
                SELECT 
                    COUNT(id) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0.0) as cost_usd
                FROM public.token_usage_traces
                WHERE user_id = %s 
                  AND created_at >= (CURRENT_DATE - INTERVAL '1 day') AT TIME ZONE 'UTC'
                  AND created_at < CURRENT_DATE AT TIME ZONE 'UTC'
                """,
                (user_id,)
            )
            yesterday_stats = cur.fetchone() or {}

            # 4. Past 7 days stats
            cur.execute(
                """
                SELECT 
                    COUNT(id) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0.0) as cost_usd
                FROM public.token_usage_traces
                WHERE user_id = %s AND created_at >= NOW() - INTERVAL '7 days'
                """,
                (user_id,)
            )
            past_7d_stats = cur.fetchone() or {}

            # 5. Past 30 days stats
            cur.execute(
                """
                SELECT 
                    COUNT(id) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0.0) as cost_usd
                FROM public.token_usage_traces
                WHERE user_id = %s AND created_at >= NOW() - INTERVAL '30 days'
                """,
                (user_id,)
            )
            past_30d_stats = cur.fetchone() or {}

            # 6. Daily history breakdown (last 30 days)
            cur.execute(
                """
                SELECT 
                    DATE(created_at AT TIME ZONE 'UTC')::text as date,
                    COUNT(id) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0.0) as cost_usd
                FROM public.token_usage_traces
                WHERE user_id = %s AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(created_at AT TIME ZONE 'UTC')
                ORDER BY date DESC
                """,
                (user_id,)
            )
            daily_history = cur.fetchall() or []
            
            # Breakdown by model
            cur.execute(
                """
                SELECT 
                    model,
                    COUNT(id) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0.0) as cost_usd
                FROM public.token_usage_traces
                WHERE user_id = %s
                GROUP BY model
                ORDER BY total_tokens DESC
                """,
                (user_id,)
            )
            model_breakdown = cur.fetchall()
            
            # Breakdown by request_type
            cur.execute(
                """
                SELECT 
                    request_type,
                    COUNT(id) as request_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(estimated_cost_usd), 0.0) as cost_usd
                FROM public.token_usage_traces
                WHERE user_id = %s
                GROUP BY request_type
                ORDER BY total_tokens DESC
                """,
                (user_id,)
            )
            type_breakdown = cur.fetchall()

            return {
                "overview": {
                    "total_requests": int(overview.get("total_requests", 0)),
                    "total_tokens": int(overview.get("total_tokens", 0)),
                    "prompt_tokens": int(overview.get("total_prompt_tokens", 0)),
                    "completion_tokens": int(overview.get("total_completion_tokens", 0)),
                    "total_cost_usd": float(overview.get("total_cost_usd", 0.0)),
                    "avg_duration_ms": round(float(overview.get("avg_duration_ms", 0)), 1)
                },
                "today": {
                    "request_count": int(today_stats.get("request_count", 0)),
                    "total_tokens": int(today_stats.get("total_tokens", 0)),
                    "prompt_tokens": int(today_stats.get("prompt_tokens", 0)),
                    "completion_tokens": int(today_stats.get("completion_tokens", 0)),
                    "cost_usd": float(today_stats.get("cost_usd", 0.0)),
                },
                "yesterday": {
                    "request_count": int(yesterday_stats.get("request_count", 0)),
                    "total_tokens": int(yesterday_stats.get("total_tokens", 0)),
                    "prompt_tokens": int(yesterday_stats.get("prompt_tokens", 0)),
                    "completion_tokens": int(yesterday_stats.get("completion_tokens", 0)),
                    "cost_usd": float(yesterday_stats.get("cost_usd", 0.0)),
                },
                "past_7_days": {
                    "request_count": int(past_7d_stats.get("request_count", 0)),
                    "total_tokens": int(past_7d_stats.get("total_tokens", 0)),
                    "prompt_tokens": int(past_7d_stats.get("prompt_tokens", 0)),
                    "completion_tokens": int(past_7d_stats.get("completion_tokens", 0)),
                    "cost_usd": float(past_7d_stats.get("cost_usd", 0.0)),
                },
                "past_30_days": {
                    "request_count": int(past_30d_stats.get("request_count", 0)),
                    "total_tokens": int(past_30d_stats.get("total_tokens", 0)),
                    "prompt_tokens": int(past_30d_stats.get("prompt_tokens", 0)),
                    "completion_tokens": int(past_30d_stats.get("completion_tokens", 0)),
                    "cost_usd": float(past_30d_stats.get("cost_usd", 0.0)),
                },
                "daily_history": [
                    {
                        "date": str(d.get("date")),
                        "request_count": int(d.get("request_count", 0)),
                        "total_tokens": int(d.get("total_tokens", 0)),
                        "prompt_tokens": int(d.get("prompt_tokens", 0)),
                        "completion_tokens": int(d.get("completion_tokens", 0)),
                        "cost_usd": float(d.get("cost_usd", 0.0)),
                    }
                    for d in daily_history
                ],
                "by_model": model_breakdown,
                "by_type": type_breakdown
            }

    @staticmethod
    def get_user_traces(
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        request_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List paginated token usage traces for a user.
        """
        with get_dict_cursor() as cur:
            if request_type and request_type.lower() != "all":
                cur.execute(
                    """
                    SELECT id, session_id, request_type, model, prompt_tokens, 
                           completion_tokens, total_tokens, estimated_cost_usd, 
                           duration_ms, status, metadata, created_at
                    FROM public.token_usage_traces
                    WHERE user_id = %s AND request_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, request_type, limit, offset)
                )
            else:
                cur.execute(
                    """
                    SELECT id, session_id, request_type, model, prompt_tokens, 
                           completion_tokens, total_tokens, estimated_cost_usd, 
                           duration_ms, status, metadata, created_at
                    FROM public.token_usage_traces
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset)
                )
            return cur.fetchall()

    @staticmethod
    def get_trace_timeline(trace_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full details and timeline steps for a specific request trace.
        Validates ownership via user_id.
        """
        with get_dict_cursor() as cur:
            # 1. Fetch main trace
            cur.execute(
                """
                SELECT id, user_id, session_id, request_type, model, prompt_tokens, 
                       completion_tokens, total_tokens, estimated_cost_usd, 
                       duration_ms, status, metadata, created_at
                FROM public.token_usage_traces
                WHERE id = %s AND user_id = %s
                """,
                (trace_id, user_id)
            )
            trace = cur.fetchone()
            if not trace:
                return None
                
            # 2. Fetch timeline events
            cur.execute(
                """
                SELECT id, step_number, event_type, name, model, prompt_tokens, 
                       completion_tokens, total_tokens, estimated_cost_usd, 
                       duration_ms, details, created_at
                FROM public.token_usage_timeline
                WHERE trace_id = %s
                ORDER BY step_number ASC
                """,
                (trace_id,)
            )
            timeline = cur.fetchall()
            
            trace["timeline"] = timeline
            return trace


def get_token_tracker() -> TokenTracker:
    return TokenTracker()
