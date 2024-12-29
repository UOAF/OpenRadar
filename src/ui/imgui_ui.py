import imgui
from imgui.integrations.pygame import PygameRenderer

def menu_bar():
    pass

class ImguiUserInterface:
    def __init__(self, size):
        self.size = size
        
        imgui.create_context()
        imgui.get_io().display_size = self.size
        imgui.get_io().fonts.get_tex_data_as_rgba32()
        self.impl = PygameRenderer()
        
    def on_event(self, event):
        return self.impl.process_event(event)
    
    def render(self):
        
        imgui.render()
        self.impl.render(imgui.get_draw_data())
        imgui.end_frame()   
         
    def update(self):
        self.impl.process_inputs()
        imgui.new_frame()
        
        with imgui.begin("Your first window!", True):
            imgui.text("Hello world5!")

        
        imgui.begin("Bottom Bar", True, flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_COLLAPSE)
        imgui.text("This is the bottom bar")
        imgui.end()
        
        with imgui.begin_main_menu_bar() as main_menu_bar:
            if main_menu_bar.opened:
                # first menu dropdown
                with imgui.begin_menu('File', True) as file_menu:
                    if file_menu.opened:
                        imgui.menu_item('New', 'Ctrl+N', False, True)
                        imgui.menu_item('Open ...', 'Ctrl+O', False, True)

                        # submenu
                        with imgui.begin_menu('Open Recent', True) as open_recent_menu:
                            if open_recent_menu.opened:
                                imgui.menu_item('doc.txt', None, False, True)

        