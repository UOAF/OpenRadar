
import glm
import OpenGL.GL as gl
import OpenGL.GLU as glu
import moderngl as mgl

from util import bms_math

class Scene:
    def __init__(self, display_size, mgl_context: mgl.Context):

        self.display_size = display_size
        self.mgl_context = mgl_context
        self.map_size_ft = bms_math.THEATRE_DEFAULT_SIZE_FT
        self._pan_screen = glm.vec2(0.0)
        self.zoom_level = 1.0
        self.mvp = glm.mat4(1.0)
        self.projection_matrix = glm.mat4(1.0)
        self.view_matrix = glm.mat4(1.0)
        
        self.resize(self.display_size)
        
        
    def get_mvp(self):
        return self.mvp
    
    def set_size(self, scene_size):
        self.map_size_ft = scene_size
        self.make_camera_matrix()      
        
    def resize(self, display_size):
        ### This is the function that needs to be called when the window is resized
        self.display_size = display_size
        gl.glViewport(0, 0, *display_size)
        self.make_camera_matrix()
        
    def make_camera_matrix(self):
        w, h = self.display_size
        aspect = w / h
        projection_matrix = glm.ortho(0.0, aspect, 0.0, 1.0, -1.0, 1.0)
     
        scale = 1 / self.map_size_ft
        scale = glm.mat4(scale)
        scale[2][2] = scale[3][3] = 1.0
        projection_mat_scaled = projection_matrix * scale
        
        x,y = self.screen_to_world_distance(self._pan_screen)           
        viewmatrix = glm.mat4(1.0)
        viewmatrix = glm.scale(viewmatrix, glm.vec3(self.zoom_level, self.zoom_level, 1.0))
        viewmatrix = glm.translate(viewmatrix, glm.vec3(x, y, 0.0))
        
        self.view_matrix = viewmatrix
        self.projection_matrix = projection_mat_scaled
        self.mvp = projection_mat_scaled * viewmatrix


    def pan(self, dx_screen, dy_screen):
        delta = glm.vec2(dx_screen, -dy_screen)
        self._pan_screen += delta
        self.make_camera_matrix()
        
    def screen_to_world(self, point_screen: glm.vec2):
        w, h = self.display_size
        ratio = h / self.map_size_ft
        point_screen.y = h - point_screen.y
        pan = self._pan_screen
        point_screen_with_pan = point_screen - pan
        result = point_screen_with_pan / ratio / self.zoom_level
        return result
    
    def screen_to_world_distance(self, distance_screen: glm.vec2|float):
        w, h = self.display_size
        ratio = h / self.map_size_ft
        return distance_screen / ratio / self.zoom_level
    
    def world_to_screen(self, point_world: glm.vec2):
        w, h = self.display_size
        ratio = h / self.map_size_ft

        point_screen_with_pan = point_world * ratio * self.zoom_level

        pan = glm.vec2(self._pan_screen)
        pan.y *= -1.0
        point_screen = point_screen_with_pan + pan
        point_screen.y = h - point_screen.y
        return point_screen

    def zoom_at(self, mouse_pos, factor):
        # adjust the pan so that the world position of the mouse is preserved before and after zoom
        mouse_world_old = self.screen_to_world(glm.vec2(*mouse_pos))

        self.zoom_level += (factor / 10)
        self.zoom_level = max(0.05, self.zoom_level)

        mouse_world_new = self.screen_to_world(glm.vec2(*mouse_pos))
        delta_world = mouse_world_new - mouse_world_old
        w, h = self.display_size
        ratio = h / self.map_size_ft
        delta_screen = delta_world * ratio * self.zoom_level
        x, y = delta_screen
        self._pan_screen += glm.vec2(x, y)
        self.make_camera_matrix()