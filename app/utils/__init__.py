"""Shared utility helpers."""

import os


def allowed_file(filename, allowed_extensions):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
    )


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
