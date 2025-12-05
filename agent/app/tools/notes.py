"""
Notes Tools

Persistent memory for the RMS agent - remembers things across sessions.
"""

import os
from pathlib import Path
from datetime import datetime
from agno.tools.toolkit import Toolkit
from typing import Optional

from app.observability import observe_tool


class NotesTools(Toolkit):
    """Tools for persisting notes and memories across sessions."""

    def __init__(self, notes_dir: Optional[str] = None):
        """
        Initialize notes tools.

        Args:
            notes_dir: Directory for notes storage (default: agent/notes/)
        """
        super().__init__(name="notes")

        if notes_dir:
            self.notes_dir = Path(notes_dir)
        else:
            # Default: agent/notes/ (sibling to app/)
            self.notes_dir = Path(__file__).parent.parent.parent / "notes"

        # Create directory structure
        self.notes_dir.mkdir(exist_ok=True)
        (self.notes_dir / "carriers").mkdir(exist_ok=True)
        (self.notes_dir / "patterns").mkdir(exist_ok=True)
        (self.notes_dir / "daily").mkdir(exist_ok=True)

        # Register tools
        self.register(self.remember)
        self.register(self.recall)
        self.register(self.list_carrier_notes)
        self.register(self.log_daily)

    @observe_tool
    def remember(
        self,
        subject: str,
        note: str,
        category: str = "carriers",
    ) -> str:
        """
        Remember something for future reference.

        Use this to store important information about carriers, patterns,
        or anything else worth remembering across sessions.

        Args:
            subject: What this is about (DOT number, company name, topic)
            note: What to remember
            category: Where to store - "carriers", "patterns", or "general"

        Returns:
            str: Confirmation of what was saved
        """
        if not subject or not note:
            return "Error: Both subject and note are required"

        # Sanitize subject for filename
        safe_subject = "".join(c if c.isalnum() or c in "-_" else "_" for c in subject)

        # Determine file path
        if category not in ("carriers", "patterns", "general"):
            category = "carriers"

        if category == "general":
            file_path = self.notes_dir / f"{safe_subject}.md"
        else:
            file_path = self.notes_dir / category / f"{safe_subject}.md"

        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Append to file (create if doesn't exist)
        entry = f"\n## {timestamp}\n{note}\n"

        if file_path.exists():
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(entry)
        else:
            # Create new file with header
            header = f"# Notes: {subject}\n\nCategory: {category}\n"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(header + entry)

        return f"Remembered about {subject} ({category}): {note[:100]}{'...' if len(note) > 100 else ''}"

    @observe_tool
    def recall(
        self,
        subject: str,
        category: str = "carriers",
    ) -> str:
        """
        Recall everything known about a subject.

        Use this to retrieve past notes about a carrier, pattern, or topic.

        Args:
            subject: What to look up (DOT number, company name, etc.)
            category: Where to look - "carriers", "patterns", or "general"

        Returns:
            str: All notes about this subject, or "no notes found"
        """
        if not subject:
            return "Error: Subject is required"

        # Sanitize subject for filename
        safe_subject = "".join(c if c.isalnum() or c in "-_" else "_" for c in subject)

        # Determine file path
        if category not in ("carriers", "patterns", "general"):
            category = "carriers"

        if category == "general":
            file_path = self.notes_dir / f"{safe_subject}.md"
        else:
            file_path = self.notes_dir / category / f"{safe_subject}.md"

        if not file_path.exists():
            # Try other categories
            for cat in ["carriers", "patterns", "general"]:
                if cat == "general":
                    alt_path = self.notes_dir / f"{safe_subject}.md"
                else:
                    alt_path = self.notes_dir / cat / f"{safe_subject}.md"
                if alt_path.exists():
                    file_path = alt_path
                    category = cat
                    break
            else:
                return f"No notes found for {subject}"

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return f"Notes for {subject} ({category}):\n\n{content}"

    @observe_tool
    def list_carrier_notes(self) -> str:
        """
        List all carriers with notes.

        Returns:
            str: List of carriers that have notes stored
        """
        carriers_dir = self.notes_dir / "carriers"

        if not carriers_dir.exists():
            return "No carrier notes yet"

        files = list(carriers_dir.glob("*.md"))

        if not files:
            return "No carrier notes yet"

        output = ["Carriers with notes:\n"]

        for f in sorted(files):
            # Get file stats
            stat = f.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
            size_lines = len(f.read_text(encoding="utf-8").split("\n"))

            carrier_name = f.stem
            output.append(f"- {carrier_name} (updated {modified}, {size_lines} lines)")

        output.append(f"\nTotal: {len(files)} carrier(s)")
        return "\n".join(output)

    @observe_tool
    def log_daily(self, entry: str) -> str:
        """
        Log an entry to today's daily log.

        Use this to track significant activities, decisions, or events.

        Args:
            entry: What happened

        Returns:
            str: Confirmation
        """
        if not entry:
            return "Error: Entry is required"

        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H:%M")

        file_path = self.notes_dir / "daily" / f"{today}.md"

        log_entry = f"\n- **{timestamp}** - {entry}\n"

        if file_path.exists():
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        else:
            header = f"# Daily Log: {today}\n"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(header + log_entry)

        return f"Logged: {entry[:100]}{'...' if len(entry) > 100 else ''}"
