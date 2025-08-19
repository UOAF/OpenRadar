from dataclasses import fields, dataclass
import config

# Legacy color map - now replaced by config system
# TACVIEW_COLOR_MAP = {
#     "White": (1.0, 1.0, 1.0, 1.0),  # white
#     "Green": (0.0, 1.0, 0.0, 1.0),  # green
#     "Blue": (0.0, 0.0, 1.0, 1.0),  # blue
#     "Brown": (0.5, 0.25, 0.0, 1.0),  # brown
#     "Orange": (1.0, 0.5, 0.0, 1.0),  # orange
#     "Yellow": (1.0, 1.0, 0.0, 1.0),  # yellow
#     "Red": (1.0, 0.0, 0.0, 1.0),  # red
#     "Black": (0.0, 0.0, 0.0, 1.0),  # black
#     "White": (1.0, 1.0, 1.0, 1.0),  # white
# }


def rgba_from_str(color_name: str) -> tuple[float, float, float, float]:
    """Get RGBA color from color name using config system.
    
    # Mapping from tacview color indices to color names:
    # 0=white
    # 1=green
    # 2=blue
    # 3=brown
    # 4=orange
    # 5=yellow
    # 6=red
    # 7=black
    # 8=white
    """
    try:
        return config.app_config.get_color_rgba("tacview_colors", color_name)
    except (KeyError, ValueError):
        # Return white as default if color not found
        return (1.0, 1.0, 1.0, 1.0)


# Function to extract all attributes from GameObject instances (non-dataclass)
def get_all_attributes(instance):
    """Extract all attributes from a GameObject instance, including properties.
    
    Args:
        instance: A GameObject instance (not a dataclass)
        
    Returns:
        dict: Dictionary of attribute names and their values
    """
    attributes = {}

    # Get all instance attributes (excluding private ones and methods)
    for attr_name in dir(instance):
        if not attr_name.startswith('_'):  # Skip private attributes
            try:
                attr_value = getattr(instance, attr_name)
                # Skip methods/functions, only include data
                if not callable(attr_value):
                    attributes[attr_name] = attr_value
            except:
                # Skip attributes that can't be accessed
                pass

    return attributes


# Function to extract all attributes, including properties
def get_all_dc_attributes(instance):
    # Get dataclass fields
    dataclass_fields = {field.name: getattr(instance, field.name) for field in fields(instance)}
    # Get properties
    property_fields = {
        attr: getattr(instance, attr)
        for attr in dir(instance) if isinstance(getattr(type(instance), attr, None), property)
    }
    # Combine both
    return {**dataclass_fields, **property_fields}
