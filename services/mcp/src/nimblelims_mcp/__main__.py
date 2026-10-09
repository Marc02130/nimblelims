"""python -m nimblelims_mcp [--transport stdio|streamable-http]"""

import argparse

from nimblelims_mcp.server import serve, settings_for_cli


def main() -> None:
    parser = argparse.ArgumentParser(description="NimbleLIMS MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        help="Default is MCP_TRANSPORT or streamable-http.",
    )
    args = parser.parse_args()
    serve(settings_for_cli(args.transport))


if __name__ == "__main__":
    main()
