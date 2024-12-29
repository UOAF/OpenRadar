import OpenGL.GL as gl
import OpenGL.GLU as glu
import pygame


def load_texture(filename: str):
    map_image = pygame.image.load(filename)
    texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    texture_format = gl.GL_RGB
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, texture_format, *map_image.size, 0, texture_format, gl.GL_UNSIGNED_BYTE,
                    pygame.image.tobytes(map_image, "RGB", flipped=False))
    return texture_id


class MapGL:

    def __init__(self, display_size):
        self.display_size = display_size
        self.texture_filename = "resources/maps/Korea.jpg"
        self.pan_x = 0
        self.pan_y = 0
        self.zoom_level = 1.0
        self.texture_id = load_texture(self.texture_filename)
        self.viewport()

    def resize(self, display_size):
        ### This is the function that needs to be called when the window is resized
        self.display_size = display_size
        self.viewport()

    def on_render(self):
        # self.viewport()
        # self.viewport(*self.display_size)
        # w, h = self.display_size
        # gl.glMatrixMode(gl.GL_PROJECTION)
        # gl.glLoadIdentity()
        # glu.gluOrtho2D(0, w, 0, h)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glScalef(self.zoom_level, self.zoom_level, 1)
        gl.glTranslatef(self.pan_x, self.pan_y, 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0, 0)
        gl.glVertex2f(-1, 1)
        gl.glTexCoord2f(0, 1)
        gl.glVertex2f(-1, -1)
        gl.glTexCoord2f(1, 1)
        gl.glVertex2f(1, -1)
        gl.glTexCoord2f(1, 0)
        gl.glVertex2f(1, 1)
        gl.glEnd()

    def pan(self, dx, dy):
        print(f"panning by {dx}, {dy}")
        w, h = self.display_size
        self.pan_x += dx / w
        self.pan_y += dy / h

    def zoom(self, mouse_pos, factor):
        self.zoom_level += (factor / 10)
        self.zoom_level = max(0.01, self.zoom_level)
        self.pan_x *= factor
        self.pan_y *= factor

    def viewport(self):
        w, h = self.display_size
        gl.glViewport(0, 0, w, h)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluOrtho2D(-w / h / 2, w / h / 2, -0.5, 0.5)
        # glu.gluOrtho2D(0, w, 0, h)

    # def setup(self):
    #     gl.glMatrixMode(gl.GL_MODELVIEW)
    #     gl.glLoadIdentity()
    #     gl.glTranslatef(self.pan_x, self.pan_y, 0.0)
    #     gl.glScalef(self.zoom_level, self.zoom_level, 1.0)
