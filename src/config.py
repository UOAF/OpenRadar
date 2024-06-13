import tomlkit
from typing import Type
CONFIG_DEFAULTS = "src/defaults.toml"
DEFAULT_CONFIG_FILE = "config.toml"

class RadarConfig:
    def __init__(self, config_file: str = DEFAULT_CONFIG_FILE):
        
        self.config_file = config_file
        self.config: tomlkit.TOMLDocument

        try:
            with open (self.config_file) as f:
                self.config = tomlkit.parse(f.read())
        except FileNotFoundError:
            self.set_defaults()
            self.save()

    def get(self, heading, key, requested_type: Type):
        try:
            val = requested_type(self.config.get(heading).get(key))
            return val
        except TypeError as e:
            print (e)
        # raise TypeError(
        #     f'''Config value "{key}" Under heading "{heading}" in file {self.config_file} is not of correct type,
        #     Expected: {requested_type}, given: {type(val)}''')
    
    def set_defaults(self):
        with open (CONFIG_DEFAULTS) as f:
            self.config = tomlkit.parse(f.read())
            
    def save(self):
        with open(self.config_file, "w") as f:
            f.write(tomlkit.dumps(self.config))
