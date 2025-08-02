import math

THEATRE_DEFAULT_SIZE_KM = 1024
NM_TO_METERS = 1852
METERS_TO_FT = 3.28084
BMS_FT_PER_KM = 3279.98
BMS_FT_PER_M = BMS_FT_PER_KM / 1000
THEATRE_DEFAULT_SIZE_METERS = THEATRE_DEFAULT_SIZE_KM * 1000  # km to m
THEATRE_DEFAULT_SIZE_FT = THEATRE_DEFAULT_SIZE_KM * BMS_FT_PER_KM
M_PER_SEC_TO_KNOTS = 1.94384


def canvas_to_screen(canvasCoords: tuple[float, float], scale: float, offset: tuple[float, float]) -> tuple[int, int]:
    screenX = int((canvasCoords[0] * scale) + offset[0])
    screenY = int((canvasCoords[1] * scale) + offset[1])
    return screenX, screenY


def screen_to_canvas(screenCoords: tuple[int, int], scale: float, offset: tuple[float, float]) -> tuple[float, float]:
    canvasX = float((screenCoords[0] - offset[0]) / scale)
    canvasY = float((screenCoords[1] - offset[1]) / scale)
    return canvasX, canvasY


def canvas_to_world(canvasCoords: tuple[float, float],
                    canvas_size: tuple[float, float],
                    theatre_size_meters=THEATRE_DEFAULT_SIZE_METERS) -> tuple[float, float]:
    radar_map_size_x, radar_map_size_y = canvas_size

    pos_ux = canvasCoords[0] / radar_map_size_x * theatre_size_meters
    pos_vy = theatre_size_meters - (canvasCoords[1] / radar_map_size_y * theatre_size_meters)

    return pos_ux, pos_vy


def world_to_canvas(worldCoords: tuple[float, float],
                    canvas_size: tuple[float, float],
                    theatre_size_meters=THEATRE_DEFAULT_SIZE_METERS) -> tuple[float, float]:

    map_size_x, map_size_y = canvas_size

    pos_ux = worldCoords[0]  #float(properties["T"]["U"])
    pos_vy = worldCoords[1]  #float(properties["T"]["V"])
    canvasX = pos_ux / theatre_size_meters * map_size_x
    canvasY = (theatre_size_meters - pos_vy) / theatre_size_meters * map_size_y

    return canvasX, canvasY


def screen_to_world(screenCoords: tuple[int, int], canvas_size: tuple[float, float], scale: float,
                    offset: tuple[float, float]) -> tuple[float, float]:
    return canvas_to_world(screen_to_canvas(screenCoords, scale, offset), canvas_size)


def world_to_screen(worldCoords: tuple[float, float],
                    canvas_size: tuple[float, float],
                    scale: float = 1,
                    offset: tuple[float, float] = (0, 0)) -> tuple[int, int]:
    return canvas_to_screen(world_to_canvas(worldCoords, canvas_size), scale, offset)


def world_distance(worldCoords1: tuple[float, float], worldCoords2: tuple[float, float]) -> float:
    return math.sqrt((worldCoords2[0] - worldCoords1[0])**2 + (worldCoords2[1] - worldCoords1[1])**2) / NM_TO_METERS


def world_bearing(worldCoords1: tuple[float, float], worldCoords2: tuple[float, float]) -> float:
    return math.degrees(math.atan2(worldCoords1[0] - worldCoords2[0], worldCoords1[1] - worldCoords2[1])) + 180
