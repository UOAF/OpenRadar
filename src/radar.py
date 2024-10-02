import pygame
import math

import pygame_gui

from game_state import GameState, CLASS_MAP
from map import Map

from game_objects import *

from bms_math import METERS_TO_FT

from ui.context_menu import ContextMenu

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
    def __init__(self, displaysurface: pygame.Surface, ui_manager: pygame_gui.UIManager):
        super().__init__(displaysurface)
        self._display_surf = displaysurface
        self._radar_surf = pygame.Surface(self._display_surf.get_size(), pygame.SRCALPHA)
        self._gamestate = GameState()
        self._drawBRAA = False
        self.unitFont = pygame.font.SysFont('Comic Sans MS', 14)
        self.cursorFont = pygame.font.SysFont('Comic Sans MS', 12)
        self.hover_obj_id: str = ""
        self.ui_manager = ui_manager
        
    def on_render(self):
        """
        Renders the radar display.
        """
        super().on_render()
        self._radar_surf.fill((0,0,0,0)) # Fill transparent
        

        self._draw_all_contacts(self._radar_surf)

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
        
    def resize(self, width, height):
        """
        Resizes the radar display.

        Args:
            width (int): The new width of the display.
            height (int): The new height of the display.
        """
        super().resize(width, height)
        self._radar_surf = pygame.Surface(self._display_surf.get_size(), pygame.SRCALPHA)

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
        
    def _draw_contact(self, surface: pygame.Surface, obj: GameObject) -> None:
        
        if obj.locked_target is not None:
            obj.draw(surface, self._world_to_screen(obj.get_pos()), self._px_per_nm(), 
                     target_pos=self._world_to_screen(obj.locked_target.get_pos()))
        else:
            obj.draw(surface, self._world_to_screen(obj.get_pos()), self._px_per_nm())
        
        
    def _draw_all_contacts(self, surface: pygame.Surface) -> None:
        
        for drawable_type in CLASS_MAP.values():
            for id in self._gamestate.new_objects[drawable_type]:
                obj = self._gamestate.new_objects[drawable_type][id]
                self._draw_contact(surface, obj)
    
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
        bearing = self._world_bearing(self._gamestate.get_bullseye_pos(), pos_world)
        distance = self._world_distance(self._gamestate.get_bullseye_pos(), pos_world)
        
        return bearing, distance
    
    def select_object(self, mouse_pos):
        
        CONTEXT_DIST = self._canvas_to_world((RADAR_CONTACT_SIZE_PX*8, 0))[0]
        
        obj = self._gamestate.get_nearest_object(self._screen_to_world(mouse_pos), CONTEXT_DIST)
        print(f"Selected object: {obj}")
            
        if obj is not None:
           menu = ContextMenu( (mouse_pos[0], mouse_pos[1]), obj, manager=self.ui_manager)