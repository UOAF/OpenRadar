import imgui
from imgui.integrations.pygame import PygameRenderer

def TextCentered(text: str):
    window_width, window_height = imgui.get_window_size()
    text_width, text_height = imgui.calc_text_size(text)
    imgui.set_cursor_pos_x((window_width - text_width) * 0.5)
    imgui.set_cursor_pos_y((window_height - text_height) * 0.5)
    imgui.text(text)

class ImguiUserInterface:
    def __init__(self, size):
        self.size = size
        
        imgui.create_context()
        io = imgui.get_io()
        io.display_size = self.size
        io.fonts.add_font_from_file_ttf("resources/fonts/ProggyClean.ttf", 18) #TODO make this work with the exe bundle
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
        self.ui_main_menu()
        self.ui_bottom_bar()

    def ui_main_menu(self):
        
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

    def ui_bottom_bar(self):
        
        bottom_flags = (imgui.WINDOW_NO_TITLE_BAR | 
                        imgui.WINDOW_NO_RESIZE | 
                        imgui.WINDOW_NO_MOVE | 
                        imgui.WINDOW_NO_COLLAPSE)
        width = imgui.get_io().display_size[0]
        height = 80
        
        imgui.set_next_window_size(width, height)
        imgui.set_next_window_position(0, imgui.get_io().display_size[1] - height)
        with imgui.begin("Bottom Bar", True, flags=bottom_flags):
            TextCentered("This is the bottom bar")

            