class Rect:
    
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        
    def __repr__(self):
        return f"Rect({self.x}, {self.y}, {self.w}, {self.h})"
    
    @property
    def top_left(self) -> tuple[int, int]:
        return self.x, self.y
    
    @top_left.setter
    def top_left(self, value: tuple[int, int]):
        self.x, self.y = value
        
    @property
    def top_right(self) -> tuple[int, int]:
        return self.x + self.w, self.y
    
    @top_right.setter
    def top_right(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w, value[1]
        
    @property
    def bottom_left(self) -> tuple[int, int]:
        return self.x, self.y + self.h
    
    @bottom_left.setter
    def bottom_left(self, value: tuple[int, int]):
        self.x, self.y = value[0], value[1] - self.h
        
    @property
    def bottom_right(self) -> tuple[int, int]:
        return self.x + self.w, self.y + self.h
    
    @bottom_right.setter
    def bottom_right(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w, value[1] - self.h
        
    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2
    
    @center.setter
    def center(self, value: tuple[int, int]):
        self.x, self.y = value[0] - self.w // 2, value[1] - self.h // 2
        