"""
Execution service — safely runs subprocesses with timeout and resource limits.
All submitted code is executed in a temporary directory, never inline.
"""
import os
import sys
import subprocess
import tempfile
import shutil
import threading
import uuid
from typing import Dict, Tuple, Optional

from config import MAX_EXECUTION_TIMEOUT, TEMP_DIR

# Semaphore to limit concurrent analyses
_ANALYSIS_LOCK = threading.Semaphore(5)


def create_workspace(code: str, filename: str = "user_code.py") -> Tuple[str, str]:
    """
    Write source code to an isolated temporary directory.

    Returns (workspace_dir, code_filepath).
    """
    workspace_dir = os.path.join(TEMP_DIR, f"cctd_{uuid.uuid4().hex}")
    os.makedirs(workspace_dir, exist_ok=True)
    code_path = os.path.join(workspace_dir, filename)
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    return workspace_dir, code_path


def cleanup_workspace(workspace_dir: str) -> None:
    """Remove a temporary workspace directory."""
    try:
        shutil.rmtree(workspace_dir, ignore_errors=True)
    except Exception:
        pass


def run_tool(
    cmd: list,
    cwd: str,
    timeout: int = MAX_EXECUTION_TIMEOUT,
    env_extra: Optional[Dict] = None,
) -> Dict:
    """
    Execute a command safely and return structured output.

    Returns dict with keys: stdout, stderr, returncode, timed_out, error.
    Never raises; all errors are captured.
    """
    env = os.environ.copy()
    # Remove sensitive env vars
    for key in ("SECRET_KEY", "DATABASE_URL", "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY"):
        env.pop(key, None)
    if env_extra:
        env.update(env_extra)

    result = {
        "stdout": "",
        "stderr": "",
        "returncode": -1,
        "timed_out": False,
        "error": None,
    }

    with _ANALYSIS_LOCK:
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                # Do not inherit stdin
                stdin=subprocess.DEVNULL,
            )
            result["stdout"] = proc.stdout or ""
            result["stderr"] = proc.stderr or ""
            result["returncode"] = proc.returncode
        except subprocess.TimeoutExpired:
            result["timed_out"] = True
            result["error"] = f"Tool timed out after {timeout} seconds"
        except FileNotFoundError as exc:
            result["error"] = f"Tool not found: {exc}"
        except Exception as exc:
            result["error"] = str(exc)

    return result


def get_python_executable() -> str:
    """Return the current Python interpreter path."""
    return sys.executable
