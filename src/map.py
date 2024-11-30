import pygame

from bms_ini import FalconBMSIni
from os_uils import open_file_dialog

import config

from bms_math import *

#TODO Move to config
THEATRE_MAPS_BUILTIN = [{"name": "Balkans", "path": "resources/maps/balkans_4k_airbases.png", "size": 1024},
                        {"name": "KTO", "path": "resources/maps/Korea.jpg", "size": 1024},
                        {"name": "Israel", "path": "resources/maps/Israel.jpg", "size": 1024},
                        {"name": "MidEast", "path": "resources/maps/MidEast128Map.png", "size": 1024},]

class Map:
    def __init__(self, displaysurface: pygame.Surface):
        super().__init__()
        self._running = True
        self._display_surf = displaysurface
        self.size = self.width, self.height = displaysurface.get_size()[0], displaysurface.get_size()[1] - 74 # 74 is the height of the UI panel #TODO parameterize this
        self._map_source = pygame.Surface(self.size)
        self._map_annotated = pygame.Surface(self.size)
        self._map_quick_scaled = pygame.Surface(self.size)
        
        self.offset = pygame.Vector2(0,0) # Coordinate for the top left corner of the zoomed map in the original map 
        self._zoom_level = 0
        self._scale_new = 1
        self.screen_offset = pygame.Vector2(0,0)
        
        self.ini_surface = pygame.Surface(self.size)
        self.map_alpha = int(config.app_config.get("map", "map_alpha", int)) # type: ignore
        self.background_color = tuple (config.app_config.get("map", "background_color", tuple[int,int,int])) # type: ignore    
        self.font = pygame.font.SysFont('Comic Sans MS', 10)     
        active_theatre = config.app_config.get("map", "theatre", str)
        theatre = next((x for x in THEATRE_MAPS_BUILTIN if x["name"] == active_theatre), None)

        self._base_zoom = 1
        self._zoom = 0
        self._scale_c2s = 1
        self.max_zoom_level = int(config.app_config.get("map", "max_zoom_level", int)) # type: ignore
        
        self.ini: FalconBMSIni | None = None
        self._load_ini()   
                     
        if theatre is not None:
            self.load_map(config.bundle_dir / theatre["path"], 
                          config.app_config.get("map", "map_alpha", int)) # type: ignore
            self.theatre_size_km = theatre["size"]
        else:
            self.load_map(None)
            self.theatre_size_km = THEATRE_DEFAULT_SIZE   
                 
        self.theater_max_meter = self.theatre_size_km * 1000 # km to m

        self.fitInView()
        
    def on_render(self):
        self._display_surf.fill(self.background_color) # Fill grey
        # self._display_surf.blit(self._map_scaled,(self._offsetX,self._offsetY))
        self._display_surf.blit(self.map_scaled, self.screen_offset)
        self._draw_scale()
        
    def on_cleanup(self):
        pass
    
    def handle_load_map(self, event):
        map_file = open_file_dialog()
        print(f"Loading map file {map_file}")
        if map_file:
            self.load_map(map_file)
    
    def handle_load_ini(self, event):
        ini_file = open_file_dialog()
        print(f"Loading ini file {ini_file}")
        if ini_file:
            self._load_ini(ini_file)

    def _load_ini(self, ini_file=None):
        
        if ini_file is None: 
            self.ini = None
            self.ini_surface = None

        else:
            self.ini = FalconBMSIni(ini_file)
            self.ini_surface = self.ini.get_surf(self._map_source.get_size())
            self.prerender_map()     
        
    def prerender_map(self):
        """Prepares the map surface by loading the map image, precalculaing the alpha with a blit and
        """
        
        self._map_annotated = pygame.Surface(self._map_source.get_size())
        if self.map_alpha is not None: self._map_source.set_alpha(self.map_alpha)
        self._map_annotated.fill(self.background_color)
        self._map_annotated.blit(self._map_source, (0,0))
        if self.ini is not None and self.ini_surface is not None:
            self.ini_surface = self.ini.get_surf(self._map_source.get_size())
            self._map_annotated.blit(self.ini_surface, (0,0))        
        self._map_annotated.convert()
        # self._scale_map() #TODO: remove this and replace with new
    
    def on_loop(self):
        pass
        
    def load_map(self, mappath, alpha: int|None = 100):
        """
        Loads a map image from the given file path and sets it as the map source.
        Args:
            mappath (str): The file path of the map image.
            alpha (int|None, optional): The alpha value for the map image. Defaults to 100.
        Returns:
            None
        """
        if mappath:
            self._map_source = pygame.image.load(mappath).convert()
            if alpha is not None: self.map_alpha = alpha
        else:
            self._map_source = pygame.Surface(self.size)
        self.prerender_map()
            
    def pan(self, panVector: tuple[float,float] = (0,0) ):

        self.offset += pygame.Vector2(panVector)
        
        # Pan Limits
        pan_border = 100 # TODO configure
        screen_size = pygame.Vector2(self.size)
        map_size = pygame.Vector2(self._map_annotated.get_size()) * self._scale_c2s
        
        x_left = -map_size.x + pan_border
        x_right = screen_size.x - pan_border
        y_top = -map_size.y + pan_border
        y_bottom = screen_size.y - pan_border
        
        self.offset.x = pygame.math.clamp(self.offset.x, x_left, x_right)
        self.offset.y = pygame.math.clamp(self.offset.y, y_top,  y_bottom)
        
        self.map_transform(self._scale_c2s, self.offset)
        
    def resize(self, width, height):
        self.size = self.width, self.height = width, height - 74 # 74 is the height of the UI panel #TODO parameterize this
        self.fitInView()      
        
    def fitInView(self):
        
        if self._map_annotated is not None:
            screen_rect = pygame.Rect((0,0), self.size)
            map_rect = pygame.Rect((0,0), self._map_annotated.get_size())
            self._base_zoom = min(screen_rect.width / map_rect.width, screen_rect.height / map_rect.height) # Assumes map is square
            self._scale_c2s = self._base_zoom
            fit_size = pygame.Vector2(int(map_rect.width * self._base_zoom), 
                                    int(map_rect.height * self._base_zoom))
            self.offset = pygame.Vector2((screen_rect.width - fit_size.x) // 2, (screen_rect.height - fit_size.y) // 2)

            self.map_transform(self._scale_c2s, self.offset)
            
    def map_transform(self, scale_m2s: float, pos: pygame.Vector2):
        scale_s2m = 1.0 / scale_m2s
                
        screen_rect = pygame.Rect((0,0), self.size)
        map_rect = pygame.Rect((0,0), self._map_annotated.get_size())
        
        source_rect = pygame.Rect(-pos * scale_s2m, pygame.Vector2(screen_rect.size) * scale_s2m) 
        source_rect_clipped = source_rect.clip(map_rect)
        source_rect_clipped_offset = (-pygame.Vector2(source_rect.topleft) + pygame.Vector2(source_rect_clipped.topleft)) * scale_m2s
        
        # we need to set the position equal to the _complement_ of what would be clipped
        dest_rect = source_rect_clipped.scale_by(scale_m2s).move_to(topleft=source_rect_clipped_offset)
        dest_rect_clipped = dest_rect      
        
        if dest_rect_clipped.width < 1 or dest_rect_clipped.height < 1:
            return
        
        self.screen_offset = pygame.Vector2(dest_rect_clipped.topleft)
        map_clipped = self._map_annotated.subsurface(source_rect_clipped)
        self.map_scaled = pygame.transform.smoothscale(map_clipped, dest_rect_clipped.size)      
        
        
    def zoom(self, mousepos, y: float):
        factor = 1.10
        delta_zoom = 1 if y > 0 else -1
        self._zoom_level += delta_zoom
        
        self._zoom_level = min(self._zoom_level, self.max_zoom_level)
        self._zoom_level = max(self._zoom_level, 0)
        if self._zoom_level > self.max_zoom_level:
            self._zoom_level = self.max_zoom_level
        elif self._zoom_level > 0:

            oldscale = self._scale_c2s
            
            # Scale
            self._scale_c2s = (self._base_zoom * (factor ** self._zoom_level))
            
            newscale = self._scale_c2s
            
            oldmouspos = pygame.Vector2(screen_to_canvas(mousepos, oldscale, (self.offset.x, self.offset.y)))
            newmousepos = pygame.Vector2(screen_to_canvas(mousepos, newscale, (self.offset.x, self.offset.y)))
            
            mouse_delta_canvas = newmousepos - oldmouspos
            mouse_delta_screen = mouse_delta_canvas * self._scale_c2s
            self.offset += mouse_delta_screen
            
            self.map_transform(self._scale_c2s, self.offset)
                       
            
        elif self._zoom_level <= 0:
            self.fitInView()
            self._zoom_level = 0
        else:
            self._zoom_level = 0
        
    def _draw_scale(self):
        
        bottom_extra_padding = 0 # move this up above the UI buttons TODO: move this into the UI to make it less messy
        scale_height_px = 50
        padding = 10
        color = pygame.Color("white")
        graduations_nm = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        
        scale_width_px = int(self.width / 4) # 25% of width
        scale_width_m = (scale_width_px / self._scale_c2s) / self._map_annotated.get_width() * self.theater_max_meter
        scale_width_nm = scale_width_m / NM_TO_METERS
        possible_graduations = [i for i in graduations_nm if i < scale_width_nm]
        if len(possible_graduations) == 0:
            max_graduation_nm = 1
        else:
            max_graduation_nm = max(possible_graduations)
                
        max_graduation_m = max_graduation_nm * NM_TO_METERS
        max_graduation_px = (max_graduation_m / self.theater_max_meter) * self._map_annotated.get_width() * self._scale_c2s
        
        scale_rect = pygame.Rect(0, 0, scale_width_px, scale_height_px)
        
        scale_rect.bottomright = (self.width - padding, self.height - padding - bottom_extra_padding)
        
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
        
        
    def _px_per_nm(self) -> float:
        """
        Calculates the number of pixels per nautical mile.

        Returns:
            float: The number of pixels per nautical mile.
        """
        return NM_TO_METERS * self._px_per_m()
    
    def _px_per_m(self) -> float:
        """
        Calculates the number of pixels per meter.

        Returns:
            float: The number of pixels per meter.
        """
        return self._map_annotated.get_width() / self.theater_max_meter * self._scale_c2s
        
    def _canvas_to_screen(self, canvasCoords: tuple[float,float] = (0,0)) -> tuple[int,int]:
        return canvas_to_screen(canvasCoords, self._scale_c2s, (self.offset.x, self.offset.y))
        
    def _screen_to_canvas(self, screenCoords: tuple[int,int] = (0,0)) -> tuple[float,float]:
        return screen_to_canvas(screenCoords, self._scale_c2s, (self.offset.x, self.offset.y))
    
    def _canvas_to_world(self, canvasCoords: tuple[float,float] = (0,0)) -> tuple[float,float]:
        return canvas_to_world(canvasCoords, self._map_source.get_size())
    
    def _world_to_canvas(self, worldCoords: tuple[float,float] = (0,0)) -> tuple[float,float]:
        return world_to_canvas(worldCoords, self._map_source.get_size())
    
    def _screen_to_world(self, screenCoords: tuple[int,int]) -> tuple[float,float]:
        return screen_to_world(screenCoords, self._map_source.get_size(), self._scale_c2s, (self.offset.x, self.offset.y))
                                      
    def _world_to_screen(self, worldCoords: tuple[float,float] = (0,0)) -> tuple[int,int]:
        return world_to_screen(worldCoords, self._map_source.get_size(), self._scale_c2s, (self.offset.x, self.offset.y))
    
    def _world_distance(self, worldCoords1: tuple[float,float], worldCoords2: tuple[float,float]) -> float:
        return world_distance(worldCoords1, worldCoords2)
    
    def _world_bearing(self, worldCoords1: tuple[float,float], worldCoords2: tuple[float,float]) -> float:
        return world_bearing(worldCoords1, worldCoords2)

if __name__ == "__main__" :
    
    pygame.init()
    _display_surf = pygame.display.set_mode((640,480), pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
    
    map = Map(_display_surf)
    
    print("offsetX, offsetY ", map.offset.x, map.offset.y)

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