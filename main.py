"""
Legacy entrypoint kept for systemd/service scripts.

All implementation now lives under the `pianolog/` package.
"""

from pianolog.cli import main


if __name__ == "__main__":
    main()
