import imgui
from imgui.integrations.pygame import PygameRenderer
import numpy as np


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
        io.fonts.add_font_from_file_ttf("resources/fonts/ProggyClean.ttf", 18)  #TODO make this work with the exe bundle
        self.impl = PygameRenderer()
        self._fps = 0
        self._time = ""
        self._fps_history = [0] * 10000
        self.fps_enabled = False

    def on_event(self, event):
        return self.impl.process_event(event)

    def render(self):

        imgui.render()
        self.impl.render(imgui.get_draw_data())
        imgui.end_frame()

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, fps):
        self._fps = fps

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, time):
        self._time = time

    def update(self):
        self.impl.process_inputs()
        self._fps_history.append(self._fps)
        self._fps_history.pop(0)
        
        
        imgui.new_frame()
        self.ui_main_menu()
        self.ui_bottom_bar()


    def ui_main_menu(self):

        with imgui.begin_main_menu_bar() as main_menu_bar:
            if main_menu_bar.opened:
                
                # File Dropdown
                with imgui.begin_menu('File', True) as file_menu:
                    if file_menu.opened:
                        
                        # Map submenu
                        with imgui.begin_menu('Map', True) as map_menu:
                            if map_menu.opened:
                                # submenu
                                with imgui.begin_menu('Load', True) as open_recent_menu:
                                    if open_recent_menu.opened:
                                        imgui.menu_item('', None, False, True)
                                imgui.menu_item('Clear', '', False, True)
                        # Ini submenu
                        with imgui.begin_menu('Ini', True) as ini_menu:
                            if ini_menu.opened:
                                if imgui.menu_item('Load', None, False, True)[0]:
                                    print("Load ini")
                                if imgui.menu_item('Clear', '', False, True)[0]:
                                    print("Clear ini")
                
                # Windows Dropdown
                with imgui.begin_menu('Windows', True) as windows_menu:
                    if windows_menu.opened:
                        fps_menu = imgui.menu_item('FPS', '', self.fps_enabled, True)
                        if fps_menu[0]:
                            self.fps_enabled = not self.fps_enabled
                    if self.fps_enabled:
                        self.fps_counter()

    def ui_bottom_bar(self):

        bottom_flags = (imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE
                        | imgui.WINDOW_NO_COLLAPSE)
        width = imgui.get_io().display_size[0]
        height = 80

        imgui.set_next_window_size(width, height)
        imgui.set_next_window_position(0, imgui.get_io().display_size[1] - height)
        with imgui.begin("Bottom Bar", True, flags=bottom_flags):
            TextCentered("This is the bottom bar")

    def fps_counter(self):
        
          with imgui.begin("FPS"):      
            fps_history = np.array(self._fps_history, np.float32)
            imgui.plot_lines("FPS", fps_history, graph_size=(0, 100))
            imgui.text(f"FPS: {self.fps:.2f}")