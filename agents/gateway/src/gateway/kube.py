from __future__ import annotations

import subprocess

KUBECTL_TIMEOUT_SECONDS = 15


class KubectlError(RuntimeError):
    def __init__(self, message: str, returncode: int | None = None) -> None:
        super().__init__(message)
        self.returncode = returncode


def run_kubectl(args: list[str], timeout: float = KUBECTL_TIMEOUT_SECONDS) -> str:
    """Run kubectl with an argument list (never a shell) and return stdout."""
    cmd = ["kubectl", *args]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise KubectlError(f"kubectl timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise KubectlError("kubectl binary not found in PATH") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown error").strip()
        raise KubectlError(detail[:2000], completed.returncode)
    return completed.stdout
