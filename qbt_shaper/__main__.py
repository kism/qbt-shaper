"""Main Entrypoint."""

import argparse
import asyncio

from dotenv import load_dotenv
from rich import traceback

from .config import load_config
from .constants import PROGRAM_NAME, PROGRAM_NAME_WITH_VERSION
from .loop import run_loop
from .utils.logger import get_logger, setup_logger_cli

traceback.install(extra_lines=2)
logger = get_logger(__name__)


def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME, description=PROGRAM_NAME_WITH_VERSION)
    parser.add_argument(
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times).",
    )
    return parser.parse_args()


def main() -> None:
    """Main Entrypoint."""
    args = _get_args()
    setup_logger_cli(args.v)
    logger.info("%s", PROGRAM_NAME_WITH_VERSION)
    load_dotenv()
    config = load_config()
    asyncio.run(run_loop(config))


if __name__ == "__main__":
    main()  # pragma: no cover
