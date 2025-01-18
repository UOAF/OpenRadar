from dataclasses import fields, dataclass

# Function to extract all attributes, including properties
def get_all_attributes(instance):
    # Get dataclass fields
    dataclass_fields = {field.name: getattr(instance, field.name) for field in fields(instance)}
    # Get properties
    property_fields = {
        attr: getattr(instance, attr)
        for attr in dir(instance)
        if isinstance(getattr(type(instance), attr, None), property)
    }
    # Combine both
    return {**dataclass_fields, **property_fields}
