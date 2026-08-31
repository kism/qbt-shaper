# qbt-shaper

[![Check](https://github.com/kism/qbt-shaper/actions/workflows/check.yml/badge.svg)](https://github.com/kism/qbt-shaper/actions/workflows/check.yml)
[![CheckType](https://github.com/kism/qbt-shaper/actions/workflows/check_types.yml/badge.svg)](https://github.com/kism/qbt-shaper/actions/workflows/check_types.yml)
[![Test](https://github.com/kism/qbt-shaper/actions/workflows/test.yml/badge.svg)](https://github.com/kism/qbt-shaper/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/kism/qbt-shaper/graph/badge.svg?token=FPGDA0ODT7)](https://codecov.io/gh/kism/qbt-shaper)

Throttles qBittorrent so your torrents don't ruin your streams.

It polls Jellyfin and Dispatcharr for active streams and applies speed limits to
one or more qBittorrent instances. qBittorrent instances are grouped by
`priority` (lower number = higher priority); upload used by a higher priority
group is subtracted from the caps given to lower priority groups.

Optionally, Home Assistant presence entities select a different set of limits
when nobody is home, and a bedtime window can force the "vacant" limits.

## Install

Install uv: <https://docs.astral.sh/uv/getting-started/installation/>

```bash
uv venv
source .venv/bin/activate
uv sync # add --all-extras for the lint/type/test tooling
```

## Run

```bash
uv run qbt-shaper
```

Options: `-v` (repeat for more verbosity), `--config PATH`.

## Config

JSON, at `~/.config/qbt-shaper/config.json` by default. Override with `--config`
or the `QBT_SHAPER_CONFIG_PATH` environment variable (a `.env` file works too).

Run the app once to write a config file populated with defaults, then fill it
in. All fields and defaults are defined in
[config.py](src/qbt_shaper/config.py).

Speeds in the config are kbps. `*_streaming_percent`, `*_present_percent` and
`*_vacant_percent` are percentages of `dl_max_kbps`/`ul_max_kbps`.

## Development

| Task       | Command                           |
| ---------- | --------------------------------- |
| Lint       | `ruff format && ruff check --fix` |
| Type check | `mypy && ty check .`              |
| Test       | `pytest`                          |
| Coverage   | `coverage run && coverage report` |
| Full CI    | `bash scripts/run-ci-local.sh`    |

All tooling config lives in [pyproject.toml](pyproject.toml).
