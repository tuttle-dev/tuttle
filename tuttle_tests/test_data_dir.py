"""Tests for tuttle.data_dir — env-var override and default behaviour."""

import sys

from tuttle.data_dir import get_data_dir


def test_default_is_dot_tuttle_dev_when_unfrozen(monkeypatch, tmp_path):
    """Without TUTTLE_DATA_DIR, an unfrozen (dev/test) run gets ~/.tuttle-dev.

    A source checkout must never fall back to a real user's ~/.tuttle just
    because some script forgot to set TUTTLE_DATA_DIR.
    """
    monkeypatch.delenv("TUTTLE_DATA_DIR", raising=False)
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    import tuttle.data_dir as mod

    monkeypatch.setattr(mod, "_DEFAULT_DEV", fake_home / ".tuttle-dev")
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    result = mod.get_data_dir()
    assert result == fake_home / ".tuttle-dev"
    assert result.is_dir()


def test_default_is_dot_tuttle_when_frozen(monkeypatch, tmp_path):
    """Without TUTTLE_DATA_DIR, a PyInstaller-frozen (production) build gets ~/.tuttle."""
    monkeypatch.delenv("TUTTLE_DATA_DIR", raising=False)
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    import tuttle.data_dir as mod

    monkeypatch.setattr(mod, "_DEFAULT", fake_home / ".tuttle")
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    result = mod.get_data_dir()
    assert result == fake_home / ".tuttle"
    assert result.is_dir()


def test_env_var_overrides_default(monkeypatch, tmp_path):
    """TUTTLE_DATA_DIR overrides the default ~/.tuttle."""
    custom = tmp_path / "custom-data"
    monkeypatch.setenv("TUTTLE_DATA_DIR", str(custom))

    result = get_data_dir()
    assert result == custom
    assert result.is_dir()


def test_creates_directory_if_missing(monkeypatch, tmp_path):
    """The directory is created automatically."""
    target = tmp_path / "does" / "not" / "exist"
    monkeypatch.setenv("TUTTLE_DATA_DIR", str(target))

    result = get_data_dir()
    assert result == target
    assert result.is_dir()


def test_empty_env_var_falls_back_to_default(monkeypatch, tmp_path):
    """An empty TUTTLE_DATA_DIR is treated as unset."""
    monkeypatch.setenv("TUTTLE_DATA_DIR", "")
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    import tuttle.data_dir as mod

    monkeypatch.setattr(mod, "_DEFAULT_DEV", fake_home / ".tuttle-dev")
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    result = mod.get_data_dir()
    assert result == fake_home / ".tuttle-dev"
