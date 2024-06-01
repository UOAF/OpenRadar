from cgitb import text
from pydoc import doc
from turtle import heading
import pygame
import math

class App:
    def __init__(self, *args, **kwargs):
        self._running = True
        self.size = self.width, self.height = 640, 400
        self._mouseDown = False
        self._startPan = (0,0)

 
    def on_init(self):
        pygame.init()
        self._display_surf = pygame.display.set_mode(self.size, pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.RESIZABLE)
        self._map = Map(self._display_surf)
       
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18) 
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
        self._map.on_loop()
        pass
    
    def on_render(self):
        self._display_surf.fill((50,50,50)) # Fill grey
        self._map.on_render()
        self.fps_counter()
          
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
            self.clock.tick()
            
        self.on_cleanup()
        
    def fps_counter(self):
        fps = str(int(self.clock.get_fps()))
        fps_t = self.font.render(fps , 1, pygame.Color("RED"))
        self._display_surf.blit(fps_t,(0,0))
        
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
        self._radar = Radar(self)
        
        self.font = pygame.font.SysFont('Comic Sans MS', 30)
        
    def on_render(self):
        self._display_surf.blit(self._image_surf,(self._offsetX,self._offsetY))
        self._radar.on_render()
        
        # pos = pygame.mouse.get_pos()
        # canvasPos = self._screen_to_canvas(pygame.mouse.get_pos())
        # text_surface = self.font.render(f"{pos}\n{canvasPos}", False, (0, 0, 0), (255, 255, 255))
        # self._display_surf.blit(text_surface, (self._offsetX,self._offsetY))
        
    def on_loop(self):
        self._radar.on_loop()
        
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
        self._radar.resize(width, height)
        self.fitInView()

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


from AcmiParse import ACMIObject

class Radar:
    def __init__(self, map: Map):
        self._display_surf = map._display_surf
        self._radar_surf = pygame.Surface(self._display_surf.get_size(), pygame.SRCALPHA)
        self._gamestate = GameState()
        self._map = map
        self.font = pygame.font.SysFont('Comic Sans MS', 18)
    
    def on_render(self):
        
        self._radar_surf.fill((0,0,0,0)) # Fill transparent
        
        for id, contact in self._gamestate.objects.items():
            if not any(clas in contact.Type for clas in HIDDEN_OBJECT_CLASSES): # Skip hidden objects
                self.draw_contact(self._radar_surf, contact)

        self._display_surf.blit(self._radar_surf, (0,0))
        # self.draw_contact(self._display_surf, (50,50,0), (0,0,255), 45, 1000)
        
        
    def on_loop(self):
        self._gamestate.update_state()
        
    def resize(self, width, height):
        self._radar_surf = pygame.Surface(self._display_surf.get_size(), pygame.SRCALPHA)
    
    def draw_contact(self, surface: pygame.Surface, contact: ACMIObject, 
                     color: tuple[int, int, int] | None = None, size: int = 20) -> None:
        """
        Draws a contact on the given surface.

        Args:
            surface (pygame.Surface): The surface on which to draw the contact.
            pos (tuple[int, int]): The center position of the icon to be drawn representing the contacts location.
            color (tuple[int, int, int]): The color of the contact.
            heading (float): The heading of the contact.
            velocity (float): The velocity of the contact.
            size (int, optional): The size of the contact icon in pixels. Defaults to 20.
        """
        
        pos = self._map._canvas_to_screen(self._map._world_to_canvas((contact.T["U"], contact.T["V"])))
        heading = float(contact.T["Heading"])
        velocity = float(contact.CAS)
        color = (0,0,255)
        
        # Draw Square
        contactrect = pygame.Rect((0,0,size,size))
        contactrect.center = pos
        pygame.draw.rect(surface, pygame.Color("blue"), contactrect, 3)
        
        # Draw Name
        text_surface = self.font.render(f"{contact.Name}", True, color)
        textrect = pygame.Rect((0,0),text_surface.get_size())
        textrect.bottomright = int(contactrect.left-size/4), int(contactrect.top)
        
        surface.blit(text_surface, textrect)
        
        # Draw Name Line
        # Draw a line from the top left of the contact to the right side of the name
        pygame.draw.line(surface, pygame.Color("white"), contactrect.topleft, textrect.midright, 2)

        # Draw Velocity Line
        start_point, end_point = self.getVelocityVector(pos, heading, velocity) # returns line starting at 0,0
        pygame.draw.line(surface, pygame.Color("blue"), start_point, end_point, 3)
        
    def getVelocityVector(self, start_pos: tuple[float,float] = (0,0), heading: float = 0.0, velocity: float = 0.0, 
                          size: int = 20) -> tuple[tuple[float,float],tuple[float,float]]:
        vel_scale = velocity / 1000.0
        vel_vec_len_px = size + min(size/2.0, vel_scale*size/2.0) # Scale the velocity vector

        start_pt = start_pos

        heading_rad = math.radians(heading-90) # -90 rotaes north to up
        end_x = start_pt[0] + vel_vec_len_px*math.cos(heading_rad)
        end_y = start_pt[1] + vel_vec_len_px*math.sin(heading_rad)
        end_pt = (end_x, end_y)

        return (start_pt, end_pt)

