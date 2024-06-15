import pygame
import math
import numpy as np

from acmi_parse import ACMIObject
from game_state import GameState, HIDDEN_OBJECT_CLASSES
from map import Map, NM_TO_METERS, METERS_TO_FT
from pygame_utils import draw_dashed_line

RADAR_CONTACT_SIZE_PX = 12

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
        self.unitFont = pygame.font.SysFont('Comic Sans MS', 14)
        self.cursorFont = pygame.font.SysFont('Comic Sans MS', 12)
        self.bullseye_world = self._canvas_to_world((2000,2000)) #TODO   Dynamic bullseye
        self.hover_obj_id: str = ""
    
    def on_render(self):
        """
        Renders the radar display.
        """
        super().on_render()
        self._radar_surf.fill((0,0,0,0)) # Fill transparent
        
        for id in self._gamestate.objects:
            self._draw_contact(self._radar_surf, self._gamestate.objects[id])

        if self._drawBRAA:
            self._draw_BRAA(self._radar_surf, self._startBraa, self._endBraa)
        else:
            self._draw_cursor(self._radar_surf, pygame.mouse.get_pos())
            
        self._display_surf.blit(self._radar_surf, (0,0))
        
    def on_loop(self):
        """
        Updates the game state.
        """
        super().on_loop()
        self._gamestate.update_state()
        
        self.hover_obj_id = self.get_hover_object_id()
        
        
    def resize(self, width, height):
        """
        Resizes the radar display.

        Args:
            width (int): The new width of the display.
            height (int): The new height of the display.
        """
        super().resize(width, height)
        self._radar_surf = pygame.Surface(self._display_surf.get_size(), pygame.SRCALPHA)
        
    def _draw_bullseye(self, surface: pygame.Surface, color: tuple[int,int,int,int] = (50,50,50,100), 
                      size: int = 2) -> None:
        """
        Draws the bullseye on the radar display.

        Args:
            surface (pygame.Surface): The surface on which to draw the bullseye.
            bullseye (tuple[int,int]): The position of the bullseye.
            color (tuple[int,int,int], optional): The color of the bullseye. Defaults to (50,50,50).
            size (int, optional): The size of the bullseye in pixels. Defaults to 10.
        """
        BULLSEYE_NUM_RINGS = 8
        BULLSEYE_RING_SCALE = 20 # 20nm per ring
        px_width_20nm = self._world_to_screen((BULLSEYE_RING_SCALE*NM_TO_METERS,0))[0] - self._world_to_screen((0,0))[0]
        pos = self._world_to_screen(self.bullseye_world)
    
        for i in range(1,BULLSEYE_NUM_RINGS):
            pygame.draw.circle(surface, color, pos, px_width_20nm*i, size) # Draw 20nm circle
        
        # draw cross
        pygame.draw.line(surface, color, (pos[0]-px_width_20nm*BULLSEYE_NUM_RINGS, pos[1]), 
                         (pos[0]+px_width_20nm*BULLSEYE_NUM_RINGS, pos[1]), size)
        pygame.draw.line(surface, color, (pos[0], pos[1]-px_width_20nm*BULLSEYE_NUM_RINGS),
                         (pos[0], pos[1]+px_width_20nm*BULLSEYE_NUM_RINGS), size)

    def _draw_BRAA(self, surface: pygame.Surface, start: tuple[int,int], end: tuple[int,int], 
                  color: tuple[int,int,int] = (255,165,0), size: int = 2) -> None:
        """
        Draws a BRAA line between two points on the radar display.

        Args:
            surface (pygame.Surface): The surface on which to draw the line.
            start (tuple[int,int]): The starting point of the line.
            end (tuple[int,int]): The ending point of the line.
            color (tuple[int,int,int], optional): The color of the line. Defaults to (255,165,0).
            size (int, optional): The size of the line in pixels. Defaults to 10.
        """
        
        pygame.draw.line(surface, color, start, end, size)
        
        #Calculate distance and bearing
        start_world = self._screen_to_world(start)
        end_world = self._screen_to_world(end)
        distance_NM = self._world_distance(start_world, end_world)
        bearing = self._world_bearing(start_world, end_world)
                
        
        text_surface = self.cursorFont.render(f"{bearing:.0f}/{distance_NM:.0f}", True, color)
        textrect = pygame.Rect((0,0),text_surface.get_size())
        textrect.topleft = (end[0] + 10, end[1] + 10)
        surface.blit(text_surface, textrect)
        
    def _draw_cursor(self, surface: pygame.Surface, pos: tuple[int,int], color: tuple[int,int,int] = (255,165,0), 
                    size: int = 10) -> None:
        """
        Draws a cursor on the radar display that shows the current bullseye position.

        Args:
            pos (tuple[int,int]): The position of the cursor.
            color (tuple[int,int,int], optional): The color of the cursor. Defaults to (255,255,255).
            size (int, optional): The size of the cursor in pixels. Defaults to 10.
        """
        # pygame.draw.line(self._display_surf, color, pos, (pos[0]+size, pos[1]), 2)
        # pygame.draw.line(self._display_surf, color, pos, (pos[0], pos[1]+size), 2)
        
        polar = self.get_pos_world_bullseye_relative(self._screen_to_world(pos))
        
        text_surface = self.cursorFont.render(f"{polar[0]:.0f}, {polar[1]:.0f}", True, (255,0,0)) #TODO fix color
        textrect = pygame.Rect((0,0),text_surface.get_size())
        textrect.topleft = (pos[0] + 10, pos[1] + 10)
        surface.blit(text_surface, textrect)
    
    def _draw_contact(self, surface: pygame.Surface, contact: ACMIObject, 
                     color: tuple[int, int, int] | None = None, size: int = RADAR_CONTACT_SIZE_PX) -> None:
        """
        Draws a contact on the given surface.

        Args:
            surface (pygame.Surface): The surface on which to draw the contact.
            contact (ACMIObject): The contact object to be drawn.
            color (tuple[int, int, int], optional): The color of the contact. Defaults to None.
            size (int, optional): The size of the contact icon in pixels. Defaults to 20.
        """

        hover =  contact.object_id in self.hover_obj_id

        if color is None:
            color_obj = pygame.Color( contact.Color ) 
        else:
            color_obj = pygame.Color(color)

        if "FixedWing" in contact.Type:
            self._draw_aircraft(surface, contact, color_obj, size, hover)
        elif "Missile" in contact.Type:
            self._draw_missile(surface, contact, color_obj, size)
        elif any(clas in contact.Type for clas in HIDDEN_OBJECT_CLASSES):
            pass
        elif "Watercraft" in contact.Type:
            self._draw_ship(surface, contact, color_obj)
        elif "Ground" in contact.Type:
            self._draw_ground(surface, contact, color_obj, size)
        elif "Navaid+Static+Bullseye" in contact.Type or contact.object_id == "7fffffffffffffff": #TODO remove objid hack
            self._draw_bullseye(surface)
        else:
            self._draw_other(surface, contact, color_obj, size)
            print(f"Drawing Other {contact}")

    def _draw_aircraft(self, surface: pygame.Surface, contact: ACMIObject, 
                       color: pygame.Color, size: int = RADAR_CONTACT_SIZE_PX, hover=False) -> None:

        pos = self._world_to_screen((contact.T.U, contact.T.V))
        heading = float(contact.T.Heading)
        velocity = float(contact.CAS)

        # Draw Square
        contactrect = pygame.Rect((0,0,size,size))
        contactrect.center = pos
        pygame.draw.rect(surface, color, contactrect, 2)

        # Draw Info Box
        text_surface = self._make_aircraft_text_info(contact, color)
        textrect = pygame.Rect((0,0),text_surface.get_size())
        textrect.bottomright = int(contactrect.left-size/4), int(contactrect.top)
        
        surface.blit(text_surface, textrect)

        # Draw Name Line
        # Draw a line from the top left of the contact to the right side of the name
        pygame.draw.line(surface, pygame.Color("white"), contactrect.topleft, textrect.midright, 2)

        # Draw Velocity Line
        start_point, end_point = self.getVelocityVector(pos, heading, velocity) # returns line starting at 0,0
        pygame.draw.line(surface, color, start_point, end_point, 3)
        
        # draw dashed lock line to target
        if contact.LockedTarget is not None and contact.LockedTarget in self._gamestate.objects:
            target = self._gamestate.objects[contact.LockedTarget]
            target_pos = self._world_to_screen((target.T.U, target.T.V))
            # pygame.draw.line(surface, color, pos, target_pos, 2)
            draw_dashed_line(surface, color, pos, target_pos, 1, 6)
        elif contact.LockedTarget is not None:
            pass
            # print(f"Missile {contact.object_id} has invalid target {contact.LockedTarget}")
        if hover:
            pygame.draw.circle(surface, color, pos, size*2, 2)

    def _draw_missile(self, surface: pygame.Surface, contact: ACMIObject,
                      color: pygame.Color, size: int = RADAR_CONTACT_SIZE_PX) -> None:
        
        pos = self._world_to_screen((contact.T.U, contact.T.V))
        
        # Define missile shape around origin        
        missile_points = np.array([(0,-size), (-size/2, size/2), (size/2, size/2)])
        
        heading_rad = math.radians(contact.T.Heading)
        
        # # rotate shape around orgin towards heading
        transformation_mat = ((math.cos(heading_rad), math.sin(heading_rad)),
                              (-math.sin(heading_rad), math.cos(heading_rad)))
                
        # translate and rotate shape to contact position
        for i in range(len(missile_points)):
            rotated_point = np.matmul(missile_points[i], transformation_mat)
            missile_points[i] = np.add(rotated_point, pos)
        
        # draw shape at contact position
        for point in missile_points:
            pygame.draw.line(surface, color, pos, point, 2)
            # pygame.draw.polygon(surface, color, list(map(tuple, missile_points)), 2)
        
        # draw dotted lock line to target
        if contact.LockedTarget is not None and contact.LockedTarget in self._gamestate.objects:
            target = self._gamestate.objects[contact.LockedTarget]
            target_pos = self._world_to_screen((target.T.U, target.T.V))
            # pygame.draw.line(surface, color, pos, target_pos, 2)
            draw_dashed_line(surface, color, pos, target_pos, 1, 6)
        elif contact.LockedTarget is not None:
            pass
            # print(f"Missile {contact.object_id} has invalid target {contact.LockedTarget}")

    def _draw_ship(self, surface: pygame.Surface, contact: ACMIObject,
                   color: pygame.Color, size: int = 20) -> None:
        
        pos = self._world_to_screen((contact.T.U, contact.T.V))

        # Define ship shape around origin        
        half = size/2
        qtr = size/4
        ship_points = np.array([(-half,0), (-qtr,0), (-qtr,-qtr), (qtr,-qtr), (qtr,0), (half,0), 
                                (qtr, qtr), (-qtr, qtr)])

        # translate and rotate shape to contact position
        for i in range(len(ship_points)):
            ship_points[i] = np.add(ship_points[i], pos)

        pygame.draw.polygon(surface, color, list(map(tuple, ship_points)), 2)

    def _draw_ground(self, surface: pygame.Surface, contact: ACMIObject,
                     color: pygame.Color, size: int = RADAR_CONTACT_SIZE_PX) -> None:
        
        pos = self._world_to_screen((contact.T.U, contact.T.V))
            
        # Draw Circle
        pygame.draw.circle(surface, color, pos, size/2, 2)
    
    def _draw_other(self, surface: pygame.Surface, contact: ACMIObject,
                    color: pygame.Color, size: int = RADAR_CONTACT_SIZE_PX) -> None:
        
        pos = self._world_to_screen((contact.T.U, contact.T.V))
        heading = float(contact.T.Heading)
        velocity = float(contact.CAS)
            
        # Draw Circle
        pygame.draw.circle(surface, color, pos, size/2, 2)

    def _make_aircraft_text_info(self, contact: ACMIObject, color: pygame.Color) -> pygame.Surface:
        name_surface = self.unitFont.render(f"{contact.Name}", True, color)
        data_surface = self.unitFont.render(
            f"{int(self.meters_to_ft(contact.T.Altitude)/100)}  {int(int(contact.CAS)/10)}", True, color
            )
        textrect = (max(name_surface.get_size()[0], data_surface.get_size()[0]), 
                   name_surface.get_size()[1]+ data_surface.get_size()[1])
        surface = pygame.Surface(textrect, pygame.SRCALPHA)
        surface.fill((0,0,0,0))
        surface.blit(name_surface, (textrect[0]-name_surface.get_width() ,0))
        surface.blit(data_surface, (textrect[0]-data_surface.get_width(),name_surface.get_size()[1]))
        
        return surface
    
    def meters_to_ft(self, meters: float) -> int:
        return int(meters * METERS_TO_FT)    

    def getVelocityVector(self, start_pos: tuple[float,float] = (0,0), heading: float = 0.0, velocity: float = 0.0, 
                          size: int = RADAR_CONTACT_SIZE_PX*3) -> tuple[tuple[float,float],tuple[float,float]]:
        """
        Calculates the start and end points of a velocity vector line to draw.

        Args:
            start_pos (tuple[float,float], optional): The starting position of the vector. Defaults to (0,0).
            heading (float, optional): The heading of the vector. Defaults to 0.0.
            velocity (float, optional): The velocity of the vector. Defaults to 0.0.
            size (int, optional): The size of the contact icon in pixels. Defaults to 20.

        Returns:
            tuple[tuple[float,float],tuple[float,float]]: The start and end points of the velocity vector.
        """
        vel_scale = velocity / 1000.0
        vel_vec_len_px = RADAR_CONTACT_SIZE_PX/2 + vel_scale*size # Scale the velocity vector

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

    def get_pos_world_bullseye_relative(self, pos_world: tuple[float,float]) -> tuple[float,float]:
        """
        Gets the position relative to the bullseye in polar coordinates.

        Returns:
            tuple[float,float]: (Bearing, Distance) The position of the cursor relative to the bullseye.
        """        
        bearing = self._world_bearing(self.bullseye_world, pos_world)
        distance = self._world_distance(self.bullseye_world, pos_world)
        
        return bearing, distance
    
    def get_hover_object_id(self, hover_distance: int = RADAR_CONTACT_SIZE_PX) -> str:
        """
        Gets the object ID of the object that is being hovered over.
        
        Args:
            hover_distance (int): The distance in pixels to consider an object as being hovered over.
            
        Returns:
            str: The object ID of the object being hovered over.
        """
        pos = pygame.mouse.get_pos()
        closest = None
        closest_dist = float('inf')
        for id in self._gamestate.objects:
            obj = self._gamestate.objects[id]
            dist = math.dist(pos, self._world_to_screen((obj.T.U, obj.T.V)))
            if dist < closest_dist:
                closest = obj
                closest_dist = dist
        if closest is None or closest_dist > hover_distance:
            return ""
        return closest.object_id