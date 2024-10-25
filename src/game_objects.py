import pygame

import numpy as np

import config

from bms_math import *
from typing import Callable, Any
from acmi_parse import ACMIObject
from pygame_utils import draw_dashed_line

font : pygame.font.Font | None = None

class GameCoalition:
    pass

class GameObject:
    
    #font = pygame.font.SysFont("Courier New Regular", 18)
    # font = pygame.font.SysFont("Lucida Sans Typewriter", 18)
   
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(255,255,255)):
        self.data: ACMIObject = object
        self.color = color
        self.visible = True
        self.locked_target: GameObject | None = None
        self.override_name: str | None = None
        self.override_color: pygame.Color | None = None
        
        global font
        if font is None:
            font = pygame.font.SysFont("couriernewbold", 22)
        self.font = font
        
        self.color = pygame.Color(self.data.Color)

        # Switch the object's color from its default to a respective replacement color
        for i in config.app_config.get("map", "unit_color_switching", list):
            if self.color == pygame.Color(i[0]):
                if isinstance(i[1], list):
                    self.color = pygame.Color(i[1])
                else:
                    self.color = pygame.Color(i[1][0], i[1][1], i[1][2])
        
    def get_display_name(self) -> str:

        if self.override_name is not None and self.override_name != "":
            return f"{self.override_name}"
        
        elif self.data.Pilot != "":
            return f"{self.data.Pilot}"
        
        return f"{self.data.Type}"
        
    def update(self, object: ACMIObject):
        self.data.update(object.properties)

    def get_pos(self) -> tuple[float,float]:
        return (self.data.T.U, self.data.T.V)
        
    def set_color(self, color: pygame.Color):
        self.color = color
        
    def get_color(self) -> pygame.Color:
        return self.color
        
    def hide(self):
        self.visible = False
        
    def show(self):
        self.visible = True
    
    def get_context_items(self) -> list[tuple[str, Callable[[Any], None]]]:
        return [("Change Color", self.change_color),
                ("Change Name", self.change_name)]
        
    def change_color(self, color: pygame.Color):
        pass
    
    def change_name(self, name:str):
        self.override_name = name
    
    #Abstract method
    def draw(self, surface: pygame.Surface, position, px_per_meter, target_pos=None) -> None:
        return
    
class MapAnnotation(GameObject):
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(255,255,255)):
        super().__init__(object, color)
        
class IniLine(MapAnnotation):
    def __init__(self, object: ACMIObject, line, color: pygame.Color = pygame.Color(255,255,0)):
        super().__init__(object, color)
        self.line = line
        
class PrePlannedThreat(MapAnnotation):
    def __init__(self, object: ACMIObject, radius, threat_type, color: pygame.Color = pygame.Color(255,255,0)):
        super().__init__(object, color)
        self.radius = radius
        self.text = threat_type

class Bullseye(MapAnnotation):
    
    BULLSEYE_NUM_RINGS = 8
    BULLSEYE_RING_NM = 20 # 20nm per ring
    hide_class = False
    
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(50,50,50,100)):
        super().__init__(object, color)
        self.override_color = pygame.Color(50,50,50,100)

    def draw(self,  surface: pygame.Surface, pos: tuple[float, float], px_per_nm: float, line_width: int = 2) -> None:
            """
            Draws the bullseye on the radar display.

            Args:
                surface (pygame.Surface): The surface on which to draw the bullseye.
                bullseye (tuple[int,int]): The position of the bullseye.
                line_width (int, optional): The size of the bullseye in pixels. Defaults to 2.
            """
            if self.hide_class or not self.visible:
                return  # Don't draw if not visible
            
            color = self.color
            if self.override_color is not None:
                color = self.override_color
            
            px_per_ring =  px_per_nm * self.BULLSEYE_RING_NM

            for i in range(1,self.BULLSEYE_NUM_RINGS):
                pygame.draw.circle(surface, color, pos, px_per_ring*i, line_width) # Draw 20nm circle
            
            # draw cross
            pygame.draw.line(surface, color, (pos[0]-px_per_ring*self.BULLSEYE_NUM_RINGS, pos[1]), 
                            (pos[0]+px_per_ring*self.BULLSEYE_NUM_RINGS, pos[1]), line_width)
            pygame.draw.line(surface, color, (pos[0], pos[1]-px_per_ring*self.BULLSEYE_NUM_RINGS),
                            (pos[0], pos[1]+px_per_ring*self.BULLSEYE_NUM_RINGS), line_width)

