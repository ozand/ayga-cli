"""ayga-parser CLI commands."""

from ayga_cli.commands.ping import app as ping_app
from ayga_cli.commands.parsers import app as parsers_app
from ayga_cli.commands.redis import app as redis_app

__all__ = ["ping_app", "parsers_app", "redis_app"]
