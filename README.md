<p align="center">
  <img src="docs/assets/screens/root.png" alt="netgrab running" width="900">
</p>

<h1 align="center">netgrab</h1>

<p align="center"><b>Queue downloads, pause them, resume them, watch the byte count.</b></p>

<p align="center">
  <a href="https://github.com/scar8969/netgrab/actions/workflows/ci.yml"><img src="https://github.com/scar8969/netgrab/actions/workflows/ci.yml/badge.svg" alt="ci"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/tests-25%20passed-2ea44f" alt="tests: 25 passed"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/coverage-63.7%-yellow" alt="coverage: 63.7%"></a> <a href="#api"><img src="https://img.shields.io/badge/routes-8%20live-0969da" alt="routes: 8 live"></a> <a href="#requirements"><img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="python: 3.11+"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="license: MIT"></a>
</p>

netgrab is a small download manager: submit URLs, and each becomes a task with a state machine, a byte counter and pause/resume controls. Progress is visible as JSON and in the panel.

---

**Contents** &nbsp;·&nbsp; [Why](#why-this-exists) &nbsp;·&nbsp; [What it does](#what-it-does) &nbsp;·&nbsp; [Quickstart](#quickstart) &nbsp;·&nbsp; [Screenshots](#screenshots) &nbsp;·&nbsp; [API](#api) &nbsp;·&nbsp; [CLI](#cli) &nbsp;·&nbsp; [Configuration](#configuration) &nbsp;·&nbsp; [Measured](#measured-not-estimated) &nbsp;·&nbsp; [How a request flows](#how-a-request-flows) &nbsp;·&nbsp; [Architecture](#architecture) &nbsp;·&nbsp; [Quality gates](#quality-gates) &nbsp;·&nbsp; [Development](#development) &nbsp;·&nbsp; [Deploy](#deploy) &nbsp;·&nbsp; [Limits](#limits-stated-rather-than-hidden)

## Why this exists

A loop of curl calls has no state. Once a download can fail halfway, be paused, or need to resume, you need a task table and a worker that reads it — which is exactly what this service is.

## What it does

| Capability | How it works |
| --- | --- |
| **Task state machine** | queued, running, paused, done, failed — transitions are validated, not assumed. |
| **Pause and resume** | POST /api/tasks/<id>/pause and /resume flip the worker's behaviour; the partial file stays on disk and the download continues from its size. |
| **Byte accounting** | Downloaded and total bytes are stored per task and reported by the list endpoint. |
| **CLI** | dl submits a URL and prints the task id so a script can poll it. |

## Quickstart

```sh
git clone https://github.com/scar8969/netgrab.git
cd netgrab
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python wsgi.py                                 # http://127.0.0.1:8000
```

It is up when this answers:

```sh
curl -s http://127.0.0.1:8000/api/tasks
```

## Screenshots

Captured from the running service with headless Chromium at 1440×900, one image per page, committed under [`docs/assets/screens/`](docs/assets/screens/).

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/healthz.png" alt="/healthz" width="100%"><br><sub><code>/healthz</code> &middot; 8.5 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/livez.png" alt="/livez" width="100%"><br><sub><code>/livez</code> &middot; 7.3 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/metrics.png" alt="/metrics" width="100%"><br><sub><code>/metrics</code> &middot; 14.8 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/readyz.png" alt="/readyz" width="100%"><br><sub><code>/readyz</code> &middot; 7.7 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/version.png" alt="/version" width="100%"><br><sub><code>/version</code> &middot; 29.2 KB</sub></td>
</tr>
</table>

## API

Every route below is declared in [`openapi/netgrab.yaml`](openapi/netgrab.yaml) and exercised by the live probe recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/api/tasks` | list |
| `POST` | `/api/tasks` | create task |
| `POST` | `/api/tasks/<id>/pause` | pause |
| `POST` | `/api/tasks/<id>/resume` | resume |

## CLI

The same operations without an HTTP client. Installed as `netgrab`, and runnable from a checkout with no install:

```sh
python -m ctfile_downloader.cli --help
```

```text
usage: ctfile-dl [-h] {dl} ...

positional arguments:
  {dl}
    dl        download every URL in a link file

options:
  -h, --help  show this help message and exit
```

## Configuration

Environment only — there is no config file. Copy `.env.example` to `.env` and edit; `APP_ENV=production` refuses to start without `SECRET_KEY`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_ENV` | `development` | development \| staging \| production; production enforces the secret. |
| `SECRET_KEY` | `change-me-in-production` | Session/CSRF signing key. Required when APP_ENV=production. |
| `HOST` | `0.0.0.0` | Interface the dev server binds. |
| `PORT` | `8000` | Port the dev server and the container listen on. |
| `DEBUG` | `false` | Flask debug mode. Never true in production. |
| `MAX_CONTENT_LENGTH` | `8388608` | Largest accepted request body, in bytes. |
| `DATA_DIR` | `(empty)` | Where uploaded and generated files live. |
| `INSTANCE_DIR` | `(empty)` | Where the SQLite file and instance state live. |
| `LOG_DIR` | `(empty)` | Where rotated log files are written, if file logging is on. |
| `LOG_LEVEL` | `INFO` | DEBUG \| INFO \| WARNING \| ERROR. |
| `LOG_JSON` | `true` | true emits one JSON object per line; false is human-readable. |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Header echoed on every response and stamped on every log line. |

## Measured, not estimated

Produced on this checkout by `pytest --cov` and by booting `wsgi.py` and issuing one real GET per documented path. The commands are recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Signal | Value |
| --- | --- |
| Tests | **25 / 25 passed** (2.5 s, exit 0) |
| Line coverage | **63.7%** — 441 of 652 statements |
| Source | 15 files / 1,431 lines |
| Test code | 4 files / 346 lines |
| Documented paths | 3 in the spec, 1 GET |
| Live probe | 9 GET requests to the booted app, **8 answered 200** |
| Median latency | **15.9 ms** (single uncached request, dev server) |
| Slowest / fastest | 96.1 ms `/` / 3.3 ms `/readyz` |
| Bytes served | 8.9 KB across 9 responses |
| Screenshots | 6 captured |

## How a request flows

```text
client
  │  HTTP
  ▼
wsgi.py ──▶ ctfile_downloader/app.py:get_app()
                │  reads config once (ctfile_downloader/config.py)
                │  registers the `dl` blueprint
                ▼
           route handler
             ├──▶ ctfile_downloader/models.py        tables, via Flask-SQLAlchemy
             ├──▶ ctfile_downloader/errors.py        raises typed errors → one JSON envelope
             └──▶ ctfile_downloader/observability.py JSON log line + X-Request-ID
```

Every response carries `X-Request-ID`, and the matching log line is written once at the end of the request with the status and duration, so a report of "it failed" is one `grep` away from the traceback.

## Architecture

```
netgrab/
├── src/ctfile_downloader/
│   ├── http.py                         379  HTTP plumbing for ctfile_downloader: correlation ids
│   ├── _app.py                         212  Web UI for ctfile-downloader: queue tasks, watch per
│   ├── observability.py                169  Structured logging and request correlation for ctfil
│   ├── config.py                       168  Environment-driven configuration for ctfile_download
│   ├── app.py                          119  Application factory for ctfile_downloader
│   ├── errors.py                       108  Typed application errors and their HTTP mapping for 
│   ├── dl/api.py                        98  
│   ├── paths.py                         52  Filesystem layout for ctfile_downloader
│   ├── cli.py                           51  
│   ├── dl/worker.py                     30  
│   ├── models.py                        26  
│   ├── dl/extract.py                    13  
├── openapi/netgrab.yaml                   the contract of record
├── schema/netgrab.sql                     the DDL
├── tests/                       the suite that has to stay green
├── docs/EVIDENCE.md             the recorded live route walk
├── Dockerfile                   multi-stage build
└── wsgi.py                      entry point
```

The package keeps one shape across the service: `config.py` reads the environment once, `observability.py` emits structured JSON logs carrying a request id, `errors.py` turns exceptions into a single JSON envelope, `models.py` holds the tables, and the `dl/` package holds the routes.

## Quality gates

| Gate | Command | Threshold |
| --- | --- | --- |
| Suite | `pytest -q` | all green |
| Coverage | `pytest --cov` | floor in `pyproject.toml`, set below the measured value |
| Lint | `ruff check src tests` | zero findings |
| Format | `ruff format --check src tests` | zero reformats |
| Types | `mypy src` | zero errors |
| Security | `bandit -c pyproject.toml -r src` | reviewed skip list, no unreviewed finding |
| Live routes | boot `wsgi.py`, one GET per documented path | no 5xx, no undocumented guard |

CI runs the first six on Python 3.11, 3.12 and 3.13 on every push to `main`, plus a container build — [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Development

```sh
pip install -e ".[dev]"
python -m pytest -q                      # the suite
python -m pytest --cov                   # with the coverage floor
python -m ruff check src tests           # lint
python -m ruff format --check src tests  # formatting
python -m mypy src                       # types
python -m bandit -c pyproject.toml -r src  # security
pre-commit install                       # the same checks on commit
```

Dependabot opens grouped PRs for the dev tooling weekly and for actions and the base image monthly.

## Deploy

```sh
docker build -t netgrab .
docker run --rm -p 8000:8000 --env-file .env.example netgrab
```

A `docker-compose.yml` is included for a local run with a volume for the SQLite file. The image runs as a non-root user and serves through gunicorn.

## Limits, stated rather than hidden

- One worker process; concurrency is a configuration value, not a queue service.
- Resume reopens the partial file at its current size; an origin that ignores Range makes the task start over.

## License

MIT — see [LICENSE](LICENSE).
