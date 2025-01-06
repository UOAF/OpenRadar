import numpy as np


def close_polygon(points: np.ndarray) -> np.ndarray:
    """
    Close a polygon by repeating the first point at the end and the last point at the beginning twice
    the shader needs these twice to calculate the angle of the end of the last line segment
    """
    first_pt = points[1]
    last_pt = points[-2]
    points = np.append(points, [first_pt], axis=0)
    points = np.insert(points, 0, [last_pt], axis=0)

    return points

def open_polygon(points: np.ndarray) -> np.ndarray:
    
    first_pt = points[0]
    last_pt = points[-1]
    points = np.insert(points, 0, [first_pt], axis=0)
    points = np.append(points, [last_pt], axis=0)

    return points

### Test code for drawing a circle
def get_circle_points(radius, num_points):
    # Generate angles evenly spaced around the circle
    angles = np.linspace(0, 2 * np.pi, num_points+1, endpoint=True)
    
    # Calculate x and y coordinates
    x = radius * np.cos(angles)
    y = radius * np.sin(angles)
    z = np.zeros(num_points+1)
    w = np.ones(num_points+1)
    
    # Combine into pairs of (x, y) points
    points = np.column_stack((x, y, z, w))

    return close_polygon(points)

def get_square_points():
    points = np.array([
        [-1, -1, 0, 1],
        [-1, 1, 0, 1],
        [1, 1, 0, 1],
        [1, -1, 0, 1]
    ], dtype=np.float32)

    return close_polygon(points)

def get_diamond_points():
    points = np.array([
        [0, -1, 0, 1],
        [-1, 0, 0, 1],
        [0, 1, 0, 1],
        [1, 0, 0, 1]
    ], dtype=np.float32)

    return close_polygon(points)

def get_semicircle_points(radius, num_points):
    # Generate angles evenly spaced around the circle
    angles = np.linspace(0, np.pi, num_points, endpoint=True)
    
    # Calculate x and y coordinates
    x = radius * np.cos(angles)
    y = radius * np.sin(angles)
    z = np.zeros(num_points)
    w = np.ones(num_points)
    
    # Combine into pairs of (x, y) points
    points = np.column_stack((x, y, z, w))

    return open_polygon(points)


circle = get_circle_points(1, 100)
square = get_square_points()
semicircle = get_semicircle_points(1, 50)
diamond = get_diamond_points()
