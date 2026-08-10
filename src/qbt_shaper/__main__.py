"""Main Entrypoint."""

import argparse
import asyncio
from pathlib import Path

from .config import DEFAULT_CONFIG_PATH, load_config, write_config
from .constants import PROGRAM_NAME, PROGRAM_NAME_WITH_VERSION
from .loop import run_loop
from .utils.logger import get_logger, setup_logger_cli

logger = get_logger(__name__)


def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME, description=PROGRAM_NAME_WITH_VERSION)
    parser.add_argument(
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        metavar="PATH",
        help=f"Path to JSON config file (default: {DEFAULT_CONFIG_PATH}).",
    )
    return parser.parse_args()


def main() -> None:
    """Main Entrypoint."""
    args = _get_args()
    setup_logger_cli(args.v)
    logger.info("%s", PROGRAM_NAME_WITH_VERSION)
    config = load_config(args.config)
    write_config(config, args.config)
    asyncio.run(run_loop(config))


if __name__ == "__main__":
    try:
        main()  # pragma: no cover
    except KeyboardInterrupt:
        logger.info("Goodbye!")
