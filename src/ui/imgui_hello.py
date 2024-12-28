import imgui
from imgui.integrations.pygame import PygameRenderer

class ImguiUI:
    def __init__(self, display_size: tuple[int, int] = (100, 100)):
        imgui.create_context()
        imgui.get_io().display_size = display_size
        imgui.get_io().fonts.get_tex_data_as_rgba32()
        self.impl = PygameRenderer()
        
    def on_event(self, event):
        self.impl.process_event(event)
    
    def render(self):
        
        imgui.render()
        self.impl.render(imgui.get_draw_data())
        imgui.end_frame()   
         
    def update(self):
        self.impl.process_inputs()
        imgui.new_frame()
        
        imgui.begin("Your first window!", True)
        imgui.text("Hello world!")
        imgui.end()

            