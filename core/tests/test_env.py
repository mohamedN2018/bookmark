import pytest
from decouple import UndefinedValueError

from core.env import EnvConfig


@pytest.fixture
def env_file(tmp_path):
    f = tmp_path / ".env"
    f.write_text("FROM_FILE=file-value\nFLAG=true\nEMPTY_IN_FILE=\n", encoding="utf-8")
    return f


def test_environment_wins(env_file, monkeypatch):
    monkeypatch.setenv("FROM_FILE", "env-value")
    assert EnvConfig(env_file)("FROM_FILE") == "env-value"


def test_empty_environment_falls_back_to_file(env_file, monkeypatch):
    monkeypatch.setenv("FROM_FILE", "")
    assert EnvConfig(env_file)("FROM_FILE") == "file-value"


def test_bool_cast_and_default(env_file):
    config = EnvConfig(env_file)
    assert config("FLAG", cast=bool) is True
    assert config("MISSING_FLAG", default=False, cast=bool) is False


def test_missing_without_default_raises(env_file):
    with pytest.raises(UndefinedValueError):
        EnvConfig(env_file)("EMPTY_IN_FILE")


def test_missing_file_is_fine(tmp_path, monkeypatch):
    monkeypatch.setenv("ONLY_ENV", "x")
    assert EnvConfig(tmp_path / "nope.env")("ONLY_ENV") == "x"
