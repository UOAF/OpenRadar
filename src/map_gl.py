import OpenGL.GL as gl
import OpenGL.GLU as glu
import pygame
import bms_math
import numpy as np
import json

import config

def load_texture(filename: str):
    map_image = pygame.image.load(filename)
    texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    texture_format = gl.GL_RGBA
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, texture_format, *map_image.size, 0, texture_format, gl.GL_UNSIGNED_BYTE,
                    pygame.image.tobytes(map_image, "RGBA", flipped=True))
    return texture_id

def load_texture_data(data: np.ndarray):
    texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    texture_format = gl.GL_RGBA
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, texture_format, data.shape[1], data.shape[0], 0, texture_format, gl.GL_UNSIGNED_BYTE,
                    data)
    return texture_id

class MapGL:

    def __init__(self, display_size):
        self.display_size = display_size

        self.map_size_km = 1024  # in KM
        self.map_size_ft = self.map_size_km * bms_math.BMS_FT_PER_KM
        self.pan_x_screen = 0
        self.pan_y_screen = 0
        self.zoom_level = 1.0
        
        self.default_map()
        self.viewport()
        
        
    def list_maps(self):
        map_dir = config.bundle_dir / "resources/maps"
        with open(map_dir / "maps.json") as f:
            maps = json.load(f)       
        
        for theatre, data in maps.items():
            print(theatre, print (data["theatre_size_km"]))
            for map_entry in data["maps"]:
                print ("  ", map_entry["style"], map_entry["path"])
                map_entry["path"] = map_dir / map_entry["path"]
        return maps
        
        
    def load_map(self, filename, map_size_km):
        if self.texture_id is not None:
            gl.glDeleteTextures([self.texture_id])
            self.texture_id = None        
        self.texture_id = load_texture(filename)
        
        self.map_size_km = map_size_km
        self.map_size_ft = self.map_size_km * bms_math.BMS_FT_PER_KM
        
    def clear_map(self):
        if self.texture_id is not None:
            gl.glDeleteTextures([self.texture_id])
            self.texture_id = None
        self.default_map()
        
    def say_hi(self):
        print("Hello from MapGL")
        
    def default_map(self):
        grey = np.array([[535830592]], dtype=np.uint32) # 11111111100000010000001000000
        grey_pixel = np.array([[[128, 128, 128, 255]]], dtype=np.uint8)
        self.texture_id = load_texture_data(grey_pixel)
        self.map_size_km = 1024  # in KM
        self.map_size_ft = self.map_size_km * bms_math.BMS_FT_PER_KM

    def resize(self, display_size):
        ### This is the function that needs to be called when the window is resized
        self.display_size = display_size
        self.viewport()

    def on_render(self):
        half_map_size_ft = self.map_size_ft / 2
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        w, h = self.display_size
        #
        ratio = h / self.map_size_ft
        gl.glScalef(self.zoom_level, self.zoom_level, 1)
        gl.glTranslatef(self.pan_x_screen / self.zoom_level / ratio, self.pan_y_screen / self.zoom_level / ratio, 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0, 0)
        gl.glVertex2f(0, 0)
        gl.glTexCoord2f(0, 1)
        gl.glVertex2f(0, self.map_size_ft)
        gl.glTexCoord2f(1, 1)
        gl.glVertex2f(self.map_size_ft, self.map_size_ft)
        gl.glTexCoord2f(1, 0)
        gl.glVertex2f(self.map_size_ft, 0)
        gl.glEnd()

    def pan(self, dx_screen, dy_screen):
        self.pan_x_screen += dx_screen
        self.pan_y_screen -= dy_screen

    def screen_to_world(self, point_screen: pygame.Vector2):
        w, h = self.display_size
        ratio = h / self.map_size_ft
        pan = pygame.Vector2(self.pan_x_screen, -self.pan_y_screen)
        point_screen_with_pan = point_screen - pan
        point_screen_with_pan.y = h - point_screen_with_pan.y
        result = point_screen_with_pan / ratio / self.zoom_level
        return result

    def world_to_screen(self, point_world: pygame.Vector2):
        w, h = self.display_size
        ratio = h / self.map_size_ft

        point_screen_with_pan = point_world * ratio * self.zoom_level
        point_screen_with_pan.y = h - point_screen_with_pan.y

        pan = pygame.Vector2(self.pan_x_screen, -self.pan_y_screen)
        point_screen = point_screen_with_pan + pan
        return point_screen

    def zoom_at(self, mouse_pos, factor):
        # adjust the pan so that the world position of the mouse is preserved before and after zoom
        mouse_world_old = self.screen_to_world(pygame.Vector2(*mouse_pos))

        self.zoom_level += (factor / 10)
        self.zoom_level = max(0.05, self.zoom_level)

        mouse_world_new = self.screen_to_world(pygame.Vector2(*mouse_pos))
        delta_world = mouse_world_new - mouse_world_old
        w, h = self.display_size
        ratio = h / self.map_size_ft
        delta_screen = delta_world * ratio * self.zoom_level
        x, y = delta_screen
        self.pan_x_screen += x
        self.pan_y_screen += y

    def viewport(self):
        w, h = self.display_size
        aspect = w / h
        gl.glViewport(0, 0, w, h)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        scale = 1 / self.map_size_ft
        glu.gluOrtho2D(0, aspect, 0, 1)
        gl.glScalef(scale, scale, 1)
