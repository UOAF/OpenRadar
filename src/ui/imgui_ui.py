import imgui
from imgui.integrations.pygame import PygameRenderer
import numpy as np
import datetime

from map_gl import MapGL
import config

from os_uils import open_file_dialog


def TextCentered(text: str):
    window_width, window_height = imgui.get_window_size()
    text_width, text_height = imgui.calc_text_size(text)
    imgui.set_cursor_pos_x((window_width - text_width) * 0.5)
    imgui.set_cursor_pos_y((window_height - text_height) * 0.5)
    imgui.text(text)


class ImguiUserInterface:

    def __init__(self, size, map_gl: MapGL):
        self.size = size
        self.map_gl: MapGL = map_gl

        imgui.create_context()
        io = imgui.get_io()
        io.display_size = self.size
        io.fonts.add_font_from_file_ttf("resources/fonts/ProggyClean.ttf", 18)  #TODO make this work with the exe bundle
        self.impl = PygameRenderer()
        self._time = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

        self._fps = 0
        self._fps_history = [0] * 10000

        self.fps_window_open = False
        self.layers_window_open = False
        self.settings_window_open = False
        self.server_window_open = False
        self.notepad_window_open = False

        self.map_selection_dialog_size = 1
        self.map_selection_dialog_path = ""
        self.map_selection_dialog_open = False

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
        self.map_selection_dialog()
        self.fps_counter()
        self.settings_window()
        self.server_window()
        self.notepad_window()

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
                                        self.map_list_menu()
                                        if imgui.menu_item('Custom', '', False, True)[0]:
                                            self.map_selection_dialog_open = True

                                if imgui.menu_item('Clear', '', False, True)[0]:
                                    self.map_gl.clear_map()

                        # Ini submenu
                        with imgui.begin_menu('Ini', True) as ini_menu:
                            if ini_menu.opened:
                                if imgui.menu_item('Load', None, False, True)[0]:
                                    print("Load ini")
                                if imgui.menu_item('Clear', '', False, True)[0]:
                                    print("Clear ini")

                        if imgui.menu_item('Settings', None, self.settings_window_open, True)[0]:
                            self.settings_window_open = not self.settings_window_open

                # Windows Dropdown
                with imgui.begin_menu('Windows', True) as windows_menu:
                    if windows_menu.opened:
                        
                        if imgui.menu_item('Server', '', self.server_window_open, True)[0]:
                            self.server_window_open = not self.server_window_open
                        if imgui.menu_item('Layers', '', self.layers_window_open, True)[0]:
                            self.layers_window_open = not self.layers_window_open
                        if imgui.menu_item('Notepad', '', self.notepad_window_open, True)[0]:
                            self.notepad_window_open = not self.notepad_window_open
                        if imgui.menu_item('FPS', '', self.fps_window_open, True)[0]:
                            self.fps_window_open = not self.fps_window_open

    def map_list_menu(self):
        maps = self.map_gl.list_maps()
        for theatre, data in maps.items():
            with imgui.begin_menu(theatre, True) as theatre_menu:
                if theatre_menu.opened:
                    for map_entry in data["maps"]:
                        if imgui.menu_item(map_entry["style"], None, False, True)[0]:
                            self.map_gl.load_map(map_entry["path"], data["theatre_size_km"])

    def map_selection_dialog(self):

        if self.map_selection_dialog_open:
            imgui.open_popup("Map Selection")
            if imgui.begin_popup_modal("Map Selection", True)[0]:

                # Create input text field with folder path
                imgui.input_text("", self.map_selection_dialog_path, 256, imgui.INPUT_TEXT_READ_ONLY)

                # Button with folder icon
                imgui.same_line()
                if imgui.button("Select Map"):
                    # Open folder dialog
                    selected_folder = open_file_dialog()
                    if selected_folder:  # Update the path if selected
                        self.map_selection_dialog_path = selected_folder

                sizes = ["512", "1024", "4096"]
                _, self.map_selection_dialog_size = imgui.combo("Theatre Size (km)", self.map_selection_dialog_size,
                                                                sizes)

                if imgui.button("Confirm"):
                    self.map_gl.load_map(self.map_selection_dialog_path, int(sizes[self.map_selection_dialog_size]))
                    self.map_selection_dialog_open = False
                    imgui.close_current_popup()
                imgui.end_popup()

    def ui_bottom_bar(self):

        bottom_flags = (imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE
                        | imgui.WINDOW_NO_COLLAPSE)
        width = imgui.get_io().display_size[0]
        height = 50

        imgui.set_next_window_size(width, height)
        imgui.set_next_window_position(0, imgui.get_io().display_size[1] - height)
        with imgui.begin("Bottom Bar", True, flags=bottom_flags):
            TextCentered(self.time.strftime("%H:%M:%SZ"))

    def fps_counter(self):
        if not self.fps_window_open:
            return
        _, open = imgui.begin("FPS", True)
        fps_history = np.array(self._fps_history, np.float32)
        imgui.plot_lines("FPS", fps_history, graph_size=(0, 100))
        imgui.text(f"FPS: {self.fps:.2f}")
        imgui.end()

        if not open:
            self.fps_window_open = False

    def settings_window(self):

        if not self.settings_window_open:
            return

        _, open = imgui.begin("Settings", True)
        if imgui.begin_tab_bar("Settings Tabs"):
            if imgui.begin_tab_item("Map").selected:
                self.settings_tab_map()
                imgui.end_tab_item()
            if imgui.begin_tab_item("Annotations").selected:
                imgui.end_tab_item()
        imgui.end_tab_bar()
        imgui.end()

        if not open:
            self.settings_window_open = False
            
    def settings_tab_map(self):
        map_alpha = config.app_config.get_int("map", "map_alpha")
        map_background_color = [float(c / 255) for c in config.app_config.get_list_int("map", "background_color")]
        
        bg_color_picker = imgui.color_edit3("Background Color", *map_background_color)
        imgui.same_line()
        imgui.text_disabled("(?)")
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text_unformatted("Click on the color square to open a color picker.\n"
                                    "CTRL+click on individual component to input value.\n")
            imgui.end_tooltip()
            
        alpha_slider = imgui.slider_int("Map Alpha", map_alpha, 0, 255)
        imgui.text("Map Size")
        
        if alpha_slider[0]:
            config.app_config.set("map", "map_alpha", alpha_slider[1])
        if bg_color_picker[0]:
            config.app_config.set("map", "background_color", [int(c * 255) for c in bg_color_picker[1]])

    def layers_window(self):
        if not self.layers_window_open:
            return
        with imgui.begin("Layers"):
            pass #TODO add layers window
        
    def server_window(self):
        if not self.server_window_open:
            return
        
        _, open = imgui.begin("Server")
        
        imgui.text("Server Address")
        imgui.same_line()
        imgui.input_text("##server_address", "localhost:42674", 256)
        imgui.text("Server Status: ")
        imgui.same_line()
        imgui.text("Not Connected")
        imgui.text("Server Password")
        imgui.same_line()
        imgui.input_text("##server_password", "", 256)
        if imgui.button("Connect"):
            pass #TODO add server connection logic
        imgui.same_line()
        if imgui.button("Disconnect"):
            pass #TODO add server disconnection logic 
        imgui.end()
        
        if not open:
            self.server_window_open = False
            
    def notepad_window(self):
        if not self.notepad_window_open:
            return
        _, open = imgui.begin("Notepad", True)
        notes = config.app_config.get_str("notepad", "notes")
        
        # Get window size
        width, height = imgui.get_content_region_available()
        changed, notes = imgui.input_text_multiline("", notes, -1, width, height, imgui.INPUT_TEXT_ALLOW_TAB_INPUT)
        imgui.end()
        
        if changed:
            config.app_config.set("notepad", "notes", notes)
        if not open:
            self.notepad_window_open = False
        
    

