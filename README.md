# Workflow processor

Standalone Python workflow processor serving HTTP and WebSocket endpoints on port
3050. It can run without the parent node editor repository.

## Prerequisites

- Python 3.14, available as `python` (or use `python3.14` in the commands below).
- [uv](https://docs.astral.sh/uv/getting-started/installation/), available on `PATH`.
  One cross-platform installation option is `python -m pip install uv`.
- Git and GitHub SSH access for the clone command below.

## Clone, setup, and run

Clone the standalone repository:

```sh
git clone git@github.com:MonoPT/NCUI-SERVER.git
cd NCUI-SERVER
python setup.py
uv run main.py
```

Or set up and start in one command:

```sh
python setup.py --run
```

`setup.py` uses only the Python standard library and anchors its working directory
to the repository containing the script, even when invoked from another directory.
It checks for `uv`, runs `uv sync --locked` to create/update `.venv` from `uv.lock`,
and creates the required storage directories. A missing `uv` produces installation
instructions and a nonzero exit status. Setup does not install or configure secrets.
Dependency synchronization requires network access when packages are not cached.

Storage follows the existing API convention: use `/data` if it already exists as a
directory, otherwise use `data/` in this repository. The `input/`, `output/`, and
`temp/` directories are created under that base, which must be writable. CSV output
uses the same storage base. Run `uv run main.py` from the repository directory;
the server listens on `0.0.0.0:3050`, with `/health` and `/ws` endpoints.

## Docker

Build from this repository directory:

```sh
docker build -t ncui-server .
docker run --rm -p 3050:3050 -v ncui-data:/data ncui-server
```

The image uses Python 3.14 slim, installs `uv`, copies the standalone repository,
and runs `python setup.py` at build time. Its default command is `uv run main.py`.
The mounted `/data` volume persists runtime storage; without that mount, storage
falls back to `/app/data` inside the container. Local virtual environments, data,
and common secret files are excluded from the build context by `.dockerignore`.
Do not place other secrets in the build context. No secrets are needed by setup.
