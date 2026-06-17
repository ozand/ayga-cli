"""Exit codes contract for ayga-cli. These are the official codes for machine consumers."""

SUCCESS = 0          # Data returned in stdout
ERROR_GENERAL = 1    # Unknown/general error
ERROR_TIMEOUT = 2    # Server did not respond in time
ERROR_NOT_FOUND = 3  # Source not found on server
ERROR_UNAVAILABLE = 4 # Redis Wrapper unreachable
ERROR_INPUT = 5      # Invalid input (bad source name, empty query)

DESCRIPTIONS = {
    SUCCESS: "Success",
    ERROR_GENERAL: "General error",
    ERROR_TIMEOUT: "Timeout — server did not respond",
    ERROR_NOT_FOUND: "Source not found",
    ERROR_UNAVAILABLE: "Server unavailable",
    ERROR_INPUT: "Invalid input",
}
