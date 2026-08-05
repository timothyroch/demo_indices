import os


def _env_flag(name: str, default: str = "false") -> bool:
    value = os.environ.get(name, default)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def auth_disabled() -> bool:
    return _env_flag("AUTH_DISABLED", "false")
