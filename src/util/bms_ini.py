import configparser
# import pygame
import os

from util.bms_math import BMS_FT_PER_M, world_to_canvas

BMS_NUM_LINES = 4
BMS_LINE_POINTS = 6
BMS_NUM_THREATS = 15


class FalconBMSIni:

    def __init__(self, file_path):
        self.file_path = file_path
        self.data: configparser.ConfigParser
        self.lines = []
        self.threats = []
        self.load()
        # self.font = pygame.font.SysFont("Arial", 18) #TODO: render this in the screen surface to not have variable font size with map zoom

    def load(self):
        if not os.path.isfile(self.file_path):
            print(f"File {self.file_path} not found")
            return
        with open(self.file_path, "r") as f:
            data = f.read()

            self.data = configparser.ConfigParser()
            self.data.read_string(data)

        self.get_stpt_lines()
        self.get_ppt_threats()

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
                v, u = self.data["STPT"][f"linestpt_{i*BMS_LINE_POINTS+j}"].split(",")[0:2]
                x = float(u) / BMS_FT_PER_M
                y = float(v) / BMS_FT_PER_M
                if x > 1 and y > 1:
                    self.lines[i][j] = x, y

        # Remove empty lines and points
        self.lines = [[point for point in line if point is not None] for line in self.lines if any(line)]

    def get_ppt_threats(self):
        """
        Get the ppt threats from the file.
        """
        self.threats = []
        for i in range(0, BMS_NUM_THREATS):
            v, u, alt, radius, name = self.data["STPT"][f"ppt_{i}"].split(",")
            x = float(u) / BMS_FT_PER_M
            y = float(v) / BMS_FT_PER_M
            if float(radius) < 1: radius = 0
            r = float(radius) / BMS_FT_PER_M
            name = name.strip()

            if x > 1 and y > 1:
                self.threats.append(((x, y), r, name))
