import pytest

from ingestion.config import load_database_settings

VALID_ENV = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "leu_watch",
    "POSTGRES_USER": "leu_watch",
    "POSTGRES_PASSWORD": "secret",
}


def test_reads_all_settings_and_converts_port_to_int():
    settings = load_database_settings(VALID_ENV)

    assert settings.host == "localhost"
    assert settings.port == 5432
    assert settings.dbname == "leu_watch"
    assert settings.user == "leu_watch"
    assert settings.password == "secret"


def test_missing_or_empty_variables_are_named_in_the_error():
    env = {**VALID_ENV, "POSTGRES_PASSWORD": ""}
    del env["POSTGRES_HOST"]

    with pytest.raises(RuntimeError, match="POSTGRES_HOST, POSTGRES_PASSWORD"):
        load_database_settings(env)


def test_password_is_hidden_from_repr():
    settings = load_database_settings(VALID_ENV)

    assert "secret" not in repr(settings)
