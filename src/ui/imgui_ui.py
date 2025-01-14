import imgui
from imgui.integrations.glfw import GlfwRenderer
import numpy as np
import datetime
import os

from draw.scene import Scene
from draw.map_gl import MapGL
from draw.annotations import MapAnnotations
from trtt_client import TRTTClientThread, ThreadState
from game_state import GameState
from sensor_tracks import SensorTracks
from display_data import DisplayData
import config

from util.bms_math import METERS_TO_FT
from util.os_utils import open_file_dialog

# # Regex patterns for IPv4 and IPv6 validation
# ipv4_pattern = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
# ipv6_pattern = re.compile(
#     r'^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9]))\.){3,3}(25[0-5]|(2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9]))|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9]))\.){3,3}(25[0-5]|(2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])))$'
# )

# def validate_ip(ip: str) -> bool:
#     """
#     Validate an IP address.
#     """
#     return ipv4_pattern.match(ip) is not None or ipv6_pattern.match(ip) is not None


def TextCentered(text: str):
    window_width, window_height = imgui.get_window_size()
    text_width, text_height = imgui.calc_text_size(text)
    imgui.set_cursor_pos_x((window_width - text_width) * 0.5)
    imgui.set_cursor_pos_y((window_height - text_height) * 0.5)
    imgui.text(text)


