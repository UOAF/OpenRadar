class Rect:

    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __repr__(self):
        return f"Rect({self.x}, {self.y}, {self.w}, {self.h})"

    def scale(self, scale: float):
        self.w *= scale
        self.h *= scale

    def scale_center(self, scale: float):
        self.w *= scale
        self.h *= scale
        self.x -= (self.w - self.w / scale) / 2
        self.y -= (self.h - self.h / scale) / 2

    @property
    def top_left(self) -> tuple[int, int]:
        return self.x, self.y

    @top_left.setter
    def top_left(self, value: tuple[int, int]):
        self.x, self.y = value

    @property
    def top_center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y

    @top_center.setter
    def top_center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w // 2, value[1]

    @property
    def top_right(self) -> tuple[int, int]:
        return self.x + self.w, self.y

    @top_right.setter
    def top_right(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w, value[1]

    @property
    def left_center(self) -> tuple[int, int]:
        return self.x, self.y + self.h // 2

    @left_center.setter
    def left_center(self, value: tuple[int, int]):
        self.x, self.y = value[0], value[1] - self.h // 2

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    @center.setter
    def center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w // 2, value[1] - self.h // 2

    @property
    def right_center(self) -> tuple[int, int]:
        return self.x + self.w, self.y + self.h // 2

    @right_center.setter
    def right_center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w, value[1] - self.h // 2

    @property
    def bottom_left(self) -> tuple[int, int]:
        return self.x, self.y + self.h

    @bottom_left.setter
    def bottom_left(self, value: tuple[int, int]):
        self.x, self.y = value[0], value[1] - self.h

    @property
    def bottom_center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h

    @bottom_center.setter
    def bottom_center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w // 2, value[1] - self.h

    @property
    def bottom_right(self) -> tuple[int, int]:
        return self.x + self.w, self.y + self.h

    @bottom_right.setter
    def bottom_right(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w, value[1] - self.h


class RectInvY(Rect):

    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)

    @property
    def bottom_left(self) -> tuple[int, int]:
        return self.x, self.y

    @bottom_left.setter
    def bottom_left(self, value: tuple[int, int]):
        self.x, self.y = value

    @property
    def bottom_center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y

    @bottom_center.setter
    def bottom_center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w // 2, value[1]

    @property
    def bottom_right(self) -> tuple[int, int]:
        return self.x + self.w, self.y

    @bottom_right.setter
    def bottom_right(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w, value[1]

    @property
    def left_center(self) -> tuple[int, int]:
        return self.x, self.y + self.h // 2

    @left_center.setter
    def left_center(self, value: tuple[int, int]):
        self.x, self.y = value[0], value[1] - self.h // 2

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    @center.setter
    def center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w // 2, value[1] - self.h // 2

    @property
    def right_center(self) -> tuple[int, int]:
        return self.x + self.w, self.y + self.h // 2

    @right_center.setter
    def right_center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w, value[1] - self.h // 2

    @property
    def top_left(self) -> tuple[int, int]:
        return self.x, self.y + self.h

    @top_left.setter
    def top_left(self, value: tuple[int, int]):
        self.x, self.y = value[0], value[1] - self.h

    @property
    def top_center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h

    @top_center.setter
    def top_center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w // 2, value[1] - self.h

    @property
    def top_right(self) -> tuple[int, int]:
        return self.x + self.w, self.y + self.h

    @top_right.setter
    def top_right(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w, value[1] - self.h
