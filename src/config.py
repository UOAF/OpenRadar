import atexit
import select

import tomlkit
from typing import Type
from pathlib import Path

import sys
import os

CONFIG_DEFAULTS = Path("resources/config/defaults.toml")
DEFAULT_CONFIG_FILE = "openradar.toml"


class RadarConfig:

    def __init__(self,
                 config_file: Path | None = None,
                 bundle_dir: Path = Path('.'),
                 application_dir: Path = Path(os.getcwd())):

        self.config_defaults_path = bundle_dir / CONFIG_DEFAULTS
        self.config: tomlkit.TOMLDocument
        self.config_defaults: tomlkit.TOMLDocument
        self.bundle_dir = bundle_dir
        self.application_dir = application_dir
        self.config_file_path = config_file if config_file is not None else application_dir / DEFAULT_CONFIG_FILE

        with self.config_defaults_path.open("r") as f:
            self.config_defaults = tomlkit.parse(f.read())

        if self.config_file_path.exists():
            with self.config_file_path.open() as f:
                print(f"Loading config from {self.config_file_path}")
                self.config = tomlkit.parse(f.read())
        else:
            self.set_all_defaults()
            self.save()

        atexit.register(self.save)

    def get(self, heading, key, requested_type: Type):

        section = self.config.get(heading)
        if section is None or key not in section:
            return self.set_default(heading, key)

        val = None
        try:
            val = requested_type(section.get(key))  # type: ignore
            return val
        except TypeError as e:
            print(e)
            raise TypeError(
                f"Config value {key} in heading {heading} in {self.config_file_path} is not castable to correct \
                              type, Expected: {requested_type}, given: {type(val)}")

    def get_int(self, heading, key) -> int:
        return int(self.get(heading, key, int))  # type: ignore

    def get_str(self, heading, key) -> str:
        return str(self.get(heading, key, str))  # type: ignore

    def get_float(self, heading, key) -> float:
        return float(self.get(heading, key, float))  # type: ignore

    def get_bool(self, heading, key) -> bool:
        return bool(self.get(heading, key, bool))  # type: ignore

    def get_dict(self, heading, key) -> dict:
        return dict(self.get(heading, key, dict))  # type: ignore

    def get_list(self, heading, key, type: Type) -> list:
        return list(map(type, self.get(heading, key, list)))  # type: ignore

    def get_list_int(self, heading, key) -> list[int]:
        return list(self.get_list(heading, key, int))

    def get_list_float(self, heading, key) -> list[float]:
        return list(self.get_list(heading, key, float))

    def get_color(self, heading, key) -> tuple[int, int, int]:
        if len(self.get_list_int(heading, key)) != 3:
            raise ValueError(f"Color value {key} in heading {heading} in {self.config_file_path} is not a valid color")
        return tuple(self.get_list_int(heading, key))  # type: ignore

    def get_color_normalized(self, heading, key) -> tuple[float, float, float]:
        color = self.get_color(heading, key)
        return tuple([c / 255 for c in color])  # type: ignore

    def get_color_rgba(self, heading, key) -> tuple[float, float, float, float]:
        """Get an RGBA color value as a tuple of floats (0.0-1.0)"""
        color_list = self.get_list_float(heading, key)
        if len(color_list) != 4:
            raise ValueError(
                f"RGBA color value {key} in heading {heading} in {self.config_file_path} is not a valid RGBA color")
        return tuple(color_list)  # type: ignore

    def set_color_rgba(self, heading, key, color: tuple[float, float, float, float]):
        """Set an RGBA color value from a tuple of floats (0.0-1.0)"""
        if len(color) != 4:
            raise ValueError(f"RGBA color value {key} in heading {heading} must have 4 components")
        self.set(heading, key, list(color))

    def set_color_from_normalized(self, heading, key, color: tuple[float, float, float]):
        if len(color) != 3:
            raise ValueError(f"Color value {key} in heading {heading} in {self.config_file_path} is not a valid color")
        color = tuple([int(c * 255) for c in color])  # type: ignore
        self.set(heading, key, color)

    def set(self, heading, key, value):
        if heading not in self.config:
            self.config[heading] = tomlkit.table()
        self.config[heading][key] = value  # type: ignore
        # self.save()

    def set_default(self, heading, key):

        if heading not in self.config_defaults:
            raise KeyError(f"Config heading {heading} not found in defaults {self.config_defaults_path}")
        def_val = self.config_defaults[heading][key]  # type: ignore

        self.set(heading, key, def_val)  # type: ignore
        return def_val

    def set_all_defaults(self):
        self.config = self.config_defaults

    def save(self):
        print("Saving configuration to:", self.config_file_path)
        with self.config_file_path.open('w') as f:
            f.write(tomlkit.dumps(self.config))


if 'app_config' not in globals():

    global bundle_dir
    bundle_dir = Path()
    application_dir = Path()
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):  # Running as compiled
        bundle_dir = Path(sys._MEIPASS)  # type: ignore
        application_dir = Path(sys.executable).parent
    else:
        bundle_dir = Path(os.getcwd())
        application_dir = Path(os.getcwd())

    print(f"Bundle directory: {bundle_dir}")
    print(f"Application path: {application_dir}")
    global app_config
    app_config = RadarConfig(bundle_dir=bundle_dir, application_dir=application_dir)  # global config
