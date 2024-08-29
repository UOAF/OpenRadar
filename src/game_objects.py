import pygame

from bms_math import *

class GameObject:
    def __init__(self, u, v, color: pygame.Color = pygame.Color(255,255,255)):
        self.u = u
        self.v = v
        self.color = color
        self.visible = True
        self.last_update = 0
        
    def update(self, u, v):
        self.u = u
        self.v = v
        
    def get_pos(self) -> tuple[float,float]:
        return (self.u, self.v)
        
    def set_color(self, color: pygame.Color):
        self.color = color
        
    def hide(self):
        self.visible = False
        
    def show(self):
        self.visible = True
        
    def draw(self, surface: pygame.Surface) -> None:
        pass
        
class MapAnnotation(GameObject):
    def __init__(self, u, v, color: pygame.Color = pygame.Color(255,255,0)):
        super().__init__(u, v, color)

class IniLine(MapAnnotation):
    def __init__(self, u, v, line, color: pygame.Color = pygame.Color(255,255,0)):
        super().__init__(u, v, color)
        self.line = line
        
class PrePlannedThreat(MapAnnotation):
    def __init__(self, u, v, radius, threat_type, color: pygame.Color = pygame.Color(255,255,0)):
        super().__init__(u, v, color)
        self.radius = radius
        self.text = threat_type

class Bullseye(MapAnnotation):
    
    BULLSEYE_NUM_RINGS = 8
    BULLSEYE_RING_NM = 20 # 20nm per ring
    
    def __init__(self, u, v, color: pygame.Color = pygame.Color(50,50,50,100)):
        super().__init__(u, v, color)

    def draw(self,  surface: pygame.Surface, pos: tuple[float, float], px_per_nm: float, line_width: int = 2) -> None:
            """
            Draws the bullseye on the radar display.

            Args:
                radar (pygame.Surface): The radar display on which to draw the bullseye.
                bullseye (tuple[int,int]): The position of the bullseye.
                line_width (int, optional): The size of the bullseye in pixels. Defaults to 2.
            """
            
            px_per_ring =  px_per_nm * self.BULLSEYE_RING_NM

            for i in range(1,self.BULLSEYE_NUM_RINGS):
                pygame.draw.circle(surface, self.color, pos, px_per_ring*i, line_width) # Draw 20nm circle
            
            # draw cross
            pygame.draw.line(surface, self.color, (pos[0]-px_per_ring*self.BULLSEYE_NUM_RINGS, pos[1]), 
                            (pos[0]+px_per_ring*self.BULLSEYE_NUM_RINGS, pos[1]), line_width)
            pygame.draw.line(surface, self.color, (pos[0], pos[1]-px_per_ring*self.BULLSEYE_NUM_RINGS),
                            (pos[0], pos[1]+px_per_ring*self.BULLSEYE_NUM_RINGS), line_width)
            
class groundUnit(GameObject):
    def __init__(self, u, v, unit_type, heading, speed):
        super().__init__(u, v)
        self.unit_type = unit_type
        self.heading = heading
        self.speed = speed # m/s
        
class airUnit(GameObject):
    def __init__(self, u, v, unit_type, heading, speed, altitude, color: pygame.Color = pygame.Color(255,255,255)):
        super().__init__(u, v, color)
        self.unit_type = unit_type
        self.heading = heading
        self.speed = speed # m/s
        self.altitude = altitude
        self.locked_target = None
        
    def get_surface(self) -> pygame.Surface:
        size = (20,20)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        
        contactrect = pygame.Rect((0,0,size,size))
        pygame.draw.rect(surface, self.color, contactrect, 2)
        
        velocity_line = self._getVelocityVector()
        
        return surface
    
    def draw(self, surface: pygame.Surface, pos) -> None:
        # def _draw_aircraft(self, surface: pygame.Surface, contact: ACMIObject, 
        #            color: pygame.Color, size: int = RADAR_CONTACT_SIZE_PX, hover=False) -> None:

        # pos = self._world_to_screen((contact.T.U, contact.T.V))
        heading = self.heading
        velocity = self.speed
        size = 12

        # Draw Square
        contactrect = pygame.Rect((0,0,size,size))
        contactrect.center = pos
        pygame.draw.rect(surface, self.color, contactrect, 2)

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
            
    def _getVelocityVector(self, heading: float | None = None, line_scale: int = 3) -> tuple[float,float]:
        """
        Calculates the start and end points of a velocity vector line to draw.

        Args:
        heading (float): The heading angle in degrees.
        line_scale (int): The scale factor for the velocity vector line. Default is 3.

        Returns:
            tuple[float,float]: The end point of the velocity vector.
        """
        line_max_len = 20 / 2 * 3 
        vel_scale = self.velocity / 1000.0
        vel_vec_len_px = RADAR_CONTACT_SIZE_PX/2 + vel_scale*size # Scale the velocity vector

        start_pt = start_pos

        heading_rad = math.radians(heading-90) # -90 rotaes north to up
        end_x = start_pt[0] + vel_vec_len_px*math.cos(heading_rad)
        end_y = start_pt[1] + vel_vec_len_px*math.sin(heading_rad)
        end_pt = (end_x, end_y)

        return (start_pt, end_pt)
    
class missile(airUnit):
    def __init__(self, u, v, unit_type, heading, speed, altitude):
        super().__init__(u, v, unit_type, heading, speed, altitude)
    
class fixedWing(airUnit):
    def __init__(self, u, v, unit_type, heading, speed, altitude):
        super().__init__(u, v, unit_type, heading, speed, altitude)

class rotaryWing(airUnit):
    def __init__(self, u, v, unit_type, heading, speed, altitude):
        super().__init__(u, v, unit_type, heading, speed, altitude)
        
class surfaceVessel(groundUnit):
    def __init__(self, u, v, unit_type, heading, speed):
        super().__init__(u, v, unit_type, heading, speed)
