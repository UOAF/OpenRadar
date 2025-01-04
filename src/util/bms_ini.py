import configparser
# import pygame

from util.bms_math import BMS_FT_PER_M, world_to_canvas

BMS_NUM_LINES = 4
BMS_LINE_POINTS = 6
BMS_NUM_THREATS = 15

class FalconBMSIni:
    def __init__(self, file_path, map_size_meters=1024):
        self.file_path = file_path
        self.data: configparser.ConfigParser
        self.lines = []
        self.threats = []
        self.load()
        # self.font = pygame.font.SysFont("Arial", 18) #TODO: render this in the screen surface to not have variable font size with map zoom

    def load(self):
        with open(self.file_path, "r") as f:
            data = f.read()
            
            self.data = configparser.ConfigParser()
            self.data.read_string(data)

        self.get_stpt_lines()
        self.get_ppt_threats()
        
    # def get_surf(self, size, color=(255, 255, 0)) -> pygame.Surface:
        
    #     surface = pygame.Surface(size, pygame.SRCALPHA)
    #     surface.fill((0, 0, 0, 0))
        
    #     for line in self.lines:
    #         self.draw_line(surface, line, color)
            
    #     for threat in self.threats:
    #         self.draw_threat(surface, threat, color)
        
    #     return surface
        
    # def draw_line(self, surface, line, color):
        
    #     for i in range(0, len(line)-1):
    #         if (line[i][0] < 1 or line[i+1][0] < 1):
    #             continue
            
    #         point1 = world_to_canvas(line[i], surface.get_size())
    #         point2 = world_to_canvas(line[i+1], surface.get_size())
        
    #         pygame.draw.line(surface, color, point1, point2, width=2)
        
    # def draw_threat(self, surface, threat, color):
        
    #     threat_pos = world_to_canvas(threat[0], surface.get_size())
    #     threat_radius = world_to_canvas((threat[1], 0), surface.get_size())[0]
        
    #     pygame.draw.circle(surface, color, threat_pos, int(threat_radius), width=3)
        
    #     threat_text = self.font.render(f"{str(threat[2])}", True, color)

    #     textrect = pygame.Rect((0,0),threat_text.get_size())
    #     textrect.center = threat_pos

    #     surface.blit(threat_text, textrect)
        
    def print(self):
        
        print(self.data.sections())
        if self.data.sections() == []:
            print("No sections found in file")
            
        for section in self.data.sections():
            print(section)
            for key in self.data[section]:
                print(f"\t{key} = {self.data[section][key]}")
                
    def get_stpt_lines(self):
        """
        Get the stpt lines from the file.
        """
        self.lines = []
        for i in range(0, BMS_NUM_LINES):
            self.lines.append([None] * BMS_LINE_POINTS)
            for j in range(0, BMS_LINE_POINTS):
                v,u = self.data["STPT"][f"linestpt_{i*BMS_LINE_POINTS+j}"].split(",")[0:2]
                x = float(u) / BMS_FT_PER_M
                y = float(v) / BMS_FT_PER_M
                self.lines[i][j] = x, y

    def get_ppt_threats(self):
        """
        Get the ppt threats from the file.
        """
        self.threats = []
        for i in range(0, BMS_NUM_THREATS):
            v,u,alt,radius,name = self.data["STPT"][f"ppt_{i}"].split(",")
            x = float(u) / BMS_FT_PER_M
            y = float(v) / BMS_FT_PER_M
            if float(radius) < 1: radius = 0
            r = float(radius) / BMS_FT_PER_M
            name = name.strip()
            
            if x > 1 and y > 1:
                self.threats.append(((x, y), r, name))