class groundUnit(GameObject):
    
    hide_class = True
    
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(255,255,255)):
        super().__init__(object, color)
        
    def draw(self, surface: pygame.Surface, pos, px_per_nm, target=None) -> None:
        
        if self.hide_class:
            return

        color = self.color
        if self.override_color is not None:
            color = self.override_color
            
        size = 5           
        
        # Draw Circle
        pygame.draw.circle(surface, color, pos, size, 2)
        
class airUnit(GameObject):
    
    hide_class = False
    
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(255,255,255)):
        super().__init__(object, color)
        self.locked_target: GameObject | None = None

                
    def get_surface(self, px_per_meter) -> pygame.Surface:
        size = (20,20)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        
        contactrect = pygame.Rect((0,0,size,size))
        pygame.draw.rect(surface, self.color, contactrect, 2)
        
        # Draw Velocity Line
        vec = self._getVelocityVector(px_per_meter) # returns line starting at 0,0
        pygame.draw.line(surface, self.color, (0,0), vec, 3)
        
        return surface
    
    def draw(self, surface: pygame.Surface, pos, px_per_nm, *, target_pos: tuple[float,float] | None = None) -> None:
        # def _draw_aircraft(self, surface: pygame.Surface, contact: ACMIObject, 
        #            color: pygame.Color, size: int = RADAR_CONTACT_SIZE_PX, hover=False) -> None:

        # pos = self._world_to_screen((contact.T.U, contact.T.V))
    
        if self.hide_class or not self.visible:
            return  # Don't draw if not visible
        
        color = self.color
        if self.override_color is not None:
            color = self.override_color
    
        size = 14

        # Draw Square
        contactrect = pygame.Rect((0,0,size,size))
        contactrect.center = pos
        pygame.draw.rect(surface, color, contactrect, 3)

        # Draw Info Box
        text_surface = self._make_aircraft_text_info(color)
        textrect = pygame.Rect((0,0),text_surface.get_size())
        textrect.bottomright = int(contactrect.left-size/4), int(contactrect.top)
        
        surface.blit(text_surface, textrect)

        # Draw Name Line
        # Draw a line from the top left of the contact to the right side of the name
        pygame.draw.line(surface, pygame.Color("white"), contactrect.topleft, textrect.midright, 2)

        # Draw Velocity Line
        vec = self._getVelocityVector(px_per_nm) # returns line starting at 0,0
        end_point = (vec[0]+pos[0], vec[1]+pos[1])
        pygame.draw.line(surface, color, pos, end_point, 3)
        
        # draw dashed lock line to target
        if target_pos is not None:
            draw_dashed_line(surface, color, pos, target_pos, 1, 6)

        # if hover:
        #     pygame.draw.circle(surface, color, pos, size*2, 2)
            
    def _make_aircraft_text_info(self, color: pygame.Color) -> pygame.Surface:
        
        altitude = self.data.T.Altitude
        calibratedspeed = self.data.CAS
        
        text = self.get_display_name()
        
        name_surface = self.font.render(f"{text}", True, color)
        type_surface = self.font.render(f"{self.data.Name}", True, color)
        data_surface = self.font.render(
            f"{int(altitude*METERS_TO_FT//100)}  {(int(int(calibratedspeed)*M_PER_SEC_TO_KNOTS)//10)}", True, color)
        
        textrect = (max(name_surface.get_size()[0], data_surface.get_size()[0], type_surface.get_size()[0]), 
                   name_surface.get_size()[1]+ data_surface.get_size()[1] + type_surface.get_size()[1])
        surface = pygame.Surface(textrect, pygame.SRCALPHA)
        surface.fill((0,0,0,0))
        surface.blit(name_surface, (textrect[0]-name_surface.get_width() ,0))
        surface.blit(type_surface, (textrect[0]-type_surface.get_width(),name_surface.get_size()[1]))
        surface.blit(data_surface, (textrect[0]-data_surface.get_width(),name_surface.get_size()[1] + type_surface.get_size()[1]))
        
        return surface
            
    def _getVelocityVector(self, px_per_nm: float, heading: float | None = None, line_scale: int = 3) -> tuple[float,float]:
        """
        Calculates the end point of a velocity vector line to draw.

        Args:
        heading (float): The heading angle in degrees.
        line_scale (int): The scale factor for the velocity vector line. Default is 3.

        Returns:
            tuple[float,float]: The end point of the velocity vector.
        """
        LINE_LEN_SECONDS = 30 # 30 seconds of velocity vector
        px_per_second = px_per_nm * self.data.CAS / NM_TO_METERS # Scale the velocity vector 
        vel_vec_len_px = px_per_second * LINE_LEN_SECONDS # Scale the velocity vector

        heading_rad = math.radians(self.data.T.Heading-90) # -90 rotaes north to up
        end_x = vel_vec_len_px*math.cos(heading_rad)
        end_y = vel_vec_len_px*math.sin(heading_rad)
        end_pt = (end_x, end_y)

        return end_pt
    
