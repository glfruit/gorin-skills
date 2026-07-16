#!/usr/bin/env python3
"""
NeoBear CLI - Next-Gen Bear Notes Tool
A command-line interface for Bear notes app with perfect URL encoding.

"Where old Bear links become new again." 🐻💫

This tool uses proper percent-encoding (%20 for spaces) instead of
plus-encoding (+) to prevent the space corruption bug in Bear notes.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List


class NeoBearCLI:
    """NeoBear notes command-line interface with perfect URL encoding."""
    
    def __init__(self, token_file: Optional[str] = None, verbose: bool = False):
        self.verbose = verbose
        self.token_file = token_file or os.path.expanduser("~/.config/bear/token")
        self.token = self._load_token()
        
    def _load_token(self) -> Optional[str]:
        """Load Bear API token from file."""
        token_path = Path(self.token_file)
        if token_path.exists():
            try:
                return token_path.read_text().strip()
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Could not load token: {e}", file=sys.stderr)
        return None
    
    def _encode_param(self, value: str) -> str:
        """
        Properly encode URL parameter using percent-encoding.
        Spaces become %20, not +
        """
        # Use quote instead of quote_plus to get %20 for spaces
        return urllib.parse.quote(value, safe='')
    
    def _build_url(self, action: str, params: Dict[str, Any]) -> str:
        """Build Bear x-callback-url with proper encoding."""
        base_url = f"bear://x-callback-url/{action}"
        
        # Filter out None values and encode parameters
        encoded_params = []
        for key, value in params.items():
            if value is not None:
                if isinstance(value, bool):
                    # Convert boolean to yes/no
                    value = "yes" if value else "no"
                elif isinstance(value, list):
                    # Join list items
                    value = ",".join(str(v) for v in value)
                else:
                    value = str(value)
                
                # Encode both key and value
                encoded_key = self._encode_param(key)
                encoded_value = self._encode_param(value)
                encoded_params.append(f"{encoded_key}={encoded_value}")
        
        if encoded_params:
            return f"{base_url}?{'&'.join(encoded_params)}"
        return base_url
    
    def _execute_url(self, url: str, dry_run: bool = False) -> bool:
        """Execute Bear URL scheme."""
        if self.verbose or dry_run:
            print(f"URL: {url}", file=sys.stderr)
        
        if dry_run:
            return True
        
        try:
            # Use 'open' command on macOS to trigger URL scheme
            result = subprocess.run(
                ["open", url],
                capture_output=True,
                text=True,
                check=True
            )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"Error executing URL: {e}", file=sys.stderr)
            return False
        except FileNotFoundError:
            print("Error: 'open' command not found. Are you on macOS?", file=sys.stderr)
            return False
    
    def create(
        self,
        title: str,
        text: Optional[str] = None,
        tags: Optional[List[str]] = None,
        file_path: Optional[str] = None,
        pin: bool = False,
        open_note: bool = True,
        new_window: bool = False,
        float_window: bool = False,
        edit: bool = False,
        timestamp: bool = False,
        dry_run: bool = False
    ) -> bool:
        """Create a new note in Bear."""
        
        # Read content from file if specified
        if file_path:
            try:
                text = Path(file_path).read_text()
            except Exception as e:
                print(f"Error reading file: {e}", file=sys.stderr)
                return False
        
        # Read from stdin if no text provided
        if text is None and not sys.stdin.isatty():
            text = sys.stdin.read()
        
        if text is None or text.strip() == "":
            print("Error: Note content cannot be empty", file=sys.stderr)
            return False
        
        params = {
            "title": title,
            "text": text,
            "tags": tags,
            "pin": pin if pin else None,
            "open_note": "no" if not open_note else None,
            "new_window": new_window if new_window else None,
            "float": float_window if float_window else None,
            "edit": edit if edit else None,
            "timestamp": timestamp if timestamp else None,
        }
        
        url = self._build_url("create", params)
        return self._execute_url(url, dry_run)
    
    def open_note(
        self,
        note_id: Optional[str] = None,
        title: Optional[str] = None,
        header: Optional[str] = None,
        exclude_trashed: bool = True,
        new_window: bool = False,
        float_window: bool = False,
        show_window: bool = True,
        edit: bool = False,
        dry_run: bool = False
    ) -> bool:
        """Open a note in Bear."""
        if not note_id and not title:
            print("Error: Either note_id or title must be provided", file=sys.stderr)
            return False
        
        params = {
            "id": note_id,
            "title": title,
            "header": header,
            "exclude_trashed": exclude_trashed if exclude_trashed else None,
            "new_window": new_window if new_window else None,
            "float": float_window if float_window else None,
            "show_window": "no" if not show_window else None,
            "edit": edit if edit else None,
        }
        
        url = self._build_url("open-note", params)
        return self._execute_url(url, dry_run)
    
    def add_text(
        self,
        note_id: Optional[str] = None,
        title: Optional[str] = None,
        text: Optional[str] = None,
        mode: str = "append",
        new_line: bool = True,
        exclude_trashed: bool = True,
        open_note: bool = False,
        edit: bool = False,
        dry_run: bool = False
    ) -> bool:
        """Append or prepend text to an existing note."""
        if not note_id and not title:
            print("Error: Either note_id or title must be provided", file=sys.stderr)
            return False
        
        # Read from stdin if no text provided
        if text is None and not sys.stdin.isatty():
            text = sys.stdin.read()
        
        if not text:
            print("Error: Text cannot be empty", file=sys.stderr)
            return False
        
        if not self.token:
            print("Error: Token required for add-text operation", file=sys.stderr)
            return False
        
        params = {
            "id": note_id,
            "title": title,
            "text": text,
            "mode": mode,
            "new_line": new_line if new_line else None,
            "exclude_trashed": exclude_trashed if exclude_trashed else None,
            "open_note": open_note if open_note else None,
            "edit": edit if edit else None,
            "token": self.token,
        }
        
        url = self._build_url("add-text", params)
        return self._execute_url(url, dry_run)
    
    def search(
        self,
        query: Optional[str] = None,
        tag: Optional[str] = None,
        dry_run: bool = False
    ) -> bool:
        """Search notes in Bear."""
        if tag:
            # Use open-tag for tag-based search
            params = {"name": tag}
            url = self._build_url("open-tag", params)
        else:
            params = {"term": query} if query else {}
            url = self._build_url("search", params)
        
        return self._execute_url(url, dry_run)
    
    def tags(self, dry_run: bool = False) -> bool:
        """List all tags."""
        if not self.token:
            print("Error: Token required for tags operation", file=sys.stderr)
            return False
        
        params = {"token": self.token}
        url = self._build_url("tags", params)
        return self._execute_url(url, dry_run)
    
    def archive(self, note_id: Optional[str] = None, search: Optional[str] = None, dry_run: bool = False) -> bool:
        """Archive a note."""
        params = {"id": note_id, "search": search}
        url = self._build_url("archive", params)
        return self._execute_url(url, dry_run)
    
    def trash(self, note_id: Optional[str] = None, search: Optional[str] = None, dry_run: bool = False) -> bool:
        """Move a note to trash."""
        params = {"id": note_id, "search": search}
        url = self._build_url("trash", params)
        return self._execute_url(url, dry_run)
    
    def change_theme(self, theme: str, dry_run: bool = False) -> bool:
        """Change Bear theme."""
        params = {"theme": theme}
        url = self._build_url("change-theme", params)
        return self._execute_url(url, dry_run)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Bear Notes CLI - Fixed version with proper URL encoding"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="bear_cli.py 2.0.0 (fixed)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--token-file",
        help="Path to Bear API token file (default: ~/.config/bear/token)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new note")
    create_parser.add_argument("--title", required=True, help="Note title")
    create_parser.add_argument("--text", help="Note content (use stdin if not provided)")
    create_parser.add_argument("--file", help="Read content from file")
    create_parser.add_argument("--tags", help="Comma-separated tags")
    create_parser.add_argument("--pin", action="store_true", help="Pin the note")
    create_parser.add_argument("--no-open", action="store_true", help="Don't open the note")
    create_parser.add_argument("--new-window", action="store_true", help="Open in new window")
    create_parser.add_argument("--float", action="store_true", help="Float the window")
    create_parser.add_argument("--edit", action="store_true", help="Place cursor in editor")
    create_parser.add_argument("--timestamp", action="store_true", help="Add timestamp")
    create_parser.add_argument("--dry-run", action="store_true", help="Preview URL without executing")
    
    # Open command
    open_parser = subparsers.add_parser("open", help="Open a note")
    open_parser.add_argument("--id", help="Note ID")
    open_parser.add_argument("--title", help="Note title")
    open_parser.add_argument("--header", help="Scroll to header")
    open_parser.add_argument("--new-window", action="store_true", help="Open in new window")
    open_parser.add_argument("--edit", action="store_true", help="Place cursor in editor")
    open_parser.add_argument("--dry-run", action="store_true", help="Preview URL without executing")
    
    # Append command
    append_parser = subparsers.add_parser("append", help="Append text to a note")
    append_parser.add_argument("--id", help="Note ID")
    append_parser.add_argument("--title", help="Note title")
    append_parser.add_argument("--text", help="Text to append (use stdin if not provided)")
    append_parser.add_argument("--mode", choices=["append", "prepend", "replace", "replace_all"], default="append")
    append_parser.add_argument("--no-new-line", action="store_true", help="Don't add new line")
    append_parser.add_argument("--dry-run", action="store_true", help="Preview URL without executing")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search notes")
    search_parser.add_argument("--query", help="Search query")
    search_parser.add_argument("--tag", help="Search by tag")
    search_parser.add_argument("--dry-run", action="store_true", help="Preview URL without executing")
    
    # Tags command
    tags_parser = subparsers.add_parser("tags", help="List all tags")
    tags_parser.add_argument("--json", action="store_true", help="Output as JSON")
    tags_parser.add_argument("--dry-run", action="store_true", help="Preview URL without executing")
    
    # Archive command
    archive_parser = subparsers.add_parser("archive", help="Archive a note")
    archive_parser.add_argument("--id", help="Note ID")
    archive_parser.add_argument("--search", help="Search term")
    archive_parser.add_argument("--dry-run", action="store_true", help="Preview URL without executing")
    
    # Trash command
    trash_parser = subparsers.add_parser("trash", help="Move note to trash")
    trash_parser.add_argument("--id", help="Note ID")
    trash_parser.add_argument("--search", help="Search term")
    trash_parser.add_argument("--dry-run", action="store_true", help="Preview URL without executing")
    
    # Theme command
    theme_parser = subparsers.add_parser("set-theme", help="Change Bear theme")
    theme_parser.add_argument("--theme", required=True, help="Theme name")
    theme_parser.add_argument("--dry-run", action="store_true", help="Preview URL without executing")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize CLI
    cli = NeoBearCLI(token_file=args.token_file, verbose=args.verbose)
    
    # Execute command
    success = False
    try:
        if args.command == "create":
            tags = args.tags.split(",") if args.tags else None
            success = cli.create(
                title=args.title,
                text=args.text,
                tags=tags,
                file_path=args.file,
                pin=args.pin,
                open_note=not args.no_open,
                new_window=args.new_window,
                float_window=args.float,
                edit=args.edit,
                timestamp=args.timestamp,
                dry_run=args.dry_run
            )
        elif args.command == "open":
            success = cli.open_note(
                note_id=args.id,
                title=args.title,
                header=args.header,
                new_window=args.new_window,
                edit=args.edit,
                dry_run=args.dry_run
            )
        elif args.command == "append":
            success = cli.add_text(
                note_id=args.id,
                title=args.title,
                text=args.text,
                mode=args.mode,
                new_line=not args.no_new_line,
                dry_run=args.dry_run
            )
        elif args.command == "search":
            success = cli.search(
                query=args.query,
                tag=args.tag,
                dry_run=args.dry_run
            )
        elif args.command == "tags":
            success = cli.tags(dry_run=args.dry_run)
        elif args.command == "archive":
            success = cli.archive(note_id=args.id, search=args.search, dry_run=args.dry_run)
        elif args.command == "trash":
            success = cli.trash(note_id=args.id, search=args.search, dry_run=args.dry_run)
        elif args.command == "set-theme":
            success = cli.change_theme(theme=args.theme, dry_run=args.dry_run)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