import AcmiParse
from TRTTClient import TRTTClientThread
import queue 
SHOWN_OBJECT_CLASSES = ("Aircraft")
HIDDEN_OBJECT_CLASSES = ("Static", "Vehicle")

class GameState:
    """
    Represents the state of the game.

    Attributes:
        objects (list[AcmiParse.ACMIObject]): List of ACMI objects in the game.
        data_queue (queue.Queue): Queue to store incoming data from the Tacview client.
        global_vars (dict): Dictionary to store global variables.
        parser (AcmiParse.ACMIFileParser): ACMI parser to parse incoming data.
    """

    def __init__(self):
        self.objects: dict["str", AcmiParse.ACMIObject] = dict()
        self.data_queue = queue.Queue()
        self.global_vars = dict()
        
        # Create the ACMI parser
        self.parser = AcmiParse.ACMIFileParser()
        
        # Create the Tacview RT Relemetry client
        tac_client = TRTTClientThread(self.data_queue)
        tac_client.start()
        
    def update_state(self):
        """
        Update the game state with the latest data from the Tacview client.
        """
        print(len(self.objects))
        
        while not self.data_queue.empty():
            
            line = self.data_queue.get()
            if line is None: break # End of data
            
            acmiline = self.parser.parse_line(line) # Parse the line into a dict
            if acmiline is None: continue # Skip if line fails to parse

            if acmiline.action in AcmiParse.ACTION_REMOVE:
                # Remove object from battlefield
                self._remove_object(acmiline.object_id)
                # print(f"tried to delete object {acmiline.object_id} not in self.state")
            
            elif acmiline.action in AcmiParse.ACTION_TIME:
                pass
            
            elif acmiline.action in AcmiParse.ACTION_GLOBAL and isinstance(acmiline, AcmiParse.ACMIObject):
                self.global_vars = self.global_vars | acmiline.properties
            
            elif acmiline.action in AcmiParse.ACTION_UPDATE and isinstance(acmiline, AcmiParse.ACMIObject):
                self._update_object(acmiline)
            
            else:
                print(f"Unknown action {acmiline.action} in {acmiline}")

    def _remove_object(self, object_id: str) -> None:
        """
        Remove an object from the game state.

        Args:
            object_id (str): The ID of the object to remove.
        """
        # self.objects = [obj for obj in self.objects.ite if obj.object_id != object_id]
        if object_id in self.objects:
            del self.objects[object_id]
        else:
            print(f"tried to delete object {object_id} not in self.objects")

    def _update_object(self, updateObj: AcmiParse.ACMIObject) -> None:
        """
        Update an object in the game state.

        Args:
            updateObj (AcmiParse.ACMIObject): The Object with the new data to update.
        """
        if updateObj.object_id not in self.objects:
            self.objects[updateObj.object_id] = updateObj
        else:
            self.objects[updateObj.object_id].update(updateObj.properties)
            
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