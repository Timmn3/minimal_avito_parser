import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get_version() -> str:
    """
    Версия задеплоенного кода: BOT_VERSION (аварийный override) -> version.txt, который пишет
    post-receive хук -> git рядом с кодом -> "unknown". Руками версию нигде не правим.
    """
    override = os.getenv("BOT_VERSION")
    if override:
        return override

    version_file = ROOT / "version.txt"
    if version_file.exists():
        text = version_file.read_text(encoding="utf-8").strip()
        if text:
            return text

    try:
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y.%m.%d", "HEAD"],
            cwd=ROOT, stderr=subprocess.DEVNULL, encoding="utf-8").strip()
        short_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, stderr=subprocess.DEVNULL, encoding="utf-8").strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=ROOT, stderr=subprocess.DEVNULL, encoding="utf-8").strip()
        return f"v{date}-g{short_hash}" + (" (dirty)" if dirty else "")
    except Exception:
        return "unknown"
