# qbt-shaper — Agent Instructions

Async Python app that monitors Jellyfin/Dispatcharr for active streams and throttles qBittorrent upload/download speeds accordingly. Optional Home Assistant integration for presence-based limits.

## Setup

```bash
uv venv
source .venv/bin/activate
uv sync --all-extras
```

## Common Commands

| Task            | Command                           |
| --------------- | --------------------------------- |
| Run app         | `python -m qbt_shaper`            |
| Lint (fix)      | `ruff format && ruff check --fix` |
| Type check      | `mypy && ty check .`              |
| Tests           | `pytest`                          |
| Coverage        | `coverage run && coverage report` |
| Full CI locally | `bash scripts/run-ci-local.sh`    |

## Architecture

- **`config.py`** — Pydantic v2 models; config stored at `~/.config/qbt-shaper/config.json`. On startup, config is written back to disk to populate defaults.
- **`loop.py`** — Main async loop (15 s poll interval, 60 s presence check interval). Creates service clients and `PriorityThrottler`, then loops forever.
- **`throttle.py`** — `PriorityThrottler`: groups qBittorrent instances by `priority` (lower = higher priority). Higher-priority groups' upload usage proportionally reduces lower-priority groups' upload caps.
- **`services/`** — One async client per external service:
  - `qbittorrent.py` — wraps synchronous `qbittorrentapi` in `asyncio.to_thread`; caches last-applied limits to skip redundant API calls.
  - `jellyfin.py`, `dispatcharr.py` — use a shared `aiohttp.ClientSession`; `dispatcharr.py` re-authenticates on HTTP 401.
  - `homeassistant.py` — presence detection via Home Assistant entity states.
- **`utils/logger.py`** — `get_logger(__name__)` for all modules; `setup_logger_cli()` for verbosity levels.

## Conventions

- Python 3.12+; use `X | Y` not `Union[X, Y]`
- All tooling configured in [`pyproject.toml`](pyproject.toml): ruff (ALL rules, see ignores), mypy (strict), pytest, coverage
- `ruff` select `"ALL"` — check pyproject.toml `[tool.ruff.lint.ignore]` before adding code that would trigger new rules
- Docstrings are **not required** (D rules ignored)
- Speeds are stored/passed as bytes/s internally; config uses kbps; KiB/s used in log messages
- `_applied_*` cache pattern on `QbittorrentClient` to avoid redundant API calls — maintain this pattern when adding new settings
