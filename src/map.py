import pygame
import math

import config

THEATRE_DEFAULT_SIZE = 1024
NM_TO_METERS = 1852
METERS_TO_FT = 3.28084

#TODO Move to config
THEATRE_MAPS_BUILTIN = [{"name": "Balkans", "path": "resources/maps/balkans_4k_airbases.png", "size": 1024},
                        {"name": "KTO", "path": "resources/maps/Korea.jpg", "size": 1024}]

class Map:
    def __init__(self, displaysurface: pygame.Surface):
        super().__init__()
        self._running = True
        self._display_surf = displaysurface
        self.size = self.width, self.height = displaysurface.get_size()
        self._map_source = pygame.Surface(self.size)
       
        active_theatre = config.app_config.get("map", "theatre", str)
        theatre = next((x for x in THEATRE_MAPS_BUILTIN if x["name"] == active_theatre), None)
        
        if theatre is not None:
            self.load_map(theatre["path"], config.app_config.get("map", "map_alpha", int)) # type: ignore
            self.theatre_size_km = theatre["size"]
        else:
            self.load_map(None)
            self.theatre_size_km = THEATRE_DEFAULT_SIZE
            
        self._image_surf = pygame.Surface((0,0))
        self._zoom_levels = dict() #Cache for scaled map images #TODO use if zoom needs optimization0
        self._offsetX, self._offsetY = (0,0)
        self._base_zoom = 1
        self._zoom = 0
        self._scale = 1
        self.theater_max_meter = self.theatre_size_km * 1000 # km to m
        self.fitInView()
        # self._radar = Radar(self)
        
        self.font = pygame.font.SysFont('Comic Sans MS', 10)
        
    def on_render(self):
        self._display_surf.blit(self._image_surf,(self._offsetX,self._offsetY))
        self._draw_scale()
        
    def on_loop(self):
        pass
        
    def load_map(self, mappath, alpha: int|None = 100):
        if mappath:
            self._map_source = pygame.image.load(mappath).convert()
        else:
            self._map_source = pygame.Surface(self.size)
            
        if alpha is not None:
            self._map_source.set_alpha(alpha)
            
    def pan(self, panVector: tuple[float,float] = (0,0) ):
        self._offsetX = (self._offsetX + panVector[0]) 
        self._offsetY = (self._offsetY + panVector[1]) 
        
        #TODO Pan limits
        
    def resize(self, width, height):
        self.size = self.width, self.height = width, height
        self.fitInView()
        # self._radar.resize(width, height)

    def fitInView(self, scale=True):
        
        if self._map_source is not None:
            maprect = pygame.Rect((0,0), self._map_source.get_size())
            self._base_zoom = min(self.width / maprect.width, self.height / maprect.height)
            self._scale = self._base_zoom
            newSize = int(maprect.width * self._base_zoom), int(maprect.height * self._base_zoom)
            
            self._image_surf = pygame.transform.scale(self._map_source, newSize)
            #Center
            self._offsetX, self._offsetY = ((self.size[0] - newSize[0]) / 2), ((self.size[1] - newSize[1]) / 2) 
                
        self._zoom = 0

    def zoom(self, mousepos, y: float):
        factor = 1.10
        maxZoom = 20
        if y > 0:
            self._zoom += 1
        else:
            self._zoom -= 1
            
        if self._zoom > maxZoom:
            self._zoom = maxZoom
        elif self._zoom > 0:
            
            sourceMapSize = self._map_source.get_size()
            oldcanvasmousepos = self._screen_to_canvas(mousepos)

            # Scale
            self._scale = (self._base_zoom * (factor ** self._zoom))
            newSize = (int(sourceMapSize[0] * self._scale), 
                      int(sourceMapSize[1] * self._scale))
            self._image_surf = pygame.transform.scale(self._map_source, newSize)
            
            # Pan to keep mouse in the same place
            newcanvasmousepos = self._screen_to_canvas(mousepos)
            
            self._offsetX = self._offsetX - (oldcanvasmousepos[0] - newcanvasmousepos[0]) * self._scale
            self._offsetY = self._offsetY - (oldcanvasmousepos[1] - newcanvasmousepos[1]) * self._scale
            
        elif self._zoom <= 0:
            self.fitInView()
        else:
            self._zoom = 0
            
    def _draw_scale(self):
        
        scale_height_px = 50
        padding = 10
        color = pygame.Color("white")
        graduations_nm = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        
        scale_width_px = int(self.width / 4) # 25% of width
        scale_width_m = (scale_width_px / self._scale) / self._map_source.get_width() * self.theater_max_meter
        scale_width_nm = scale_width_m / NM_TO_METERS
        possible_graduations = [i for i in graduations_nm if i < scale_width_nm]
        if len(possible_graduations) == 0:
            max_graduation_nm = 1
        else:
            max_graduation_nm = max(possible_graduations)
                
        max_graduation_m = max_graduation_nm * NM_TO_METERS
        max_graduation_px = (max_graduation_m / self.theater_max_meter) * self._map_source.get_width() * self._scale
        
        scale_rect = pygame.Rect(self.width - scale_width_px - padding, self.height - scale_height_px - padding, 
                                 scale_width_px, scale_height_px)
        
        # pygame.draw.rect(self._display_surf, color, scale_rect, 2)
        
        scale_left = (scale_rect.left + (scale_rect.width - max_graduation_px) / 2, 
                      scale_rect.top + scale_rect.height / 2)
        
        scale_right = (scale_left[0] + max_graduation_px, scale_left[1])
        
        #Horizontal line
        pygame.draw.line(self._display_surf, color, scale_left, 
                         (scale_left[0] + max_graduation_px, scale_left[1]), 2)
        
        #Graduations
        pygame.draw.line(self._display_surf, color, (scale_left[0], scale_left[1] - 10), 
                         (scale_left[0], scale_left[1] + 10), 2)
        
        pygame.draw.line(self._display_surf, color, (scale_right[0], scale_right[1] - 10), 
                    (scale_right[0], scale_right[1] + 10), 2)
        
        center = scale_rect.center
        
        pygame.draw.line(self._display_surf, color, (center[0], center[1] - 5), 
                         (center[0], center[1] + 5), 2)
        
        #text
        text = self.font.render(f"{max_graduation_nm} NM", True, color)
        text_rect = text.get_rect()
        
        
        self._display_surf.blit(text, (scale_left[0] ,scale_rect.top ))
        
        
        
            
    def _canvas_to_screen(self, canvasCoords: tuple[float,float] = (0,0)) -> tuple[int,int]:
        screenX = int((canvasCoords[0] * self._scale) + self._offsetX)
        screenY = int((canvasCoords[1] * self._scale) + self._offsetY)
        return screenX, screenY
        
    def _screen_to_canvas(self, screenCoords: tuple[int,int] = (0,0)) -> tuple[float,float]:
        canvasX = float((screenCoords[0] - self._offsetX) / self._scale)
        canvasY = float((screenCoords[1] - self._offsetY) / self._scale)
        return  canvasX, canvasY
    
    def _canvas_to_world(self, canvasCoords: tuple[float,float] = (0,0)) -> tuple[float,float]:
        radar_map_size_x, radar_map_size_y = self._map_source.get_size()

        pos_ux = canvasCoords[0] / radar_map_size_x * self.theater_max_meter
        pos_vy = self.theater_max_meter - (canvasCoords[1] / radar_map_size_y * self.theater_max_meter)

        return pos_ux, pos_vy
        
    def _world_to_canvas(self, worldCoords: tuple[float,float] = (0,0)) -> tuple[float,float]:
        
        radar_map_size_x, radar_map_size_y = self._map_source.get_size()

        pos_ux = worldCoords[0] #float(properties["T"]["U"])
        pos_vy = worldCoords[1] #float(properties["T"]["V"])
        canvasX = pos_ux / self.theater_max_meter * radar_map_size_x
        canvasY = (self.theater_max_meter - pos_vy) / self.theater_max_meter * radar_map_size_y     
                
        return canvasX, canvasY
    
    def _screen_to_world(self, screenCoords: tuple[int,int] = (0,0)) -> tuple[float,float]:
        return self._canvas_to_world(self._screen_to_canvas(screenCoords))
                                      
    def _world_to_screen(self, worldCoords: tuple[float,float] = (0,0)) -> tuple[int,int]:
        return self._canvas_to_screen(self._world_to_canvas(worldCoords))
    
    def _world_distance(self, worldCoords1: tuple[float,float], worldCoords2: tuple[float,float]) -> float:
        return math.sqrt((worldCoords2[0] - worldCoords1[0])**2 + (worldCoords2[1] - worldCoords1[1])**2) / NM_TO_METERS
    
    def _world_bearing(self, worldCoords1: tuple[float,float], worldCoords2: tuple[float,float]) -> float:
        return math.degrees(math.atan2(worldCoords1[0] - worldCoords2[0], worldCoords1[1] - worldCoords2[1])) + 180

if __name__ == "__main__" :
    
    pygame.init()
    _display_surf = pygame.display.set_mode((640,480), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
    
    map = Map(_display_surf)
    
    print("offsetX, offsetY ", map._offsetX, map._offsetY)
    print("map size ", map._image_surf.get_size())
    
    top_left = map._world_to_canvas((0,1024*1000))
    top_left_screen = map._canvas_to_screen(top_left)
    print(f"Top Left: {top_left} Screen: {top_left_screen}")
    
    top_right = map._world_to_canvas((1024*1000,1024*1000))
    top_right_screen = map._canvas_to_screen(top_right)
    print(f"Top Right: {top_right} Screen: {top_right_screen}")
    
    bottom_left = map._world_to_canvas((0,0))
    bottom_left_screen = map._canvas_to_screen(bottom_left)
    print(f"Bottom Left: {bottom_left} Screen: {bottom_left_screen}")
    
    bottom_right = map._world_to_canvas((1024*1000,0))
    bottom_right_screen = map._canvas_to_screen(bottom_right)
    print(f"Bottom Right: {bottom_right} Screen: {bottom_right_screen}")
    
    pygame.quit()