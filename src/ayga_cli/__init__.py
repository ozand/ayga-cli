"""ayga_parser CLI Tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ayga-cli")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
