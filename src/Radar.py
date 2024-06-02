import pygame
import math

from AcmiParse import ACMIObject
from GameState import GameState
from Map import Map

SHOWN_OBJECT_CLASSES = ("Aircraft")
HIDDEN_OBJECT_CLASSES = ("Static", "Vehicle")

class Radar(Map):
    def __init__(self, displaysurface: pygame.Surface):
        super().__init__(displaysurface)
        self._display_surf = displaysurface
        self._radar_surf = pygame.Surface(self._display_surf.get_size(), pygame.SRCALPHA)
        self._gamestate = GameState()
        self.font = pygame.font.SysFont('Comic Sans MS', 18)
    
    def on_render(self):
        super().on_render()
        self._radar_surf.fill((0,0,0,0)) # Fill transparent
        
        for id, contact in self._gamestate.objects.items():
            if not any(clas in contact.Type for clas in HIDDEN_OBJECT_CLASSES): # Skip hidden objects
                self.draw_contact(self._radar_surf, contact)

        self._display_surf.blit(self._radar_surf, (0,0))
        # self.draw_contact(self._display_surf, (50,50,0), (0,0,255), 45, 1000)
        
    def on_loop(self):
        super().on_loop()
        self._gamestate.update_state()
        
    def resize(self, width, height):
        super().resize(width, height)
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
        
        pos = self._canvas_to_screen(self._world_to_canvas((contact.T["U"], contact.T["V"])))
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
