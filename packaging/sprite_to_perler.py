"""Entry point for the packaged Windows program (same code as `python -m perler_app`)."""
import sys

from perler_app.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
