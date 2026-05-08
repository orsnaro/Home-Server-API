from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from datetime import datetime

from flask import Blueprint, abort, jsonify, render_template, request, send_file, session

bp = Blueprint("media", __name__)
EXPLORER_SESSION_KEY = "media_explorer_unlocked"

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".log",
    ".ini",
    ".yaml",
    ".yml",
    ".csv",
}


def get_media_root() -> Path:
    configured_root = os.getenv("MEDIA_BROWSER_ROOT")
    if configured_root:
        configured_path = Path(configured_root).expanduser()
        if not configured_path.is_absolute():
            configured_path = Path.cwd() / configured_path
        return configured_path.resolve()
    return Path.cwd().resolve()


def get_explorer_passcode() -> str:
    return (os.getenv("SERVER_UI_EXPLORER_PASSCODE") or "").strip()


def is_explorer_unlocked() -> bool:
    passcode = get_explorer_passcode()
    if not passcode:
        return True
    return bool(session.get(EXPLORER_SESSION_KEY))


def resolve_browser_path(raw_path: str = "", abort_on_error: bool = True) -> tuple[Path, Path] | None:
    root = get_media_root()
    candidate = (root / raw_path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        if abort_on_error:
            abort(404, "Path is outside the configured media root.")
        return None

    return root, candidate


def classify_file(path: Path) -> tuple[str, str | None]:
    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type:
        if mime_type.startswith("image/"):
            return "image", mime_type
        if mime_type.startswith("audio/"):
            return "audio", mime_type
        if mime_type.startswith("video/"):
            return "video", mime_type
        if mime_type.startswith("text/"):
            return "text", mime_type

    if path.suffix.lower() in TEXT_EXTENSIONS:
        return "text", mime_type

    return "file", mime_type


def format_size(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def build_breadcrumbs(root: Path, current: Path) -> list[dict[str, str]]:
    breadcrumbs = [{"label": root.name or str(root), "path": ""}]
    relative_parts = current.relative_to(root).parts if current != root else []

    cumulative = Path()
    for part in relative_parts:
        cumulative /= part
        breadcrumbs.append({"label": part, "path": cumulative.as_posix()})

    return breadcrumbs


@bp.route("/media")
def explorer():
    requested_path = request.args.get("path", "").strip()
    selected_file = request.args.get("file", "").strip()
    root, current = resolve_browser_path(requested_path)

    # Prevent browsing into hidden directories
    relative_current = current.relative_to(root)
    if any(part.startswith(".") for part in relative_current.parts):
        abort(403, "Access to hidden directories is restricted.")

    is_unlocked = is_explorer_unlocked()

    if not current.exists() or not current.is_dir():
        abort(404, "Folder not found.")

    if not is_unlocked:
        return render_template(
            "pages/media_explorer.html",
            breadcrumbs=build_breadcrumbs(root, root),
            current_fs_path=str(root),
            current_path="",
            entries=[],
            listing_error=None,
            parent_path=None,
            root_fs_path=str(root),
            selected_file="",
            is_unlocked=False,
        )

    listing_error = None
    try:
        # Filter out hidden files and noise directories
        children = sorted(
            [item for item in current.iterdir() if not item.name.startswith(".") and item.name != "__pycache__"],
            key=lambda item: (not item.is_dir(), item.name.casefold()),
        )
    except PermissionError:
        children = []
        listing_error = "This folder cannot be listed by the server process."

    entries = []
    for child in children:
        try:
            stat = child.stat()
        except OSError:
            continue

        relative_path = child.relative_to(root).as_posix()
        kind, mime_type = classify_file(child)
        entries.append(
            {
                "name": child.name,
                "relative_path": relative_path,
                "is_dir": child.is_dir(),
                "media_kind": "directory" if child.is_dir() else kind,
                "mime_type": mime_type or "",
                "size_label": "--" if child.is_dir() else format_size(stat.st_size),
                "modified_label": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "is_selected": relative_path == selected_file,
            }
        )

    parent_path = None
    if current != root:
        parent_path = current.parent.relative_to(root).as_posix()

    if selected_file:
        selected_resolution = resolve_browser_path(selected_file, abort_on_error=False)
        if not selected_resolution:
            selected_file = ""
        else:
            _, selected_target = selected_resolution
            if not selected_target.exists() or not selected_target.is_file() or selected_target.parent != current:
                selected_file = ""

    return render_template(
        "pages/media_explorer.html",
        breadcrumbs=build_breadcrumbs(root, current),
        current_fs_path=str(current),
        current_path=current.relative_to(root).as_posix() if current != root else "",
        entries=entries,
        is_unlocked=is_unlocked,
        listing_error=listing_error,
        parent_path=parent_path,
        root_fs_path=str(root),
        selected_file=selected_file,
    )


@bp.route("/media/verify-passcode", methods=["POST"])
def verify_explorer_passcode():
    configured_passcode = get_explorer_passcode()
    if not configured_passcode:
        return jsonify({"success": False, "message": "Explorer passcode is not configured."}), 500

    entered_passcode = (request.json or {}).get("passcode", "").strip()
    if entered_passcode == configured_passcode:
        session[EXPLORER_SESSION_KEY] = True
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid passcode."}), 403


@bp.route("/media/lock", methods=["POST"])
def lock_explorer():
    session.pop(EXPLORER_SESSION_KEY, None)
    return jsonify({"success": True})


@bp.route("/media/file")
def serve_file():
    if not is_explorer_unlocked():
        abort(403, "Explorer is locked.")

    requested_path = request.args.get("path", "").strip()
    root, target = resolve_browser_path(requested_path)

    if not target.exists() or not target.is_file():
        abort(404, "File not found.")

    # Prevent serving hidden files or files in hidden directories
    relative_path = target.relative_to(root)
    if any(part.startswith(".") for part in relative_path.parts):
        abort(403, "Access to hidden files or directories is restricted.")

    mime_type, _ = mimetypes.guess_type(target.name)
    if not mime_type and target.suffix.lower() in TEXT_EXTENSIONS:
        mime_type = "text/plain"
    as_attachment = request.args.get("download") == "1"

    return send_file(
        target,
        mimetype=mime_type,
        as_attachment=as_attachment,
        conditional=True,
        download_name=target.name,
    )
