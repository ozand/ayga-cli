"""A-Parser CLI commands."""

from aparser_cli.commands.ping import app as ping_app
from aparser_cli.commands.parsers import app as parsers_app
from aparser_cli.commands.redis import app as redis_app

__all__ = ["ping_app", "parsers_app", "redis_app"]
