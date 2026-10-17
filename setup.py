"""Prepare this standalone processor using only the Python standard library."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def install_fish() -> None:
    """Install Fish when setup runs with the worker image's root privileges."""

    if shutil.which("fish") is not None:
        return

    if os.name != "posix" or os.geteuid() != 0:
        raise RuntimeError(
            "Fish is required for terminal sessions. Install Fish, then rerun python setup.py."
        )

    apt_get = shutil.which("apt-get")
    if apt_get is None:
        raise RuntimeError(
            "Fish is required for terminal sessions, but setup can only install it automatically with apt-get."
        )

    subprocess.run([apt_get, "update"], check=True)
    subprocess.run(
        [apt_get, "install", "--yes", "--no-install-recommends", "fish"],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="start the processor after setup")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent
    os.chdir(repo)

    uv = shutil.which("uv")
    if uv is None:
        print(
            "uv was not found on PATH. Install it with:\n"
            "  python -m pip install uv\n"
            "or follow https://docs.astral.sh/uv/getting-started/installation/\n"
            "Then reopen your terminal if needed and rerun python setup.py.\n"
            "Python 3.14 is required by this project.",
            file=sys.stderr,
        )
        return 1

    try:
        install_fish()
        subprocess.run([uv, "sync", "--locked"], cwd=repo, check=True)

        preferred = Path("/data")
        base = preferred if preferred.exists() and preferred.is_dir() else repo / "data"
        for folder in ("input", "output", "temp"):
            (base / folder).mkdir(parents=True, exist_ok=True)
        print(f"Setup complete. Storage: {base}", flush=True)

        if args.run:
            subprocess.run([uv, "run", "main.py"], cwd=repo, check=True)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        return exc.returncode
    except OSError as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
