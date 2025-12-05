"""
Conversation Logger for RMS Assistant

Logs all conversations verbatim for:
- Review and iteration
- Training data collection
- Memory/retrieval in future
- Feedback collection

Storage format: JSONL (one JSON object per line)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid


class ConversationLogger:
    """Logs conversations to JSONL files organized by date."""

    def __init__(self, storage_dir: str = "conversations"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_id: Optional[str] = None
        self.current_session_file: Optional[Path] = None

    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start a new conversation session."""
        self.current_session_id = f"session_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Create date folder
        date_folder = self.storage_dir / datetime.now().strftime("%Y-%m-%d")
        date_folder.mkdir(exist_ok=True)

        self.current_session_file = date_folder / f"{self.current_session_id}.jsonl"

        # Log session start
        self._write_event({
            "event": "session_start",
            "session_id": self.current_session_id,
            "metadata": metadata or {}
        })

        # Update index
        self._update_index()

        print(f"[ConversationLogger] Started session: {self.current_session_id}")
        return self.current_session_id

    def log_message(
        self,
        role: str,
        content: str,
        tab_state: Optional[Dict[str, Any]] = None,
        tools_called: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a single message in the conversation."""
        if not self.current_session_file:
            self.start_session()

        event = {
            "event": "message",
            "role": role,
            "content": content,
        }

        if tab_state:
            event["tab_state"] = {
                "url": tab_state.get("url", ""),
                "title": tab_state.get("title", "")
            }

        if tools_called:
            event["tools_called"] = tools_called

        if metadata:
            event["metadata"] = metadata

        self._write_event(event)

    def log_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        success: bool = True,
        duration_ms: Optional[float] = None
    ) -> None:
        """Log a tool call with its result."""
        if not self.current_session_file:
            self.start_session()

        event = {
            "event": "tool_call",
            "tool": tool_name,
            "args": args,
            "result": str(result)[:1000],  # Truncate long results
            "success": success
        }

        if duration_ms is not None:
            event["duration_ms"] = round(duration_ms, 2)

        self._write_event(event)

    def log_tool_error(
        self,
        tool_name: str,
        args: Dict[str, Any],
        error: str,
        traceback_str: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """Log a tool error with traceback."""
        if not self.current_session_file:
            self.start_session()

        event = {
            "event": "tool_error",
            "tool": tool_name,
            "args": args,
            "error": error,
            "success": False
        }

        if traceback_str:
            event["traceback"] = traceback_str[:2000]  # Truncate long tracebacks

        if duration_ms is not None:
            event["duration_ms"] = round(duration_ms, 2)

        self._write_event(event)

    def log_api_request(
        self,
        url: str,
        method: str,
        status_code: Optional[Any] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Log an external API request."""
        if not self.current_session_file:
            self.start_session()

        event = {
            "event": "api_request",
            "url": url,
            "method": method,
            "success": success
        }

        if status_code is not None:
            event["status_code"] = status_code

        if duration_ms is not None:
            event["duration_ms"] = round(duration_ms, 2)

        if error:
            event["error"] = error

        self._write_event(event)

    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error that occurred during the conversation."""
        if not self.current_session_file:
            self.start_session()

        self._write_event({
            "event": "error",
            "error": error,
            "context": context or {}
        })

    def log_feedback(
        self,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        message_ref: Optional[str] = None
    ) -> None:
        """Log user feedback on a response."""
        if not self.current_session_file:
            return

        self._write_event({
            "event": "feedback",
            "rating": rating,
            "comment": comment,
            "message_ref": message_ref
        })

    def end_session(self, summary: Optional[str] = None) -> None:
        """End the current session."""
        if not self.current_session_file:
            return

        self._write_event({
            "event": "session_end",
            "summary": summary
        })

        print(f"[ConversationLogger] Ended session: {self.current_session_id}")
        self.current_session_id = None
        self.current_session_file = None

    def _write_event(self, event: Dict[str, Any]) -> None:
        """Write an event to the current session file."""
        if not self.current_session_file:
            return

        event["ts"] = datetime.utcnow().isoformat() + "Z"

        with open(self.current_session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _update_index(self) -> None:
        """Update the sessions index file."""
        index_file = self.storage_dir / "index.json"

        # Load existing index
        if index_file.exists():
            with open(index_file, "r") as f:
                index = json.load(f)
        else:
            index = {"sessions": []}

        # Add current session
        index["sessions"].append({
            "session_id": self.current_session_id,
            "file": str(self.current_session_file.relative_to(self.storage_dir)),
            "started": datetime.utcnow().isoformat() + "Z"
        })

        # Keep last 1000 sessions in index
        index["sessions"] = index["sessions"][-1000:]

        with open(index_file, "w") as f:
            json.dump(index, f, indent=2)

    # =========================================================================
    # Reading/Analysis Methods (for iteration)
    # =========================================================================

    def get_recent_sessions(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get list of recent sessions."""
        index_file = self.storage_dir / "index.json"
        if not index_file.exists():
            return []

        with open(index_file, "r") as f:
            index = json.load(f)

        return index.get("sessions", [])[-100:]  # Last 100 sessions

    def read_session(self, session_file: str) -> List[Dict[str, Any]]:
        """Read all events from a session file."""
        file_path = self.storage_dir / session_file
        if not file_path.exists():
            return []

        events = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        return events

    def get_all_messages(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get all messages from recent sessions for analysis."""
        messages = []

        for session in self.get_recent_sessions(days):
            events = self.read_session(session["file"])
            for event in events:
                if event.get("event") == "message":
                    event["session_id"] = session["session_id"]
                    messages.append(event)

        return messages

    def get_tool_usage_stats(self, days: int = 7) -> Dict[str, int]:
        """Get statistics on tool usage."""
        tool_counts = {}

        for session in self.get_recent_sessions(days):
            events = self.read_session(session["file"])
            for event in events:
                if event.get("event") == "tool_call":
                    tool = event.get("tool", "unknown")
                    tool_counts[tool] = tool_counts.get(tool, 0) + 1

        return tool_counts

    def search_conversations(self, query: str, days: int = 7) -> List[Dict[str, Any]]:
        """Search conversations for a specific term."""
        results = []
        query_lower = query.lower()

        for session in self.get_recent_sessions(days):
            events = self.read_session(session["file"])
            for event in events:
                if event.get("event") == "message":
                    content = event.get("content", "").lower()
                    if query_lower in content:
                        results.append({
                            "session_id": session["session_id"],
                            "role": event.get("role"),
                            "content": event.get("content"),
                            "ts": event.get("ts")
                        })

        return results


# Global logger instance
_logger: Optional[ConversationLogger] = None


def get_logger() -> ConversationLogger:
    """Get or create the conversation logger."""
    global _logger
    if _logger is None:
        # Store in agent directory
        storage_path = Path(__file__).parent.parent / "conversations"
        _logger = ConversationLogger(str(storage_path))
    return _logger
