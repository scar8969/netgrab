<p align="center">
  <img src="docs/assets/screens/root.png" alt="netgrab running" width="900">
</p>

<h1 align="center">netgrab</h1>

<p align="center"><b>Queue downloads, pause them, resume them, watch the byte count.</b></p>

<p align="center">
  <a href="#quality-gates"><img src="https://img.shields.io/badge/tests-25%20passed-2ea44f" alt="tests: 25 passed"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/coverage-63.7%-yellow" alt="coverage: 63.7%"></a> <a href="#api"><img src="https://img.shields.io/badge/routes-8%20answered-0969da" alt="routes: 8 answered"></a> <a href="#requirements"><img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="python: 3.11+"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="license: MIT"></a>
</p>

netgrab is a small download manager: submit URLs, and each becomes a task with a state machine, a byte counter and pause/resume controls. Progress is visible as JSON and in the panel.

---

**Contents** &nbsp;·&nbsp; [Why](#why-this-exists) &nbsp;·&nbsp; [What it does](#what-it-does) &nbsp;·&nbsp; [Quickstart](#quickstart) &nbsp;·&nbsp; [API](#api) &nbsp;·&nbsp; [Screenshots](#screenshots) &nbsp;·&nbsp; [Measured](#measured-not-estimated) &nbsp;·&nbsp; [Architecture](#architecture) &nbsp;·&nbsp; [Quality gates](#quality-gates) &nbsp;·&nbsp; [Deploy](#deploy) &nbsp;·&nbsp; [Limits](#limits-stated-rather-than-hidden)

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

The same work from the CLI:

```sh
python -m ctfile_downloader.cli --help
```

Commands: `dl`.

A first request:

```sh
curl -s http://127.0.0.1:8000/api/tasks | head
```

## Requirements

- Python **3.11+** — CI runs 3.11, 3.12 and 3.13.
- Runtime dependencies: `Flask>=3.0`, `Flask-SQLAlchemy>=3.1`, `SQLAlchemy>=2.0`, `PyYAML>=6.0`, `aiohttp`, `beautifulsoup4`.
- No JavaScript build step: every page is server-rendered Jinja.

## API

Every route below is in [`openapi/netgrab.yaml`](openapi/netgrab.yaml) and is exercised by the live probe recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/api/tasks` | list |
| `POST` | `/api/tasks` | create task |
| `POST` | `/api/tasks/<id>/pause` | pause |
| `POST` | `/api/tasks/<id>/resume` | resume |

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

## Measured, not estimated

These numbers were produced on this checkout by `pytest --cov` and by booting `wsgi.py` and issuing one real GET per documented path. The commands are in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Signal | Value |
| --- | --- |
| Tests | **25 / 25 passed** (2.5 s, exit 0) |
| Line coverage | **63.7%** — 441 of 652 statements |
| Source | 15 files / 1,430 lines |
| Test code | 4 files / 346 lines |
| Documented paths | 3 in the spec, 1 GET |
| Live probe | 9 GET requests to the booted app, **8 answered 200** |
| Median latency | **15.9 ms** (single uncached request, dev server) |
| Slowest / fastest | 96.1 ms `/` / 3.3 ms `/readyz` |
| Bytes served | 8.9 KB across 9 responses |
| Screenshots | 6 captured |

## Architecture

```
netgrab/
├── src/ctfile_downloader/
│   ├── http.py                         379  HTTP plumbing for ctfile_downloader: correlation ids
│   ├── _app.py                         212  Web UI for ctfile-downloader: queue tasks, watch per
│   ├── config.py                       171  Environment-driven configuration for ctfile_download
│   ├── observability.py                169  Structured logging and request correlation for ctfil
│   ├── app.py                          119  Application factory for ctfile_downloader
│   ├── errors.py                       108  Typed application errors and their HTTP mapping for 
│   ├── dl/api.py                        98  
│   ├── paths.py                         52  Filesystem layout for ctfile_downloader
│   ├── cli.py                           47  
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
| Coverage | `pytest --cov` | floor set in `pyproject.toml` from the measured value |
| Lint | `ruff check src tests` | zero findings |
| Format | `ruff format --check src tests` | zero reformats |
| Types | `mypy src` | zero errors |
| Security | `bandit -c pyproject.toml -r src` | reviewed skip list, no unreviewed finding |
| Live routes | boot `wsgi.py`, one GET per documented path | no 5xx, no undocumented guard |

CI runs the first six on Python 3.11, 3.12 and 3.13 for every push to `main`, plus a container build. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Deploy

```sh
docker build -t netgrab .
docker run --rm -p 8000:8000 --env-file .env.example netgrab
```

Configuration is environment-only — every variable is documented in [`.env.example`](.env.example), and the service refuses to start with a production secret missing.

## Limits, stated rather than hidden

- One worker process; concurrency is a configuration value, not a queue service.
- Resume reopens the partial file at its current size; an origin that ignores Range makes the task start over.

## License

MIT — see [LICENSE](LICENSE).
