"""Tests for track label formatting.

evaluate_input_format() renders user-authored template strings against a GameObject. It
was rewritten to use str.format_map over a lazy mapping instead of eval(), which both
removed arbitrary code execution on config-supplied text and stopped every property being
evaluated on every label. These tests pin that behaviour down.
"""
import json

import pytest
import tomlkit

from game_object import GameObject
from game_object_types import GameObjectType
from util.track_labels import (deserialize_track_labels, evaluate_input_format, serialize_track_labels)

from test_config import BUNDLE_DIR

ALL_TYPES = ["FIXEDWING", "ROTARYWING", "MISSILE", "GROUND", "SEA", "BULLSEYE", "UNKNOWN"]


@pytest.fixture
def track():
    """A fixed-wing track with known values, so expected output is deterministic."""
    obj = GameObject("3001", GameObjectType.FIXEDWING)
    obj.CallSign = "Viper11"
    obj.Altitude = 7500.0  # metres -> 24606 ft
    obj.CAS = 200.0
    obj.Mach = 0.8532000184059143
    obj.Heading = 270.0
    obj.U = 50000.0
    obj.V = 30000.0
    obj.bull_x = 0.0
    obj.bull_y = 0.0
    return obj


class TestSubstitution:

    def test_plain_field(self, track):
        assert evaluate_input_format("{display_name}", track) == "Viper11"

    def test_literal_text_is_preserved(self, track):
        assert evaluate_input_format("ANGELS {altitude_1000ft:.0f}", track) == "ANGELS 25"

    def test_multiple_placeholders(self, track):
        assert evaluate_input_format("{altitude_ft_floor100:.0f}ft M{Mach:.2f}", track) == "24600ft M0.85"

    def test_raw_acmi_field(self, track):
        assert evaluate_input_format("{Mach:.2f}", track) == "0.85"

    @pytest.mark.parametrize("alias,expected", [("{id}", "3001"), ("{name}", "Viper11"),
                                                ("{type}", "FIXEDWING")])
    def test_aliases(self, track, alias, expected):
        """id/name/type are not real attributes - the mapping special-cases them."""
        assert evaluate_input_format(alias, track) == expected


class TestFormatSpecs:

    def test_decimal_places(self, track):
        assert evaluate_input_format("{altitude_ft:.0f}", track) == "24606"

    def test_bullseye_is_indexable(self, track):
        result = evaluate_input_format("{bullseye[0]:.0f}/{bullseye[1]:.0f}", track)

        bearing, _, distance = result.partition("/")
        assert bearing.isdigit() and distance.isdigit()

    @pytest.mark.parametrize("heading,expected", [(3.0, "003"), (59.0, "059"), (297.0, "297")])
    def test_bearings_zero_pad_to_three_digits(self, track, heading, expected):
        """`:03.0f` is the conventional bearing format, e.g. 005 rather than 5.

        Uses the raw Heading field rather than magnetic_heading, which applies the
        configured magnetic variation and so is not fixed by the object alone.
        """
        track.Heading = heading

        assert evaluate_input_format("{Heading:03.0f}", track) == expected


class TestErrorHandling:

    def test_unknown_field_returns_error_string(self, track):
        """A bad template must not raise - it renders an error in place of the label."""
        result = evaluate_input_format("{not_a_real_field}", track)

        assert "Error" in result

    def test_field_names_are_case_sensitive(self, track):
        assert "Error" in evaluate_input_format("{mach}", track)
        assert evaluate_input_format("{Mach:.2f}", track) == "0.85"

    def test_methods_are_not_callable_from_templates(self, track):
        """Callables are rejected so templates stay data-only."""
        assert "Error" in evaluate_input_format("{get_display_name}", track)


class TestLazyEvaluation:

    def test_unreferenced_properties_are_not_evaluated(self, track, monkeypatch):
        """The whole point of format_map: only referenced placeholders are resolved.

        The old implementation walked dir() and evaluated every property - including
        expensive ones like magnetic_heading - for every label on every object.
        """
        calls = []
        monkeypatch.setattr(type(track), "magnetic_heading",
                            property(lambda self: calls.append(1) or 0.0))

        evaluate_input_format("{display_name}", track)
        assert calls == []

        evaluate_input_format("{magnetic_heading:.0f}", track)
        assert len(calls) == 1


class TestSerialization:

    def test_round_trip(self):
        labels = deserialize_track_labels(
            "FIXEDWING",
            json.dumps({
                "TOP_RIGHT": {
                    "label_name": "TR",
                    "label_format": "{display_name}",
                    "show_on_hover": False
                }
            }))
        assert labels is not None

        _, data = serialize_track_labels(labels)
        reparsed = deserialize_track_labels("FIXEDWING", data)

        assert reparsed is not None
        assert [t.label_format for t in reparsed.labels.values()] == ["{display_name}"]


class TestShippedDefaults:
    """Every label format in defaults.toml must render against a real GameObject."""

    @staticmethod
    def shipped_labels():
        doc = tomlkit.parse((BUNDLE_DIR / "resources/config/defaults.toml").read_text(encoding="utf-8"))
        return doc["labels"]

    @pytest.mark.parametrize("type_name", ALL_TYPES)
    def test_defaults_deserialize(self, type_name):
        assert deserialize_track_labels(type_name, str(self.shipped_labels()[type_name])) is not None

    @pytest.mark.parametrize("type_name", ALL_TYPES)
    def test_defaults_render_without_errors(self, track, type_name):
        labels = deserialize_track_labels(type_name, str(self.shipped_labels()[type_name]))
        assert labels is not None

        for track_label in labels.labels.values():
            rendered = evaluate_input_format(track_label.label_format, track)
            assert "Error" not in rendered, f"{type_name} label {track_label.label_format!r} -> {rendered}"
