
from game_state import GameObjectClassType
from dataclasses import dataclass, field, fields
from enum import Enum
import json


@dataclass(frozen=True)
class TrackLabelLocationData():
    index: int
    ui_reference_coords: tuple[int, int]
    description: str
    render_coords: tuple[float, float] 

class TrackLabelLocation(Enum):
    TOP_LEFT = TrackLabelLocationData(0, (0, 0), "Top Left", (0.0, 0.0))
    TOP_CENTER = TrackLabelLocationData(1, (1, 0), "Top", (0.0, 0.0))
    TOP_RIGHT = TrackLabelLocationData(2, (2, 0), "Top Right", (0.0, 0.0))
    LEFT = TrackLabelLocationData(3, (0, 1), "Left", (0.0, 0.0))
    RIGHT = TrackLabelLocationData(5, (2, 1), "Right", (0.0, 0.0))
    BOTTOM_LEFT = TrackLabelLocationData(6, (0, 2), "Bottom Left", (0.0, 0.0))
    BOTTOM_CENTER = TrackLabelLocationData(7, (1, 2), "Center", (0.0, 0.0))
    BOTTOM_RIGHT = TrackLabelLocationData(8, (2, 2), "Bottom Right", (0.0, 0.0))
    
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
    type: GameObjectClassType
    labels: dict[TrackLabelLocation, TrackLabel] = field(default_factory=dict)
    
def serialize_track_labels(track_labels: TrackLabels) -> tuple[str, str]:
    classname = track_labels.type.name
    data_string = json.dumps({
        location.name: {
            "label_name": track_label.label_name,
            "label_format": track_label.label_format,
            "show_on_hover": track_label.show_on_hover
        } for location, track_label in track_labels.labels.items()
    })
    
    return classname, data_string
           

def deserialize_track_labels(classtype:str, data: str) -> TrackLabels | None:
    try:
        data_dict = json.loads(data)
        return TrackLabels(
            type=GameObjectClassType[classtype],
            labels={
                TrackLabelLocation[location]: TrackLabel(**track_label)
                for location, track_label in data_dict.items()
            }
        )
    except (KeyError, ValueError, TypeError) as e: 
        print(f"Invalid Track labels format in config file, using default labels: {e}")
        return None

def evaluate_input_format(user_input, instance):
    # Create a context with all dataclass fields
    context = {field.name: getattr(instance, field.name) for field in fields(instance)}
    # Add properties to context
    context.update({
        attr: getattr(instance, attr)
        for attr in dir(instance)
        if isinstance(getattr(type(instance), attr, None), property)
    })
    # Use eval to evaluate expressions within {}
    try:
        output = eval(f"f'{user_input}'", {}, context)  
    except Exception as e:
        output = (f"Error evaluating user input: {e}")
        # print(output)
    return output
        
    
# default_label = {TrackLabelLocation.TOP_LEFT: TrackLabel("Top Left", "{id}"),}
# default_labels = TrackLabels(GameObjectClassType.FIXEDWING, default_label)

# print(serialize_track_labels(default_labels))
# print(deserialize_track_labels(*serialize_track_labels(default_labels)))

# cls_name, ser = serialize_track_labels(default_labels)
# if ser == serialize_track_labels(deserialize_track_labels(cls_name, ser)):
#     print("Test good")
