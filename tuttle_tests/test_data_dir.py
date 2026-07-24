"""Tests for tuttle.data_dir — env-var override and default behaviour."""

from pathlib import Path

from tuttle.data_dir import get_data_dir


def test_default_is_dot_tuttle(monkeypatch, tmp_path):
    """Without TUTTLE_DATA_DIR, get_data_dir() returns ~/.tuttle."""
    monkeypatch.delenv("TUTTLE_DATA_DIR", raising=False)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

    # Re-import to pick up patched home
    import tuttle.data_dir as mod

    monkeypatch.setattr(mod, "_DEFAULT", fake_home / ".tuttle")

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
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

    import tuttle.data_dir as mod

    monkeypatch.setattr(mod, "_DEFAULT", fake_home / ".tuttle")

    result = mod.get_data_dir()
    assert result == fake_home / ".tuttle"
