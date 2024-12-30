import tomlkit
from typing import Type
from pathlib import Path

import sys

CONFIG_DEFAULTS = Path("resources/config/defaults.toml")
DEFAULT_CONFIG_FILE = Path("config.toml")

class RadarConfig:
    def __init__(self, config_file: Path = DEFAULT_CONFIG_FILE, bundle_dir: Path = Path('.')):
        
        self.config_file_path = config_file
        self.config_defaults_path = bundle_dir / CONFIG_DEFAULTS
        self.config: tomlkit.TOMLDocument
        self.config_defaults: tomlkit.TOMLDocument
        
        with self.config_defaults_path.open("r") as f:
            self.config_defaults = tomlkit.parse(f.read())

        if config_file.exists():
            with config_file.open() as f:
                self.config = tomlkit.parse(f.read())
        else:
            self.set_all_defaults()
            self.save()

    def get(self, heading, key, requested_type: Type):

        section = self.config.get(heading)
        if section is None or key not in section:
            return self.set_default(heading, key)

        val = None
        try:
            val = requested_type(section.get(key)) # type: ignore
            return val
        except TypeError as e:
            print (e)
            raise TypeError(f"Config value {key} in heading {heading} in {self.config_file_path} is not castable to correct \
                              type, Expected: {requested_type}, given: {type(val)}")
            
    def get_int(self, heading, key) -> int:
        return int(self.get(heading, key, int)) # type: ignore
    
    def get_str(self, heading, key) -> str:
        return str(self.get(heading, key, str)) # type: ignore
            
    def set(self, heading, key, value):
        if heading not in self.config:
            self.config[heading] = tomlkit.table()
        self.config[heading][key] = value # type: ignore
        self.save()
        
    def set_default(self, heading, key):
        
        if heading not in self.config_defaults:
            raise KeyError(f"Config heading {heading} not found in defaults {self.config_defaults_path}")
        def_val = self.config_defaults[heading][key] # type: ignore
        
        self.set(heading, key, def_val) # type: ignore
        return def_val

    def set_all_defaults(self):  
        self.config = self.config_defaults
            
    def save(self):
        with self.config_file_path.open('w') as f:
            f.write(tomlkit.dumps(self.config))

if 'app_config' not in globals():
    
    
    global bundle_dir
    bundle_dir = Path()
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'): # Running as compiled
        bundle_dir = Path(sys._MEIPASS) # type: ignore
    else:
        bundle_dir = Path(__file__).parent.parent
    
    global app_config
    app_config = RadarConfig(bundle_dir=bundle_dir) # global config
            