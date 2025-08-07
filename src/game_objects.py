# import pygame

import numpy as np

import config

from util.bms_math import *
from typing import Callable, Any
from acmi_parse import ACMIObject


class GameCoalition:
    pass


class GameObject:

    hide_class = True

    def __init__(self, object: ACMIObject, color: tuple[float, float, float, float] = (255, 0, 255, 255)):
        self.data: ACMIObject = object
        self.color = color
        self.visible = True
        self.locked_target: GameObject | None = None
        self.override_name: str | None = None
        self.override_color: tuple[float, float, float, float] | None = None

    def get_display_name(self) -> str:

        if self.override_name is not None and self.override_name != "":
            return f"{self.override_name}"

        elif self.data.Pilot != "":
            return f"{self.data.Pilot}"

        return f"{self.data.Type}"

    def update(self, object: ACMIObject):
        self.data.update(object.properties, object.timestamp)

    def get_pos(self) -> tuple[float, float]:
        return (self.data.T.U, self.data.T.V)

    def set_color(self, color: tuple[float, float, float, float]):
        self.color = color

    def get_color(self) -> tuple[float, float, float, float]:
        return self.color

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def get_context_items(self) -> list[tuple[str, Callable[[Any], None]]]:
        return [("Change Color", self.change_color), ("Change Name", self.change_name)]

    def change_color(self, color: tuple[float, float, float, float]):
        pass

    def change_name(self, name: str):
        self.override_name = name


class Bullseye(GameObject):

    BULLSEYE_NUM_RINGS = 8
    BULLSEYE_RING_NM = 20  # 20nm per ring
    hide_class = False

    def __init__(self, object: ACMIObject, color: tuple[float, float, float, float] = (50, 50, 50, 100)):
        super().__init__(object, color)
        self.override_color = (50, 50, 50, 100)


class groundUnit(GameObject):

    hide_class = True

    def __init__(self, object: ACMIObject, color: tuple[float, float, float, float] = (255, 255, 255, 255)):
        super().__init__(object, color)


class airUnit(GameObject):

    hide_class = False

    def __init__(self, object: ACMIObject, color: tuple[float, float, float, float] = (255, 255, 255, 255)):
        super().__init__(object, color)
        self.locked_target: GameObject | None = None

    def _getVelocityVector(self,
                           px_per_nm: float,
                           heading: float | None = None,
                           line_scale: int = 3) -> tuple[float, float]:
        """
        Calculates the end point of a velocity vector line to draw.

        Args:
        heading (float): The heading angle in degrees.
        line_scale (int): The scale factor for the velocity vector line. Default is 3.

        Returns:
            tuple[float,float]: The end point of the velocity vector.
        """
        LINE_LEN_SECONDS = 30  # 30 seconds of velocity vector
        px_per_second = px_per_nm * self.data.CAS / NM_TO_METERS  # Scale the velocity vector
        vel_vec_len_px = px_per_second * LINE_LEN_SECONDS  # Scale the velocity vector

        heading_rad = math.radians(self.data.T.Heading - 90)  # -90 rotaes north to up
        end_x = vel_vec_len_px * math.cos(heading_rad)
        end_y = vel_vec_len_px * math.sin(heading_rad)
        end_pt = (end_x, end_y)

        return end_pt


class missile(airUnit):

    hide_class = False

    def __init__(self, object: ACMIObject, color: tuple[float, float, float, float] = (255, 255, 255, 255)):
        super().__init__(object, color)


class fixedWing(airUnit):

    def __init__(self, object: ACMIObject, color: tuple[float, float, float, float] = (255, 255, 255, 255)):
        super().__init__(object, color)


class rotaryWing(airUnit):

    def __init__(self, object: ACMIObject, color: tuple[float, float, float, float] = (255, 255, 255, 255)):
        super().__init__(object, color)


class surfaceVessel(groundUnit):

    hide_class = False

    def __init__(self, object: ACMIObject, color: tuple[float, float, float, float] = (255, 255, 255, 255)):
        super().__init__(object, color)
