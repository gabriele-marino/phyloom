from argparse import ArgumentParser
from importlib.metadata import version

from phyloom.run import run

DISTRIBUTION_NAME = "phyloom"


def main():
    parser = ArgumentParser(
        description="Generate dataset(s) starting from provided config(s)."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version(DISTRIBUTION_NAME)}",
        help="Show phyloom version and exit.",
    )
    parser.add_argument(
        "config_path",
        type=str,
        help="Path to a config file or a directory containing config files.",
    )
    args = parser.parse_args()

    run(args.config_path)


if __name__ == "__main__":
    main()
