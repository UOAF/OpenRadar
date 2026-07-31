from game_object import GameObject
from game_object_types import GameObjectType
from dataclasses import dataclass, field
from enum import Enum
import json

import config


@dataclass(frozen=True)
class TrackLabelLocationData():
    index: int
    ui_reference_coords: tuple[int, int]
    description: str
    render_coords: tuple[float, float]


class TrackLabelLocation(Enum):
    TOP_LEFT = TrackLabelLocationData(0, (0, 0), "Top Left", (-1, 0))
    TOP_CENTER = TrackLabelLocationData(1, (0, 1), "Top", (-0.5, 0))
    TOP_RIGHT = TrackLabelLocationData(2, (0, 2), "Top Right", (0.0, 0.0))
    LEFT = TrackLabelLocationData(3, (1, 0), "Left", (-1, 0.5))
    CENTER = TrackLabelLocationData(4, (1, 1), "Center", (-0.5, 0.5))
    RIGHT = TrackLabelLocationData(5, (1, 2), "Right", (0.0, 0.5))
    BOTTOM_LEFT = TrackLabelLocationData(6, (2, 0), "Bottom Left", (-1, -1))
    BOTTOM_CENTER = TrackLabelLocationData(7, (2, 1), "Bottom Center", (-0.5, -1))
    BOTTOM_RIGHT = TrackLabelLocationData(8, (2, 2), "Bottom Right", (0.0, -1))

    def __eq__(self, value: object) -> bool:
        if isinstance(value, tuple) and len(value) == 2:
            return self.value.ui_reference_coords == value
        return super().__eq__(value)

    def __hash__(self) -> int:
        return hash(self.value.ui_reference_coords)


def get_label_loc_by_ui_coords(ui_coords: tuple[int, int]) -> TrackLabelLocation:
    for location in TrackLabelLocation:
        if location.value.ui_reference_coords == ui_coords:
            return location
    raise ValueError(f"No TrackLabelLocation found with ui_reference_coords {ui_coords}")


@dataclass
class TrackLabel:
    label_name: str
    label_format: str
    show_on_hover: bool = False


@dataclass
class TrackLabels:
    type: GameObjectType
    labels: dict[TrackLabelLocation, TrackLabel] = field(default_factory=dict)


def serialize_track_labels(track_labels: TrackLabels) -> tuple[str, str]:
    classname = track_labels.type.name
    data_string = json.dumps({
        location.name: {
            "label_name": track_label.label_name,
            "label_format": track_label.label_format,
            "show_on_hover": track_label.show_on_hover
        }
        for location, track_label in track_labels.labels.items()
    })

    return classname, data_string


def deserialize_track_labels(classtype: str, data: str) -> TrackLabels | None:
    try:
        data_dict = json.loads(data)
        return TrackLabels(type=GameObjectType[classtype],
                           labels={
                               TrackLabelLocation[location]: TrackLabel(**track_label)
                               for location, track_label in data_dict.items()
                           })
    except (KeyError, ValueError, TypeError) as e:
        print(f"Invalid Track labels format in config file, using default labels: {e}")
        try:
            config.app_config.set_default("labels", classtype)
            return deserialize_track_labels(classtype, config.app_config.get_str("labels", classtype))

        except Exception as e:
            raise ValueError(f"Failed to set default labels for {classtype}: {e}")


def get_labels_for_class_type(class_type: GameObjectType) -> TrackLabels | None:

    labels = deserialize_track_labels(class_type.name, config.app_config.get_str(
        "labels", class_type.name))  # TODO: this may be slow, consider caching

    return labels


class _LabelFieldMapping:
    """Resolves label placeholder names to GameObject attributes on demand.

    Used with str.format_map, which only calls __getitem__ for placeholders
    actually present in the format string - unreferenced attributes/properties
    (e.g. expensive ones like magnetic_heading) are never touched.
    """

    def __init__(self, instance: GameObject):
        self._instance = instance

    def __getitem__(self, key: str):
        if key == "id":
            return self._instance.object_id
        if key == "type":
            object_type = self._instance.object_type
            return object_type.name if hasattr(object_type, 'name') else str(object_type)
        if key == "name":
            return self._instance.get_display_name()

        try:
            value = getattr(self._instance, key)
        except AttributeError:
            raise KeyError(key)

        if callable(value):
            raise KeyError(key)
        return value


def evaluate_input_format(user_input: str, instance: GameObject) -> str:
    try:
        return user_input.format_map(_LabelFieldMapping(instance))
    except Exception as e:
        return f"Error evaluating user input: {e}"


# default_label = {TrackLabelLocation.TOP_LEFT: TrackLabel("Top Left", "{id}"),}
# default_labels = TrackLabels(GameObjectClassType.FIXEDWING, default_label)

# print(serialize_track_labels(default_labels))
# print(deserialize_track_labels(*serialize_track_labels(default_labels)))

# cls_name, ser = serialize_track_labels(default_labels)
# if ser == serialize_track_labels(deserialize_track_labels(cls_name, ser)):
#     print("Test good")
