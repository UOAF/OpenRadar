import OpenGL.GL as gl
import OpenGL.GLU as glu
from numpy import half
import pygame
import bms_math


def load_texture(filename: str):
    map_image = pygame.image.load(filename)
    texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    texture_format = gl.GL_RGB
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, texture_format, *map_image.size, 0, texture_format, gl.GL_UNSIGNED_BYTE,
                    pygame.image.tobytes(map_image, "RGB", flipped=True))
    return texture_id


class MapGL:

    def __init__(self, display_size):
        self.display_size = display_size
        self.texture_filename = "resources/maps/Korea.jpg"
        # self.map_size_px = 4096  # in pixels
        self.map_size_km = 1024  # in KM
        self.map_size_ft = self.map_size_km * bms_math.BMS_FT_PER_KM
        # self.px_per_ft = self.map_size_px / self.map_size_ft
        self.pan_x_screen = 0
        self.pan_y_screen = 0
        self.zoom_level = 1.0
        self.texture_id = load_texture(self.texture_filename)
        self.viewport()

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

    # def zoom_at(self, mouse_pos, factor):
    #     x, y = mouse_pos
    #     self.pan(-x, -y)
    #     self.zoom(factor)
    #     self.pan(x, y)

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
        mouse_world = self.screen_to_world(pygame.Vector2(*mouse_pos))
        # pan_x_world_old = self.pan_x_screen * self.zoom_level / self.px_per_ft
        # pan_y_world_old = self.pan_x_screen * self.zoom_level / self.px_per_ft

        self.zoom_level += (factor / 10)
        self.zoom_level = max(0.05, self.zoom_level)

        # pan_x_world = self.pan_x_screen * self.zoom_level / self.px_per_ft
        # pan_y_world = self.pan_x_screen * self.zoom_level / self.px_per_ft

        # delta_x_world = pan_x_world_old - pan_x_world
        # delta_y_world = pan_y_world_old - pan_y_world

        # delta_x_screen = delta_x_world * self.px_per_ft / self.zoom_level
        # delta_y_screen = delta_y_world * self.px_per_ft / self.zoom_level
        # self.pan_x_screen += delta_x_screen
        # self.pan_y_screen += delta_y_screen

        # zoom is centered on center of texture

        # self.pan_x *= factor
        # self.pan_y *= factor

    def viewport(self):
        w, h = self.display_size
        aspect = w / h
        gl.glViewport(0, 0, w, h)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        scale = 1 / self.map_size_ft
        glu.gluOrtho2D(0, aspect, 0, 1)
        gl.glScalef(scale, scale, 1)

    # def setup(self):
    #     gl.glMatrixMode(gl.GL_MODELVIEW)
    #     gl.glLoadIdentity()
    #     gl.glTranslatef(self.pan_x, self.pan_y, 0.0)
    #     gl.glScalef(self.zoom_level, self.zoom_level, 1.0)
