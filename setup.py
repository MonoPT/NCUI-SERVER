"""Prepare this standalone processor using only the Python standard library."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def install_system_packages(
    packages: list[str],
    required_commands: list[str],
) -> None:
    """Install missing command dependencies with a supported system package manager."""

    missing_commands = [
        command
        for command in required_commands
        if shutil.which(command) is None
    ]
    if not missing_commands:
        return

    if os.name != "posix" or os.geteuid() != 0:
        commands = ", ".join(missing_commands)
        raise RuntimeError(
            f"Missing required commands: {commands}. Install them, then rerun python setup.py."
        )

    apt_get = shutil.which("apt-get")
    pacman = shutil.which("pacman")

    if apt_get is not None:
        subprocess.run([apt_get, "update"], check=True)
        subprocess.run(
            [apt_get, "install", "--yes", "--no-install-recommends", *packages],
            check=True,
        )
        return

    if pacman is not None:
        subprocess.run([pacman, "--sync", "--refresh", "--noconfirm"], check=True)
        subprocess.run(
            [pacman, "--sync", "--needed", "--noconfirm", *packages],
            check=True,
        )
        return

    managers = "apt-get or pacman"
    package_list = ", ".join(packages)
    raise RuntimeError(
        f"Missing required commands: {', '.join(missing_commands)}. "
        f"Install packages ({package_list}) with {managers}, then rerun python setup.py."
    )


def install_fish() -> None:
    """Ensure Fish is available for terminal sessions."""

    install_system_packages(
        packages=["fish"],
        required_commands=["fish"],
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
