"""Tests for RadarConfig.

Covers the read cache, the corrupt-config recovery path, atomic saving, and the
defaults-copy behaviour - none of which were covered before.
"""
import atexit
import shutil
import tempfile
from pathlib import Path

import pytest

from config import RadarConfig

BUNDLE_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture
def config_dir():
    """An empty directory to hold a throwaway openradar.toml."""
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(path, ignore_errors=True)


def make_config(config_dir: Path) -> RadarConfig:
    cfg = RadarConfig(config_file=config_dir / "openradar.toml",
                      bundle_dir=BUNDLE_DIR,
                      application_dir=config_dir)
    # RadarConfig registers save() with atexit. In tests the temp directory is long gone
    # by interpreter shutdown, so leave the handler out to keep the output clean.
    atexit.unregister(cfg.save)
    return cfg


class TestDefaults:

    def test_missing_config_is_created_from_defaults(self, config_dir):
        cfg = make_config(config_dir)

        assert (config_dir / "openradar.toml").exists()
        assert cfg.get_int("radar", "contact_size") > 0

    def test_set_does_not_mutate_the_defaults_document(self, config_dir):
        """set_all_defaults must deep copy.

        Aliasing meant every later set() also edited config_defaults, which silently
        turned the UI's "reset to defaults" into a no-op for the rest of the session.
        """
        cfg = make_config(config_dir)
        pristine = int(str(cfg.config_defaults["radar"]["contact_size"]))

        cfg.set("radar", "contact_size", pristine + 25)

        assert int(str(cfg.config_defaults["radar"]["contact_size"])) == pristine

    def test_missing_key_falls_back_to_default(self, config_dir):
        cfg = make_config(config_dir)
        expected = cfg.get_int("radar", "contact_size")

        del cfg.config["radar"]["contact_size"]
        cfg._value_cache.pop(("radar", "contact_size"), None)

        assert cfg.get_int("radar", "contact_size") == expected


class TestValueCache:

    def test_repeated_reads_are_stable(self, config_dir):
        cfg = make_config(config_dir)

        assert cfg.get_int("radar", "contact_size") == cfg.get_int("radar", "contact_size")

    def test_read_after_write_sees_the_new_value(self, config_dir):
        """The cache must be invalidated by set(), or the UI appears to ignore edits."""
        cfg = make_config(config_dir)
        cfg.get_int("radar", "contact_size")  # populate the cache

        cfg.set("radar", "contact_size", 33)

        assert cfg.get_int("radar", "contact_size") == 33

    def test_cached_list_is_not_aliased_to_callers(self, config_dir):
        """Mutating a returned list must not corrupt the cached value."""
        cfg = make_config(config_dir)

        first = cfg.get_list_int("map", "background_color")
        first.append(999)

        assert 999 not in cfg.get_list_int("map", "background_color")


class TestTypeConversion:

    def test_scalar_types(self, config_dir):
        cfg = make_config(config_dir)

        assert isinstance(cfg.get_int("radar", "contact_size"), int)
        assert isinstance(cfg.get_float("radar", "contact_font_scale"), float)
        assert isinstance(cfg.get_str("display", "icon_set"), str)
        assert isinstance(cfg.get_bool("layers", "show_fixed_wing"), bool)

    def test_colors(self, config_dir):
        cfg = make_config(config_dir)

        color = cfg.get_color("map", "background_color")
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)

        normalized = cfg.get_color_normalized("map", "background_color")
        assert all(0.0 <= c <= 1.0 for c in normalized)

    def test_generic_alias_lookup(self, config_dir):
        """app.py reads the window size with a tuple[int, int] type."""
        cfg = make_config(config_dir)

        size = cfg.get("window", "size", tuple[int, int])

        assert len(size) == 2


class TestPersistence:

    def test_save_round_trips(self, config_dir):
        cfg = make_config(config_dir)
        cfg.set("radar", "contact_size", 42)
        cfg.save()

        assert make_config(config_dir).get_int("radar", "contact_size") == 42

    def test_save_leaves_no_temp_file(self, config_dir):
        cfg = make_config(config_dir)
        cfg.save()

        assert not list(config_dir.glob("*.tmp"))

    def test_save_to_unwritable_path_does_not_raise(self, config_dir):
        """save() runs from atexit, so a read-only install dir must not throw."""
        cfg = make_config(config_dir)
        cfg.config_file_path = config_dir / "no-such-dir" / "openradar.toml"

        cfg.save()  # must not raise


class TestCorruptConfigRecovery:

    def test_unparseable_config_falls_back_to_defaults(self, config_dir):
        """A truncated config used to be fatal, and before logging was even set up."""
        (config_dir / "openradar.toml").write_text("[window]\nsize = [1920, 1060\n### truncated",
                                                   encoding="utf-8")

        cfg = make_config(config_dir)

        assert cfg.get_int("radar", "contact_size") > 0

    def test_unparseable_config_is_preserved_for_diagnosis(self, config_dir):
        (config_dir / "openradar.toml").write_text("not = = valid toml", encoding="utf-8")

        make_config(config_dir)

        assert (config_dir / "openradar.toml.corrupt").exists()
