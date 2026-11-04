"""Database settings, read from environment variables.

Locally the variables come from the .env file (see .env.example);
in GitHub Actions they will come from GitHub Secrets.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from dotenv import load_dotenv

REQUIRED_VARIABLES = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    dbname: str
    user: str
    # repr=False keeps the password out of logs and error messages.
    password: str = field(repr=False)


def load_database_settings(env: Mapping[str, str] | None = None) -> DatabaseSettings:
    """Return the database settings, failing early if any variable is missing.

    `env` is only passed by tests; normally the settings are read from the
    process environment, after loading the .env file if there is one.
    """
    if env is None:
        load_dotenv()
        env = os.environ

    missing = [name for name in REQUIRED_VARIABLES if not env.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in the values."
        )

    return DatabaseSettings(
        host=env["POSTGRES_HOST"],
        port=int(env["POSTGRES_PORT"]),
        dbname=env["POSTGRES_DB"],
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
    )
