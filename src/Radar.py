from cgitb import text
import pygame
import math

from AcmiParse import ACMIObject
from GameState import GameState
from Map import Map

SHOWN_OBJECT_CLASSES = ("Aircraft")
HIDDEN_OBJECT_CLASSES = ("Static", "Vehicle")

class Radar(Map):
    """
    Represents a radar display.

    Args:
        displaysurface (pygame.Surface): The surface on which to display the radar.

    Attributes:
        _display_surf (pygame.Surface): The surface on which the radar is displayed.
        _radar_surf (pygame.Surface): The surface used for rendering the radar.
        _gamestate (GameState): The game state object.
        font (pygame.font.Font): The font used for rendering text on the radar.
    """
    def __init__(self, displaysurface: pygame.Surface):
        super().__init__(displaysurface)
        self._display_surf = displaysurface
        self._radar_surf = pygame.Surface(self._display_surf.get_size(), pygame.SRCALPHA)
        self._gamestate = GameState()
        self._drawBRAA = False
        self.unitFont = pygame.font.SysFont('Comic Sans MS', 18)
        self.cursorFont = pygame.font.SysFont('Comic Sans MS', 12)
    
    def on_render(self):
        """
        Renders the radar display.
        """
        super().on_render()
        self._radar_surf.fill((0,0,0,0)) # Fill transparent
        
        for id, contact in self._gamestate.objects.items():
            if not any(clas in contact.Type for clas in HIDDEN_OBJECT_CLASSES): # Skip hidden objects
                self.draw_contact(self._radar_surf, contact)

        if self._drawBRAA:
            # Draw BRAA Line
            pass
            # pygame.draw.line(self._display_surf, pygame.Color("orange"), self._startBraa, self._endBraa, 2)
        else:
            # Draw Cursor
            self.draw_cursor(self._radar_surf, pygame.mouse.get_pos())
            
        self._display_surf.blit(self._radar_surf, (0,0))
        
        
    def on_loop(self):
        """
        Updates the game state.
        """
        super().on_loop()
        self._gamestate.update_state()
        
    def resize(self, width, height):
        """
        Resizes the radar display.

        Args:
            width (int): The new width of the display.
            height (int): The new height of the display.
        """
        super().resize(width, height)
        self._radar_surf = pygame.Surface(self._display_surf.get_size(), pygame.SRCALPHA)
        
    def draw_cursor(self, surface: pygame.Surface, pos: tuple[int,int], color: tuple[int,int,int] = (255,165,0), size: int = 10) -> None:
        """
        Draws a cursor on the radar display that shows the current bullseye position.

        Args:
            pos (tuple[int,int]): The position of the cursor.
            color (tuple[int,int,int], optional): The color of the cursor. Defaults to (255,255,255).
            size (int, optional): The size of the cursor in pixels. Defaults to 10.
        """
        # pygame.draw.line(self._display_surf, color, pos, (pos[0]+size, pos[1]), 2)
        # pygame.draw.line(self._display_surf, color, pos, (pos[0], pos[1]+size), 2)
        print(f"Drawing cursor at {pos}")
        text_surface = self.cursorFont.render(f"test {pos}", True, (255,0,0)) #TODO fix color
        textrect = pygame.Rect((0,0),text_surface.get_size())
        textrect.topleft = (pos[0] + 10, pos[1] + 10)
        surface.blit(text_surface, textrect)
    
    def draw_contact(self, surface: pygame.Surface, contact: ACMIObject, 
                     color: tuple[int, int, int] | None = None, size: int = 20) -> None:
        """
        Draws a contact on the given surface.

        Args:
            surface (pygame.Surface): The surface on which to draw the contact.
            contact (ACMIObject): The contact object to be drawn.
            color (tuple[int, int, int], optional): The color of the contact. Defaults to None.
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
        text_surface = self.unitFont.render(f"{contact.Name}", True, color)
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
        """
        Calculates the start and end points of a velocity vector.

        Args:
            start_pos (tuple[float,float], optional): The starting position of the vector. Defaults to (0,0).
            heading (float, optional): The heading of the vector. Defaults to 0.0.
            velocity (float, optional): The velocity of the vector. Defaults to 0.0.
            size (int, optional): The size of the contact icon in pixels. Defaults to 20.

        Returns:
            tuple[tuple[float,float],tuple[float,float]]: The start and end points of the velocity vector.
        """
        vel_scale = velocity / 1000.0
        vel_vec_len_px = size + min(size/2.0, vel_scale*size/2.0) # Scale the velocity vector

        start_pt = start_pos

        heading_rad = math.radians(heading-90) # -90 rotaes north to up
        end_x = start_pt[0] + vel_vec_len_px*math.cos(heading_rad)
        end_y = start_pt[1] + vel_vec_len_px*math.sin(heading_rad)
        end_pt = (end_x, end_y)

        return (start_pt, end_pt)
    
    def braa(self, braaEnabled:bool, start: tuple[int,int] = (0,0), end: tuple[int,int]= (0,0)):
        """
        Enables rendering of BRAA line between two points, additionally sets the start and end points of the line.

        Args:
            braaEnabled (bool): Whether to enable the BRAA line.
            start (tuple[int,int]): The starting point of the BRAA line.
            end (tuple[int,int]): The ending point of the BRAA line.
        """
        if not braaEnabled:
            self._drawBRAA = False
        else:
            self._startBraa = start
            self._endBraa = end
            self._drawBRAA = True
