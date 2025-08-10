from typing import Any, Iterable, Union
import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass
import math
from enum import Enum


def unit_vector(angle_rad: float) -> np.ndarray:
    """Returns a unit vector for the given angle in radians."""
    x = math.cos(angle_rad)
    y = math.sin(angle_rad)
    z = 0
    w = 1
    return np.array([x, y, z, w], dtype=np.float32)


def add_control_points_loop(points: list[Any] | np.ndarray) -> np.ndarray:
    """
    Add control points to the line to close the polygon into a loop
    :param line: The line to add control points to.
    :param endpoint: If the shape was generated with endpoint = true, the first point = last point and we handle 
                     control points differently
    :return: The line with control points added.
    """
    array_points = np.zeros((len(points) + 2, 4), dtype=np.float32)
    array_points[1:-1] = np.array(points, dtype=np.float32)

    # line[0] == line[-1] so our control points are line[1] and line[-2] to get the correct angle on the mitre
    # see the comment in polygon.py draw_instances for more details
    prior = points[-2]
    array_points[0] = prior

    after = points[1]
    array_points[-1] = after

    return array_points


def add_control_points_angle(points: NDArray[np.float32],
                             before: bool = True,
                             after: bool = True,
                             before_angle_deg: float | None = None,
                             after_angle_deg: float | None = None) -> NDArray[np.float32]:
    """
    Add control points to the line to control the angle of the line caps.

    :param points: The line to add control points to, NumPy array.
    :param before: Add a control point before the first point.
    :param after: Add a control point after the last point.
    :param before_angle: The angle of the control point before the first point. If None, the control point
                         will be at the same angle as the adjacent line segment. Leading to a tangent endcap.
    :param after_angle: The angle of the control point after the last point. If None, the control point
                        will be at the same angle as the adjacent line segment. Leading to a tangent endcap.
    :return: The line with control points added as a NumPy array of shape (N, 4).
    """
    # Validate shape
    if points.ndim != 2 or points.shape[1] != 4:
        raise ValueError("Input points must have shape (N, 4)")

    # Preallocate space
    num_points = len(points)
    total_points = num_points + int(before) + int(after)
    array_points = np.zeros((total_points, 4), dtype=np.float32)

    # Copy the original points into the allocated array
    start = 1 if before else 0
    array_points[start:start + num_points] = points

    # Add control point before the first point
    if before:
        if before_angle_deg is not None:
            angle_rad = np.deg2rad(before_angle_deg)
        else:
            # Compute tangent angle from the first segment
            delta = array_points[1] - array_points[2]
            angle_rad = np.arctan2(delta[1], delta[0])

        # Compute and insert prior control point
        array_points[0] = array_points[1] + unit_vector(angle_rad)
        array_points[0, 3] = 1

    # Add control point after the last point
    if after:
        if after_angle_deg is not None:
            angle_rad = np.deg2rad(after_angle_deg)
        else:
            # Compute tangent angle from the last segment
            delta = array_points[-2] - array_points[-3]
            angle_rad = np.arctan2(delta[1], delta[0])

        # Compute and insert after control point
        array_points[-1] = array_points[-2] + unit_vector(angle_rad)
        array_points[-1, 3] = 1

    return array_points


### Test code for drawing a circle
def get_circle_points(radius, num_points) -> np.ndarray:
    # Generate angles evenly spaced around the circle
    angles = np.linspace(0, 2 * np.pi, num_points + 1, endpoint=True)

    # Calculate x and y coordinates
    x = radius * np.cos(angles)
    y = radius * np.sin(angles)
    z = np.zeros(num_points + 1)
    w = np.ones(num_points + 1)

    # Combine into pairs of (x, y) points
    points = np.column_stack((x, y, z, w))

    return add_control_points_loop(points)


def get_square_points():
    points = np.array([[-1, -1, 0, 1], [-1, 1, 0, 1], [1, 1, 0, 1], [1, -1, 0, 1], [-1, -1, 0, 1]], dtype=np.float32)

    return add_control_points_loop(points)


def get_diamond_points():
    points = np.array([[0, -1, 0, 1], [-1, 0, 0, 1], [0, 1, 0, 1], [1, 0, 0, 1], [0, -1, 0, 1]], dtype=np.float32)

    return add_control_points_loop(points)


def get_semicircle_points(radius, num_points):
    # Generate angles evenly spaced around the circle
    angles = np.linspace(0, np.pi, num_points, endpoint=True, dtype=np.float32)

    # Calculate x and y coordinates
    x = radius * np.cos(angles, dtype=np.float32)
    y = radius * np.sin(angles, dtype=np.float32)
    z = np.zeros(num_points, dtype=np.float32)
    w = np.ones(num_points, dtype=np.float32)

    # Combine into pairs of (x, y) points
    points = np.column_stack((x, y, z, w))

    return add_control_points_angle(points, before_angle_deg=270, after_angle_deg=270)


def get_half_diamond_points():
    points = np.array([[-1, 0, 0, 1], [0, 1, 0, 1], [1, 0, 0, 1]], dtype=np.float32)
    return add_control_points_angle(points, before_angle_deg=270, after_angle_deg=270)


def get_top_box_points():
    points = np.array([[-1, 0, 0, 1], [-1, 1, 0, 1], [1, 1, 0, 1], [1, 0, 0, 1]], dtype=np.float32)
    return add_control_points_angle(points, before_angle_deg=270, after_angle_deg=270)


def get_ship_points():
    points = np.array([
        [-1, 0, 0, 1],
        [-0.5, 0, 0, 1],
        [-0.5, 0.5, 0, 1],
        [0.5, 0.5, 0, 1],
        [0.5, 0, 0, 1],
        [1, 0, 0, 1],
        [0.5, -0.5, 0, 1],
        [-0.5, -0.5, 0, 1],
        [-1, 0, 0, 1],
    ],
                      dtype=np.float32)
    return add_control_points_loop(points)


@dataclass
class Shape:
    idx: int
    str: str
    points: np.ndarray


class Shapes(Enum):
    CIRCLE = Shape(1, "Circle", get_circle_points(1, 100))
    SQUARE = Shape(2, "Square", get_square_points())
    SEMICIRCLE = Shape(3, "Semicircle", get_semicircle_points(1, 50))
    DIAMOND = Shape(4, "Diamond", get_diamond_points())
    HALF_DIAMOND = Shape(5, "Half Diamond", get_half_diamond_points())
    TOP_BOX = Shape(6, "Top Box", get_top_box_points())
    SHIP = Shape(7, "Ship", get_ship_points())

    @classmethod
    def from_idx(cls, idx):
        return next(s for s in cls if s.value.idx == idx)


# import matplotlib.pyplot as plt
# plt.scatter(SEMICIRCLE[:, 0], SEMICIRCLE[:, 1])
# plt.show()
