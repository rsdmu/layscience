"""
Robust storage module for LayScience.

This module defines a helper to compute a local path for an uploaded PDF.
It respects the ``LOCAL_UPLOAD_DIR`` environment variable and falls
back to a writable directory under ``/tmp`` when the configured
location is not writable.  This prevents failures in read‑only
deployment environments.
"""
import os
import tempfile

# Determine a base directory for uploaded files.  Explicit env var
# always wins.  Otherwise, we use ``uploads`` in the current working
# directory if it is writable, or we fall back to ``/tmp/layscience_uploads``.
_configured = os.getenv("LOCAL_UPLOAD_DIR")
if _configured:
    base_dir = _configured
else:
    # default relative directory
    candidate = os.path.join(os.getcwd(), "uploads")
    try:
        os.makedirs(candidate, exist_ok=True)
        # Verify write access
        if os.access(candidate, os.W_OK):
            base_dir = candidate
        else:
            raise PermissionError
    except Exception:
        # Fallback to tmp if the candidate is not writable
        base_dir = os.path.join(tempfile.gettempdir(), "layscience_uploads")
        os.makedirs(base_dir, exist_ok=True)


def local_path_for(file_id: str) -> str:
    """Return the absolute path for a given file ID.

    Uploaded PDFs are stored with a ``.pdf`` extension under
    ``base_dir``.  The directory is created on first use if it does
    not already exist.
    """
    return os.path.join(base_dir, f"{file_id}.pdf")