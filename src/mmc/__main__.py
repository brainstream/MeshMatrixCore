if __name__ == "__main__":
    import asyncio
    import sys

    from mmc.cli import main

    sys.exit(asyncio.run(main()))
