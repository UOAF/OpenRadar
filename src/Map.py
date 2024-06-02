import pygame

class Map:
    def __init__(self, displaysurface: pygame.Surface):
        super().__init__()
        self._running = True
        self._display_surf = displaysurface
        self.size = self.width, self.height = 640, 400
        self._map_source = pygame.Surface(self.size)
        self.load_map("maps/balkans_4k_airbases.png")
        self._image_surf = pygame.Surface((0,0))
        self._zoom_levels = dict() #Cache for scaled map images #TODO use
        self._offsetX, self._offsetY = (0,0)
        self._base_zoom = 1
        self._zoom = 0
        self._scale = 1
        self.fitInView()
        # self._radar = Radar(self)
        
        self.font = pygame.font.SysFont('Comic Sans MS', 30)
        
    def on_render(self):
        self._display_surf.blit(self._image_surf,(self._offsetX,self._offsetY))
        # self._radar.on_render()
        
        # pos = pygame.mouse.get_pos()
        # canvasPos = self._screen_to_canvas(pygame.mouse.get_pos())
        # text_surface = self.font.render(f"{pos}\n{canvasPos}", False, (0, 0, 0), (255, 255, 255))
        # self._display_surf.blit(text_surface, (self._offsetX,self._offsetY))
        
    def on_loop(self):
        # self._radar.on_loop()
        pass
        
    def load_map(self, mappath):
        if mappath:
            self._map_source = pygame.image.load(mappath).convert()
        else:
            self._map_source = pygame.Surface(self.size)
            
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
        maxZoom = 14
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
        theatre_size_km = 1024 # TODO move out
        theater_max_meter = theatre_size_km * 1000 # km to m

        pos_ux = canvasCoords[0] / radar_map_size_x * theater_max_meter
        pos_vy = theater_max_meter - (canvasCoords[1] / radar_map_size_y * theater_max_meter)

        return pos_ux, pos_vy
        
    def _world_to_canvas(self, worldCoords: tuple[float,float] = (0,0)) -> tuple[float,float]:
        
        radar_map_size_x, radar_map_size_y = self._map_source.get_size()
        theatre_size_km = 1024 # TODO move out
        theater_max_meter = theatre_size_km * 1000 # km to m

        pos_ux = worldCoords[0] #float(properties["T"]["U"])
        pos_vy = worldCoords[1] #float(properties["T"]["V"])
        canvasX = pos_ux / theater_max_meter * radar_map_size_x
        canvasY = (theater_max_meter - pos_vy) / theater_max_meter * radar_map_size_y     
                
        return canvasX, canvasY

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