class missile(airUnit):
    
    hide_class = False
    
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(255,255,255)):
        super().__init__(object, color)
    
    def draw(self, surface: pygame.Surface, pos, px_per_nm, target_pos=None):
        
        if self.hide_class or not self.visible:
            return  # Don't draw if not visible

        color = self.color
        if self.override_color is not None:
            color = self.override_color              
        
        size = 12
        
        # Define missile shape around origin        
        # missile_points = np.array([(0,-size), (-size/2, size/2), (size/2, size/2)])
        missile_points = np.array([(0,size), (-size/2, -size/2), (size/2, -size/2)])
        
        heading_rad = math.radians(self.data.T.Heading)
        
        # rotate shape around orgin towards heading
        # transformation_mat = ((math.cos(heading_rad), math.sin(heading_rad)),
        #                       (-math.sin(heading_rad), math.cos(heading_rad)))
        transformation_mat = ((math.cos(heading_rad), math.sin(heading_rad)),
                              (math.sin(heading_rad), -math.cos(heading_rad)))
        
        # (x', y') = (x, y) * transformation_mat
        
        # ( cos T -sin T )
        # ( sin T  cos T)
        
        # x' = x cos T - y sin T
        # y' = y cos T + x sin T
        
        # translate and rotate shape to contact position
        for i in range(len(missile_points)):
            rotated_point = np.matmul(missile_points[i], transformation_mat)
            missile_points[i] = np.add(rotated_point, pos)
        
        # draw shape at contact position
        for point in missile_points:
            pygame.draw.line(surface, color, pos, point, 2)
        
        # draw dotted lock line to target
        if target_pos is not None:
            # pygame.draw.line(surface, color, pos, target_pos, 2)
            draw_dashed_line(surface, color, pos, target_pos, 1, 6)
    
class fixedWing(airUnit):
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(255,255,255)):
        super().__init__(object, color)

class rotaryWing(airUnit):
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(255,255,255)):
        super().__init__(object, color)
        
    def draw(self, surface: pygame.Surface, pos, px_per_nm, target_pos=None) -> None:
        super().draw(surface, pos, px_per_nm, target_pos=target_pos)
        
class surfaceVessel(groundUnit):
    
    hide_class = False
    
    def __init__(self, object: ACMIObject, color: pygame.Color = pygame.Color(255,255,255)):
        super().__init__(object, color)
        
    def draw(self, surface: pygame.Surface, pos, px_per_nm, target=None) -> None:
        
        if self.hide_class or not self.visible:
            return  # Don't draw if not visible

        color = self.color
        if self.override_color is not None:
            color = self.override_color       
        
        size = 20
        # Define ship shape around origin        
        half = size/2
        qtr = size/4
        ship_points = np.array([(-half,0), (-qtr,0), (-qtr,-qtr), (qtr,-qtr), (qtr,0), (half,0), 
                                (qtr, qtr), (-qtr, qtr)])

        # translate and rotate shape to contact position
        for i in range(len(ship_points)):
            ship_points[i] = np.add(ship_points[i], pos)

        pygame.draw.polygon(surface, color, list(map(tuple, ship_points)), 2) # This is suprisingly slow #TODO make sprite and render