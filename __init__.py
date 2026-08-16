from __future__ import annotations

import json
import subprocess
from pathlib import Path

def _build_python_path() -> Path:
    plugin_dir = Path(__file__).resolve().parent

    venv_candidates = [
        path for path in plugin_dir.iterdir()
        if path.is_dir()
        and (path / "bin" / "python").is_file()
    ]

    if not venv_candidates:
        raise FileNotFoundError(
            f"Virtual environment not found in {plugin_dir}"
        )

    return (venv_candidates[0] / "bin" / "python").resolve()

def _build_decoder_path() -> Path:
    plugin_dir = Path(__file__).resolve().parent

    return (plugin_dir / "decoder.py")


def transform_user_message(
    user_message: str,
    session_id: str | None = None,
    task_id: str | None = None,
    **kwargs,
):
    del session_id, task_id, kwargs

    if not isinstance(user_message, str):
        return None

    if not user_message.strip():
        return user_message

    python = _build_python_path()
    decoder = _build_decoder_path()

    result = subprocess.run(
        [
            str(python),
            str(decoder)
        ],
        input=user_message,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)

    redacted_text = payload["redacted_text"]

    print(
        f"redacted {payload['span_count']} span(s)",
        flush=True,
    )

    return redacted_text


def register(ctx):
    ctx.register_hook(
        "transform_user_message",
        transform_user_message,
    )
