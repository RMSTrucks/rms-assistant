"""
Observability Module for RMS Assistant

Provides instrumentation for tool execution to enable debugging and iteration.

The key insight: We can't see inside the agent (it's opaque), but we CAN
instrument our tools. By wrapping every tool method, we capture:
- What tool was called
- With what arguments
- What it returned (or what error occurred)
- How long it took

This lets us distinguish between:
- Tool was called and succeeded
- Tool was called and failed
- Tool was NEVER called (agent hallucinated)

Dual instrumentation:
1. Local JSONL logs - full detail for debugging
2. LangWatch spans - for dashboard visualization
"""

import time
import traceback
from functools import wraps
from typing import Any, Callable

import langwatch


def observe_tool(func: Callable) -> Callable:
    """
    Decorator to log all tool executions.

    Apply to every tool method that should be observable.
    Logs to the conversation logger with:
    - tool_name: ClassName.method_name
    - args: kwargs passed to the tool
    - result: return value (truncated)
    - duration_ms: execution time
    - success: True/False

    Usage:
        from app.observability import observe_tool

        class MyTools(Toolkit):
            @observe_tool
            def my_tool(self, query: str) -> str:
                ...
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Import here to avoid circular imports
        from app.conversation_logger import get_logger

        tool_name = f"{self.__class__.__name__}.{func.__name__}"
        logger = get_logger()
        start = time.time()

        # Log start (useful for long-running tools)
        print(f"[Observability] Tool start: {tool_name}")

        # Create LangWatch span for this tool call
        with langwatch.span(type="tool", name=tool_name) as span:
            try:
                # Update span with input
                span.update(input={"args": kwargs})

                result = func(self, *args, **kwargs)
                duration_ms = (time.time() - start) * 1000

                # Update span with output
                span.update(output={"result": str(result)[:500]})

                # Log successful execution to local JSONL
                logger.log_tool_call(
                    tool_name=tool_name,
                    args=kwargs,
                    result=result,
                    success=True,
                    duration_ms=duration_ms
                )

                print(f"[Observability] Tool complete: {tool_name} ({duration_ms:.1f}ms)")
                return result

            except Exception as e:
                duration_ms = (time.time() - start) * 1000

                # Update span with error
                span.update(error=str(e))

                # Log failed execution with full traceback to local JSONL
                logger.log_tool_error(
                    tool_name=tool_name,
                    args=kwargs,
                    error=str(e),
                    traceback_str=traceback.format_exc(),
                    duration_ms=duration_ms
                )

                print(f"[Observability] Tool ERROR: {tool_name} - {e}")
                raise

    return wrapper


def observe_api_call(func: Callable) -> Callable:
    """
    Decorator for HTTP API calls.

    Use this on methods that make external API requests.
    Logs URL, method, status code, and duration.

    Usage:
        @observe_api_call
        def _make_request(self, method, endpoint, **kwargs):
            ...
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        from app.conversation_logger import get_logger

        logger = get_logger()
        start = time.time()

        # Try to extract URL info from args/kwargs
        method = args[0] if args else kwargs.get("method", "?")
        endpoint = args[1] if len(args) > 1 else kwargs.get("endpoint", "?")
        url = f"{getattr(self, 'base_url', '')}/{endpoint}"

        try:
            result = func(self, *args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            # Extract status code if result is a dict with it
            status_code = None
            if isinstance(result, dict):
                if "error" in result:
                    status_code = "error"
                else:
                    status_code = "ok"

            logger.log_api_request(
                url=url,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
                success=True
            )

            return result

        except Exception as e:
            duration_ms = (time.time() - start) * 1000

            logger.log_api_request(
                url=url,
                method=method,
                status_code="exception",
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            )

            raise

    return wrapper