class ImguiUserInterface:

    def __init__(self, size, window, scene: Scene, map_gl: MapGL, gamestate: GameState, tracks: SensorTracks,
                 display_data: DisplayData, annotations: MapAnnotations, data_client: TRTTClientThread):
        self.size = size
        self.scene = scene
        self.map_gl: MapGL = map_gl
        self.gamestate = gamestate
        self.tracks = tracks
        self.display_data = display_data
        self.annotations = annotations
        self.data_client = data_client

        imgui.create_context()
        io = imgui.get_io()
        io.display_size = self.size
        io.fonts.add_font_from_file_ttf(str(config.bundle_dir / "resources/fonts/ProggyClean.ttf"), 18)
        self.impl = GlfwRenderer(window, attach_callbacks=False)
        self._time: datetime.datetime = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

        self._fps = 0
        self._fps_history = [0] * 100
        self._frame_time = 0.0
        self._frame_time_history = [0] * 100

        self.fps_window_open = False
        self.layers_window_open = False
        self.settings_window_open = False
        self.server_window_open = False
        self.notepad_window_open = False
        self.debug_window_open = False

        self.map_selection_dialog_size = 1
        self.map_selection_dialog_path = ""
        self.map_selection_dialog_open = False

        self.server_password = ""
        self.server_connected = False

    # def on_event(self, event):
    #     return self.impl.process_event(event)

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

    @property
    def frame_time(self):
        return self._frame_time

    @frame_time.setter
    def frame_time(self, t):
        self._frame_time = t

    def update(self):
        self.impl.process_inputs()
        self._fps_history.append(self._fps)
        self._fps_history.pop(0)

        self._frame_time_history.append(int(self._frame_time))
        self._frame_time_history.pop(0)

        imgui.new_frame()
        self.ui_main_menu()
        self.ui_bottom_bar()
        self.map_selection_dialog()
        self.fps_counter()
        self.settings_window()
        self.server_window()
        self.notepad_window()
        self.debug_window()

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
                                    self.annotations.load_ini(open_file_dialog())
                                if imgui.menu_item('Clear', '', False, True)[0]:
                                    self.annotations.clear()

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
                        if imgui.menu_item('Debug', '', self.debug_window_open, True)[0]:
                            self.debug_window_open = not self.debug_window_open

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
                imgui.input_text("", self.map_selection_dialog_path, -1, imgui.INPUT_TEXT_READ_ONLY)

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
            TextCentered(self._time.strftime("%H:%M:%SZ"))

    def fps_counter(self):
        if not self.fps_window_open:
            return
        _, open = imgui.begin("FPS", True)
        fps_history = np.array(self._fps_history, np.float32)
        imgui.plot_lines("FPS", fps_history, graph_size=(0, 100))
        imgui.text(f"FPS: {self.fps:.2f}")
        frame_time_history = np.array(self._frame_time_history, np.float32)
        imgui.plot_lines("Frame time", frame_time_history, graph_size=(0, 100))
        imgui.text(f"Frame time: {np.mean(frame_time_history):.0f} ns")
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
                self.settings_tab_annotations()
                imgui.end_tab_item()
        imgui.end_tab_bar()
        imgui.end()

        if not open:
            self.settings_window_open = False
            config.app_config.save()

    def settings_tab_map(self):
        map_alpha = config.app_config.get_int("map", "map_alpha")
        map_background_color = config.app_config.get_color_normalized("map", "background_color")

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
            config.app_config.set_color_from_normalized("map", "background_color", bg_color_picker[1])

    def settings_tab_annotations(self):

        ini_width = config.app_config.get_int("annotations", "ini_width")
        ini_color = config.app_config.get_color_normalized("annotations", "ini_color")

        ini_color_picker = imgui.color_edit3("Ini Color", *ini_color)
        ini_width_slider = imgui.slider_int("Ini Line Width", ini_width, 1, 40)

        if ini_width_slider[0]:
            config.app_config.set("annotations", "ini_width", ini_width_slider[1])
        if ini_color_picker[0]:
            config.app_config.set_color_from_normalized("annotations", "ini_color", ini_color_picker[1])

    def layers_window(self):
        if not self.layers_window_open:
            return
        with imgui.begin("Layers"):
            pass  #TODO add layers window

    def server_window(self):
        if not self.server_window_open:
            return

        connected = False

        status, description = self.data_client.get_status()
        if status in [ThreadState.CONNECTED, ThreadState.CONNECTING]:
            connected = True

        _, open = imgui.begin("Server", True, imgui.WINDOW_ALWAYS_AUTO_RESIZE)

        if connected:
            imgui.internal.push_item_flag(imgui.internal.ITEM_DISABLED, True)

        address_changed, address = imgui.input_text("Address##server_address",
                                                    config.app_config.get_str("server", "address"), -1)

        port_changed, port = imgui.input_int("Port##server_port", config.app_config.get_int("server", "port"))
        imgui.same_line()
        if imgui.button("Default", width=80):
            config.app_config.set_default("server", "port")

        pw_changed, password = imgui.input_text("Password##server_password", self.server_password, -1)

        retries_changed, retries = imgui.input_int("Retries", config.app_config.get_int("server", "retries"))

        autoconnect_changed, autoconnect = imgui.checkbox("Autoconnect",
                                                          config.app_config.get_bool("server", "autoconnect"))

        if connected:
            imgui.internal.pop_item_flag()

        imgui.text("Status: ")
        imgui.same_line()

        imgui.text(f"{status.status_msg}  {description}")

        if imgui.button("Connect"):
            self.data_client.connect(address, port, password, retries)
        imgui.same_line()
        if imgui.button("Disconnect"):
            self.data_client.disconnect()
            self.gamestate.clear_state()
            self.tracks.clear()
            self.display_data.clear()
        imgui.end()

        if address_changed:
            config.app_config.set("server", "address", address)
        if port_changed:
            config.app_config.set("server", "port", port)
        if pw_changed:
            self.server_password = password
        if retries_changed:
            config.app_config.set("server", "retries", retries)
        if autoconnect_changed:
            config.app_config.set("server", "autoconnect", autoconnect)

        if not open:
            self.server_window_open = False
            config.app_config.save()

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

    def debug_window(self):
        if not self.debug_window_open:
            return
        _, open = imgui.begin("Debug", True)
        imgui.text(f"Mouse Pos: {imgui.get_mouse_pos()}")
        imgui.text(f"Mouse Pos (World (m)): {self.scene.screen_to_world(imgui.get_mouse_pos())}")
        imgui.text(f"Mouse Pos (World (ft)): {self.scene.screen_to_world(imgui.get_mouse_pos()) * METERS_TO_FT}")
        imgui.text(f"Pan: {self.scene._pan_screen}")
        imgui.text(f"Zoom: {self.scene.zoom_level}")
        imgui.text(f"Map Size: {self.scene.map_size_m}")
        if imgui.button("Load test ini"):
            self.annotations.load_ini(os.path.join(os.getcwd(), "Data", "test.ini"))
        imgui.end()
        if not open:
            self.debug_window_open = False

    # TODO handle map and ini drag-drops
