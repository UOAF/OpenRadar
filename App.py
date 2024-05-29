import pygame
import math

class App:
    def __init__(self):
        self._running = True
        self.size = self.width, self.height = 640, 400
        self._mouseDown = False
        self._startPan = (0,0)
 
    def on_init(self):
        pygame.init()
        self._display_surf = pygame.display.set_mode(self.size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        self._map = Map(self._display_surf)
        self._running = True
 
    def on_event(self, event):
        
        #TODO Consider refactor
        
        if event.type == pygame.QUIT:
            self._running = False
            
        elif event.type == pygame.VIDEORESIZE:
            self.size = self.width, self.height = event.w, event.h
            self._map.resize(self.width, self.height)
            
        elif event.type == pygame.MOUSEWHEEL:
            if event.y != 0:
                self._map.zoom(pygame.mouse.get_pos(), event.y)
                
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._startPan = event.pos
            self._mouseDown = True

        elif event.type == pygame.MOUSEMOTION:
            if self._mouseDown: # dragging
                difX = event.pos[0] - self._startPan[0]
                difY = event.pos[1] - self._startPan[1]
                self._map.pan((difX,difY)) 
                self._startPan = event.pos
                
        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouseDown = False
            
    def on_loop(self):
        pass
    
    def on_render(self):
        self._display_surf.fill((50,50,50)) # Fill grey
        self._map.on_render()
        pygame.display.flip()
    
    def on_cleanup(self):
        pygame.quit()
 
    def on_execute(self):
        if self.on_init() == False:
            self._running = False
 
        #TODO framerate limit
        while( self._running ):
            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
            
        self.on_cleanup()
        
class Map:
    def __init__(self, displaysurface: pygame.Surface):
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
        self._radar = Radar(displaysurface)
        
        self.font = pygame.font.SysFont('Comic Sans MS', 30)
        
    def on_render(self):
        self._display_surf.blit(self._image_surf,(self._offsetX,self._offsetY))
        self._radar.on_render()
        
        # pos = pygame.mouse.get_pos()
        # canvasPos = self._screen_to_canvas(pygame.mouse.get_pos())
        # text_surface = self.font.render(f"{pos}\n{canvasPos}", False, (0, 0, 0), (255, 255, 255))
        # self._display_surf.blit(text_surface, (self._offsetX,self._offsetY))
        
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

    def fitInView(self, scale=True):
        
        if self._map_source is not None:
            maprect = pygame.Rect((0,0), self._map_source.get_size())
            self._base_zoom = min(self.width / maprect.width, self.height / maprect.height)
            self._scale = self._base_zoom
            newSize = int(maprect.width * self._base_zoom), int(maprect.height * self._base_zoom)
            print(self._map_source.get_size())
            print(self.size)
            print(newSize)
            
            self._image_surf = pygame.transform.scale(self._map_source, newSize)
            print("resize", self._scale)
            
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
            
        print(self._zoom)
            
    def _canvas_to_screen(self, canvasCoords: tuple[float,float] = (0,0)) -> tuple[int,int]:
        screenX = int((canvasCoords[0] + self._offsetX) * self._scale)
        screenY = int((canvasCoords[1] + self._offsetY) * self._scale)
        return screenX, screenY
        
    def _screen_to_canvas(self, screenCoords: tuple[int,int] = (0,0)) -> tuple[float,float]:
        canvasX = float((screenCoords[0] - self._offsetX) / self._scale)
        canvasY = float((screenCoords[1] - self._offsetY) / self._scale)
        return  canvasX, canvasY
    
    def _canvas_to_world(self, canvasCoords: tuple[float,float] = (0,0)) -> tuple[float,float]:
        return (0,0)    
    
        # TODO port to pygame
        # radar_map_size_x, radar_map_size_y = self._map.boundingRect().width(), self._map.boundingRect().height()
        # theatre_size_km = 1024 # TODO move out
        # theater_max_meter = theatre_size_km * 1000 # km to m
        
        # pos_ux = float(properties["T"]["U"])
        # pos_vy = float(properties["T"]["V"])
        # scene_x = pos_ux / theater_max_meter * radar_map_size_x
        # scene_y = radar_map_size_y - pos_vy / theater_max_meter * radar_map_size_y
        
    def _world_to_canvas(self, worldCoords: tuple[float,float] = (0,0)) -> tuple[float,float]:
        return (0,0)

class Radar:
    def __init__(self, surface: pygame.Surface):
        self._display_surf = surface
        self._size = self.width, self.height = (18,18)
    
    def on_render(self):
        
        self.draw_contact(self._display_surf, (50,50,0), (0,0,255), 45, 1000)
    
    def draw_contact(self, surface: pygame.Surface, pos, color, heading, velocity):
        
        # Draw Square
        contactrect = pygame.Rect((pos[0]-self.width/2.0, 
                    pos[1]-self.height/2.0, 
                    self.width, 
                    self.height))
        pygame.draw.rect(surface, color, contactrect, 3)
        
        # Draw Velocity Line
        vector = self.getVelocityVector(pos, heading, velocity) # returns line starting at 0,0
        start_point = vector[0][0] + pos[0], vector[0][1] + pos[1] # offset to the location of the contact
        end_point = vector[1][0] + pos[0], vector[1][1] + pos[1] # offset to the location of the contact
        pygame.draw.line(surface, pygame.Color("white"), start_point, end_point, 2)

    def boundingRect(self, pos) -> tuple[float,float,float,float]:

        return (pos[0]-self.width/2.0, 
                pos[1]-self.height/2.0, 
                self.width, 
                self.height)
        
    def getVelocityVector(self, start_pos: tuple[float,float] = (0,0), heading = 0.0, velocity = 0.0
                          ) -> tuple[tuple[float,float],tuple[float,float]]:
        vel_scale = velocity / 1000.0
        vel_vec_len_px = self.height/16 + min(self.height/2.0, vel_scale*self.height/2.0) # todo scale for pygame

        start_pt = (0,0)

        heading_rad = math.radians(heading-90) # -90 rotaes north to up
        end_x = start_pt[0] + vel_vec_len_px*math.cos(heading_rad)
        end_y = start_pt[1] + vel_vec_len_px*math.sin(heading_rad)
        end_pt = (end_x, end_y)

        return (start_pt, end_pt)

if __name__ == "__main__" :
    theApp = App()
    theApp.on_execute()