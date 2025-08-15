from dataclasses import fields, dataclass


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
