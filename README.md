# Workflow processor

Standalone Python workflow processor serving HTTP and WebSocket endpoints on port
3050. It can run without the parent node editor repository.

## License

This project is source-available under the [SaaS Commercial Restriction License 1.0](LICENSE). See
[LICENSING.md](LICENSING.md) for the generated-output and hosted-service policy.

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

## Owner-scoped execution

The orchestration server supplies `owner_id` from its authenticated session and a
server-issued `execution_id` in workflow messages. These fields are trusted only
on the server-to-worker connection; do not expose worker HTTP/WebSocket endpoints
to untrusted clients. This is application-level storage isolation, not an OS or
container sandbox for arbitrary custom node code or interactive shells.

Execution automatically creates `<base>/input/<owner>`, `output/<owner>`, and
`temp/<owner>`. Logical `/input/file` references are looked up under the owner;
only `/public/file` is shared. No legacy private files are migrated or read as a
fallback. Models and dataframe state are also separated by owner.

Custom nodes must use `fs.storage_folder("output")` or `"temp"`, validate supplied
filenames, and declare generated files in `NodeOutput.files_to_upload`. The old
unscoped `assets_folder()` fails closed. Result URLs remain logical
`/assets/output/<filename>` or `/temp/<filename>`; authenticated server handlers
resolve the owner's namespace without exposing an authoritative UUID in the URL.
Execution JSON events carry `execution_id`. Each upload metadata entry contains a
unique `transfer_id`, filename, folder, and exact size. Binary chunks contain the
16 UUID bytes of that transfer ID, a final flag byte, and payload; zero-byte files
send just the ID and final flag. IDs cannot be rebound within a worker connection.
The server stages each transfer and atomically publishes the complete file, cleaning
unfinished transfers on terminal errors or disconnects.

The server prepares at most one workflow at a time per worker, waiting for
`WorkflowFinished` or `WorkflowError` before preparing the next inputs. The worker
also holds a shared cache lock across execution and HTTP cache mutations, so a
connection loss cannot allow another connection to change still-running inputs. A node error
is not terminal while another DAG may still run. Parse/build errors and empty
workflows also acknowledge completion. Dataframe requests send `ExecutionComplete`
even when no dataframe exists. A workflow completion timeout closes the connection
rather than allowing another input preparation to race a possibly running workflow.

Cache uploads are published in metadata only after the complete declared size has
arrived; failed/truncated uploads are removed. Server preparation drains every
in-flight upload before returning a batch failure, rather than leaving detached
requests able to mutate a following execution's cache.

Cache identity is the unique scoped filename, not the content hash. Startup upgrades
old SQLite cache schemas transactionally, preserving distinct keys and the latest
record for duplicate keys; it does not move storage files. Keys already overwritten
by the old hash-unique schema cannot be recovered from metadata and are synchronized
again when requested.

Deploy the updated server and processor together; legacy filename-based binary
packets and untagged result events/uploads are rejected.

Focused tests: `uv run python -m unittest discover -s tests -p 'test_*.py' -v`.

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
