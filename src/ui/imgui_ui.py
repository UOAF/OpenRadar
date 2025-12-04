from imgui_bundle import imgui
from imgui_bundle import portable_file_dialogs as pfd  # type: ignore
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

import numpy as np
import datetime
import os

from logging_config import get_logger
from draw.scene import Scene
from draw.map_gl import MapGL
from draw.annotations import MapAnnotations
from game_object import GameObject
from trtt_client import TRTTClientThread, ThreadState
from game_state import GameState
from game_object_types import GameObjectType
from sensor_tracks import SensorTracks, Track, Coalition
from display_data import DisplayData
from render_data_arrays import TrackRenderDataArrays
import config

from util.bms_math import METERS_TO_FT, NM_TO_METERS, M_PER_SEC_TO_KNOTS
from util.track_labels import *
from util.other_utils import get_all_attributes

# # Regex patterns for IPv4 and IPv6 validation
# ipv4_pattern = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
# ipv6_pattern = re.compile(
#     r'^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9]))\.){3,3}(25[0-5]|(2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9]))|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9]))\.){3,3}(25[0-5]|(2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])))$'
# )

# def validate_ip(ip: str) -> bool:
#     """
#     Validate an IP address.
#     """
# return ipv4_pattern.match(ip) is not None or ipv6_pattern.match(ip) is not None

example_object = GameObject("ExampleObject", GameObjectType.FIXEDWING, None)
example_object.CallSign = "ExampleCallSign"
example_object.Pilot = "ExamplePilot"
example_object.Altitude = 15000
example_object.Heading = 270
example_object.Mach = 0.85
example_object.CAS = 300
example_object.FuelWeight = 5000
example_object.AOA = 5.0
example_object.Coalition = "U.S."
example_object.Name = "F-16C"

IMGUI_INI_FILENAME = "openradar_imgui.ini"


def help_marker(description: str):
    imgui.text_disabled("(?)")
    if imgui.is_item_hovered():
        imgui.begin_tooltip()
        imgui.push_text_wrap_pos(imgui.get_font_size() * 35.0)
        imgui.text_unformatted(description)
        imgui.pop_text_wrap_pos()
        imgui.end_tooltip()


def TextCentered(text: str):
    window_width, window_height = imgui.get_window_size()
    text_width, text_height = imgui.calc_text_size(text)
    imgui.set_cursor_pos_x((window_width - text_width) * 0.5)
    imgui.set_cursor_pos_y((window_height - text_height) * 0.5)
    imgui.text(text)


def _in_bounds(mouse_pos, window_pos, window_size):
    return (window_pos.x <= mouse_pos.x <= window_pos.x + window_size.x
            and window_pos.y <= mouse_pos.y <= window_pos.y + window_size.y)


# UI Helper Functions for reducing code duplication
def create_slider_float(label, value, min_val, max_val, config_section, config_key):
    """Helper function to create a float slider and update configuration."""
    changed, new_value = imgui.slider_float(label, value, min_val, max_val)
    if changed:
        config.app_config.set(config_section, config_key, new_value)
    return changed, new_value


def create_slider_int(label, value, min_val, max_val, config_section, config_key):
    """Helper function to create an int slider and update configuration."""
    changed, new_value = imgui.slider_int(label, value, min_val, max_val)
    if changed:
        config.app_config.set(config_section, config_key, new_value)
    return changed, new_value


def create_checkbox(label, value, config_section, config_key):
    """Helper function to create a checkbox and update configuration."""
    changed, new_value = imgui.checkbox(label, value)
    if changed:
        config.app_config.set(config_section, config_key, new_value)
    return changed, new_value


def create_color_edit(label, color, config_section, config_key):
    """Helper function to create a color picker and update configuration."""
    changed, new_color = imgui.color_edit3(label, [*color])
    if changed:
        color_tuple = (new_color[0], new_color[1], new_color[2])
        config.app_config.set_color_from_normalized(config_section, config_key, color_tuple)
    return changed, new_color


def update_config_if_changed(changed, config_section, config_key, value):
    """Helper function to update configuration only if value changed."""
    if changed:
        config.app_config.set(config_section, config_key, value)


class ImguiUserInterface:

    def __init__(self, size, window, scene: Scene, map_gl: MapGL, gamestate: GameState, tracks: SensorTracks,
                 display_data: DisplayData, data_client: TRTTClientThread):
        self.size = size
        self.scene = scene
        self.map_gl: MapGL = map_gl
        self.gamestate = gamestate
        self.tracks = tracks
        self.display_data = display_data
        self.annotations = display_data.annotations
        self.data_client = data_client
        self.reset_state_callback = None
        self.render_refresh_callback = None

        # Initialize logger
        self.logger = get_logger(f"{__name__}.ImguiUserInterface")
        self.logger.debug("Initializing ImGui UI")

        imgui.create_context()
        io = imgui.get_io()
        io.display_size = self.size

        ini_file_path = str(config.application_dir / IMGUI_INI_FILENAME)
        self.logger.info(f"ImGui INI file path: {ini_file_path}")
        io.set_ini_filename(ini_file_path)

        io.fonts.add_font_from_file_ttf(str(config.bundle_dir / "resources/fonts/ProggyClean.ttf"), 18)

        # Enable docking support
        io.config_flags = imgui.ConfigFlags_.docking_enable.value
        # Optional: Enable viewports for multi-monitor support
        # io.config_flags |= imgui.ConfigFlags_.viewports_enable.value

        # Configure docking behavior
        io.config_docking_no_split = False
        io.config_docking_with_shift = False
        io.config_docking_always_tab_bar = False
        io.config_docking_transparent_payload = True

        self.impl = GlfwRenderer(window, attach_callbacks=False)
        self._time: datetime.datetime = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

        self._fps = 0
        self._fps_history = [0.0] * 4000
        self._frame_time = 0.0
        self._frame_time_history = [0.0] * 4000
        self._cpu_frame_time = 0.0
        self._cpu_frame_time_history = [0.0] * 4000
        self.context_object: GameObject | None = None
        self.most_recent_context_object: GameObject | None = None
        self.flag_open_context_menu = False

        self.fps_window_open = False
        self.layers_window_open = False
        self.settings_window_open = False
        self.server_window_open = True
        self.notepad_window_open = False
        self.debug_window_open = False
        self.track_labels_window_open = False
        self.track_info_window_open = False
        self.scale_indicator_window_open = True
        self.tacview_colors_window_open = False
        self.contact_color_window_open = False

        self.map_selection_dialog_size = 1
        self.map_selection_dialog_path = ""
        self.map_selection_dialog_open = False

        self.scale_indicator_hovered = False

        self.server_password = ""
        self.server_connected = False

        self.track_labels_selected_square = (0, 0)

        # Modal state
        self.callsign_modal_open = False
        self.callsign_input_text = ""
        self.callsign_original_text = ""

        # Contact color window state
        self.custom_colors = []  # List of previously used custom colors
        self.current_contact_color = [1.0, 1.0, 1.0, 1.0]  # Current color being edited

        # File dialog state
        self.ini_file_dialog = None
        self.map_file_dialog = None

        # BRAA line state
        self.braa_active = False
        self.braa_start_world = None
        self.braa_start_screen = None

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

    @property
    def cpu_frame_time(self):
        return self._cpu_frame_time

    @cpu_frame_time.setter
    def cpu_frame_time(self, t):
        self._cpu_frame_time = t

    def set_reset_callback(self, callback):
        self.reset_state_callback = callback

    def set_render_refresh_callback(self, callback):
        """Set callback to refresh render arrays when configuration changes."""
        self.render_refresh_callback = callback

    def open_ini_file_dialog(self):
        """Open a non-blocking file dialog for selecting INI files."""
        # Don't open a new dialog if one is already active
        if self.ini_file_dialog is not None:
            return False

        try:
            # Use portable file dialogs for cross-platform file selection (non-blocking)
            self.ini_file_dialog = pfd.open_file("Select INI File", "", ["INI files", "*.ini", "All files", "*"])
            return True  # Dialog opened successfully
        except Exception as e:
            self.logger.error(f"Error opening INI file dialog: {e}")
            return False

    def open_map_file_dialog(self):
        """Open a non-blocking file dialog for selecting map image files."""
        # Don't open a new dialog if one is already active
        if self.map_file_dialog is not None:
            return False

        try:
            # Use portable file dialogs for cross-platform file selection (non-blocking)
            self.map_file_dialog = pfd.open_file("Select Map Image", "",
                                                 ["PNG files", "*.png", "JPG files", "*.jpg", "All files", "*"])
            return True  # Dialog opened successfully
        except Exception as e:
            self.logger.error(f"Error opening map file dialog: {e}")
            return False

    def check_file_dialogs(self):
        """Check for completed file dialog results and process them."""
        # Check INI file dialog
        if self.ini_file_dialog is not None:
            try:
                if self.ini_file_dialog.ready():
                    result = self.ini_file_dialog.result()
                    self.ini_file_dialog = None  # Clear the dialog
                    if result and len(result) > 0:
                        # Process the selected INI file
                        self.annotations.load_ini(result[0])
            except Exception as e:
                self.logger.error(f"Error processing INI file dialog result: {e}")
                self.ini_file_dialog = None  # Clear the dialog on error

        # Check map file dialog
        if self.map_file_dialog is not None:
            try:
                if self.map_file_dialog.ready():
                    result = self.map_file_dialog.result()
                    self.map_file_dialog = None  # Clear the dialog
                    if result and len(result) > 0:
                        # Update the map selection dialog path with the selected file
                        self.map_selection_dialog_path = result[0]
            except Exception as e:
                self.logger.error(f"Error processing map file dialog result: {e}")
                self.map_file_dialog = None  # Clear the dialog on error

    def cancel_file_dialogs(self):
        """Cancel any active file dialogs."""
        self.ini_file_dialog = None
        self.map_file_dialog = None

    def open_context_menu(self):
        """
        Set the track for the context menu.
        """
        self.flag_open_context_menu = True

    def update(self):
        self.impl.process_inputs()
        self._fps_history.append(self._fps)
        self._fps_history.pop(0)

        self._frame_time_history.append(self._frame_time)  # Keep as float
        self._frame_time_history.pop(0)

        self._cpu_frame_time_history.append(self._cpu_frame_time)  # Keep as float
        self._cpu_frame_time_history.pop(0)

        # Check for completed file dialogs
        self.check_file_dialogs()

        imgui.new_frame()

        # Setup dockspace
        self._setup_dockspace()

        self.ui_main_menu()
        self.ui_bottom_bar()
        self.map_selection_dialog()
        self.fps_counter()
        self.settings_window()
        self.server_window()
        self.notepad_window()
        self.debug_window()
        self.track_labels_window()
        self.layers_window()
        self.context_menu()
        self.callsign_change_modal()
        self.scale_indicator_window()
        self.track_info_window()
        self.tacview_colors_window()
        self.contact_color_window()

        self.display_data.labels_renderer.render()

    def _setup_dockspace(self):
        """Setup the main dockspace for docking windows."""
        # Create a fullscreen window for the dockspace, but leave space for bottom bar
        viewport = imgui.get_main_viewport()
        bottom_bar_height = 50  # Height of the bottom bar

        # Position dockspace to cover the viewport except for the bottom bar
        imgui.set_next_window_pos(viewport.work_pos)
        dockspace_size = imgui.ImVec2(viewport.work_size.x, viewport.work_size.y - bottom_bar_height)
        imgui.set_next_window_size(dockspace_size)

        # Window flags for the dockspace window - combine using values
        window_flags = (imgui.WindowFlags_.no_title_bar.value | imgui.WindowFlags_.no_collapse.value
                        | imgui.WindowFlags_.no_resize.value | imgui.WindowFlags_.no_move.value
                        | imgui.WindowFlags_.no_bring_to_front_on_focus.value | imgui.WindowFlags_.no_nav_focus.value
                        | imgui.WindowFlags_.no_background.value | imgui.WindowFlags_.no_decoration.value
                        | imgui.WindowFlags_.no_docking.value)

        # Make the dockspace window completely transparent
        imgui.push_style_var(imgui.StyleVar_.window_rounding.value, 0.0)
        imgui.push_style_var(imgui.StyleVar_.window_border_size.value, 0.0)
        imgui.push_style_var(imgui.StyleVar_.window_padding.value, imgui.ImVec2(0.0, 0.0))
        imgui.push_style_color(imgui.Col_.window_bg.value, imgui.ImVec4(0.0, 0.0, 0.0, 0.0))  # Fully transparent

        imgui.begin("DockSpace", None, window_flags)
        imgui.pop_style_var(3)
        imgui.pop_style_color(1)

        # Create the dockspace with pass-through flag to allow clicking through
        dockspace_flags = (imgui.DockNodeFlags_.none.value | imgui.DockNodeFlags_.passthru_central_node.value)
        # Optional: Disable the central node to prevent docking in the center
        # dockspace_flags |= imgui.DockNodeFlags_.no_docking_in_central_node.value

        dockspace_id = imgui.get_id("MainDockSpace")
        imgui.dock_space(dockspace_id, imgui.ImVec2(0.0, 0.0), dockspace_flags)

        # Render polar coordinates overlay next to cursor when not over UI
        self._render_bullseye_polar_coordinates()

        imgui.end()

    def track_info_window(self):

        # Track Information Window
        if self.track_info_window_open:
            imgui.set_next_window_size_constraints(imgui.ImVec2(250, 420), imgui.ImVec2(float('inf'), float('inf')))
            result = imgui.begin("Track Information", self.track_info_window_open)
            expanded = result[0] if isinstance(result, tuple) else result
            if len(result) > 1 and result[1] is not None:
                self.track_info_window_open = result[1]

            if expanded:

                if self.most_recent_context_object:
                    obj = self.most_recent_context_object
                    imgui.text(f"Selected Track: {obj.get_display_name()}")
                    imgui.text(f"Callsign: {obj.CallSign}")
                    imgui.text(f"Type: {obj.Name}")
                    imgui.text(f"Pilot: {obj.Pilot}")
                    imgui.text(f"Altitude: {(obj.Altitude * METERS_TO_FT):.0f}")
                    
                    # Apply magnetic variation to heading if magnetic north is enabled
                    heading = (obj.Heading + 360) % 360
                    use_magnetic_north = config.app_config.get_bool("navigation", "use_magnetic_north")
                    if use_magnetic_north:
                        mag_var_deg = config.app_config.get_float("navigation", "magnetic_variation_deg")
                        mag_heading = (heading - mag_var_deg) % 360
                        imgui.text(f"Heading: {heading:.0f} / {mag_heading:.0f} M")
                    else:
                        imgui.text(f"Heading: {heading:.0f}")
                    imgui.text(f"Mach: {obj.Mach:.2f}")
                    imgui.text(f"CAS: {(obj.CAS * M_PER_SEC_TO_KNOTS):.0f}")
                    imgui.text(f"Fuel: {obj.FuelWeight:.0f}")
                    imgui.text(f"AOA: {obj.AOA:.2f}")
                    # imgui.text(f"Gforce:") # These only work for local clients
                    # imgui.text(f" - Vertical: {obj.VerticalGForce:.2f}")
                    # imgui.text(f" - Lateral: {obj.LateralGForce:.2f}")
                    # imgui.text(f" - Longitudinal: {obj.LongitudinalGForce:.2f}")
                    imgui.text(f"Coalition: {obj.Coalition}")
                    imgui.text(f"Latitude: {obj.Latitude:.6f}")
                    imgui.text(f"Longitude: {obj.Longitude:.6f}")
                    imgui.text(f"Locked Targets: ")
                    if len(obj.locked_target_objs) == 0:
                        imgui.text("   None")
                    for target in obj.locked_target_objs:
                        if target is not None:
                            imgui.text(f" - {target.get_display_name()}")

                else:
                    imgui.text("No track selected")
                    imgui.text_disabled("Right-click on a track to select it")

            imgui.end()

    def tacview_colors_window(self):
        """Window for editing Tacview coalition colors."""
        if not self.tacview_colors_window_open:
            return

        result = imgui.begin("Tacview Display Colors", self.tacview_colors_window_open)
        expanded = result[0] if isinstance(result, tuple) else result
        if len(result) > 1 and result[1] is not None:
            self.tacview_colors_window_open = result[1]

        if expanded:
            imgui.text("Edit Tacview Coalition Colors")
            imgui.separator()

            # Define the color names in the order they appear in config
            color_names = ["White", "Green", "Blue", "Brown", "Orange", "Yellow", "Red", "Black"]

            for color_name in color_names:
                try:
                    # Get current color from config
                    current_color = config.app_config.get_color_rgba("tacview_colors", color_name)
                    # Convert to list for imgui
                    color_rgba = list(current_color)

                    # Create color editor
                    changed, new_color = imgui.color_edit4(f"{color_name}##color_{color_name}", color_rgba)

                    if changed:
                        # Update config with new color - ensure it's a 4-element tuple
                        if len(new_color) >= 4:
                            color_tuple = (float(new_color[0]), float(new_color[1]), float(new_color[2]),
                                           float(new_color[3]))
                            config.app_config.set_color_rgba("tacview_colors", color_name, color_tuple)

                            # Refresh render arrays to show color changes immediately
                            if self.render_refresh_callback:
                                self.render_refresh_callback()

                except (KeyError, ValueError) as e:
                    imgui.text(f"Error loading {color_name}: {e}")

            imgui.separator()
            if imgui.button("Reset to Defaults"):
                # Reset all colors to defaults from defaults.toml
                try:
                    defaults = config.app_config.config_defaults.get("tacview_colors", {})
                    for color_name in color_names:
                        if color_name in defaults:
                            default_color = tuple(defaults[color_name])
                            config.app_config.set_color_rgba("tacview_colors", color_name, default_color)

                    # Refresh render arrays after resetting all colors
                    if self.render_refresh_callback:
                        self.render_refresh_callback()

                except Exception as e:
                    imgui.text(f"Error resetting colors: {e}")

        imgui.end()

    def contact_color_window(self):
        """Window for changing individual contact colors."""
        if not self.contact_color_window_open:
            return

        result = imgui.begin("Change Contact Color", self.contact_color_window_open)
        expanded = result[0] if isinstance(result, tuple) else result
        if len(result) > 1 and result[1] is not None:
            self.contact_color_window_open = result[1]

        if expanded:
            obj = self.most_recent_context_object
            if not obj:
                imgui.text("No contact selected")
                imgui.end()
                return

            imgui.text(f"Changing color for: {obj.get_display_name()}")
            imgui.separator()

            # Color editor
            imgui.text("New Color:")
            changed, new_color = imgui.color_edit4("##color_picker", self.current_contact_color,
                                                   imgui.ColorEditFlags_.alpha_preview_half.value)

            if changed:
                self.current_contact_color = list(new_color)
                obj.override_color = tuple(new_color)  # type: ignore

            imgui.separator()

            # Side/Coalition color swatches
            imgui.text("Coalition Colors:")
            color_names = ["White", "Green", "Blue", "Brown", "Orange", "Yellow", "Red", "Black"]

            # Create a grid of color swatches
            columns = 4
            for i, color_name in enumerate(color_names):
                if i > 0 and i % columns != 0:
                    imgui.same_line()

                try:
                    coalition_color = config.app_config.get_color_rgba("tacview_colors", color_name)
                    if imgui.color_button(f"##coalition_{color_name}", list(coalition_color),
                                          imgui.ColorEditFlags_.no_border.value, imgui.ImVec2(30, 30)):
                        self.current_contact_color = list(coalition_color)
                        obj.override_color = tuple(coalition_color)  # type: ignore

                    # Tooltip with color name
                    if imgui.is_item_hovered():
                        imgui.set_tooltip(color_name)

                except (KeyError, ValueError):
                    pass

            imgui.separator()

            # Custom colors section
            if self.custom_colors:
                imgui.text("Recently Used Colors:")
                for i, custom_color in enumerate(self.custom_colors):
                    if i > 0 and i % columns != 0:
                        imgui.same_line()

                    if imgui.color_button(f"##custom_{i}", list(custom_color), imgui.ColorEditFlags_.no_border.value,
                                          imgui.ImVec2(30, 30)):
                        self.current_contact_color = list(custom_color)
                        obj.override_color = tuple(custom_color)  # type: ignore

                imgui.separator()

            # Buttons
            if imgui.button("Accept", imgui.ImVec2(80, 0)):
                self.contact_color_window_open = False

                if self.current_contact_color not in self.custom_colors and self.current_contact_color is not None:
                    self.custom_colors.append(self.current_contact_color)

            imgui.same_line()

            if imgui.button("Reset", imgui.ImVec2(80, 0)):
                # Reset to original color (remove override)
                obj.override_color = None
                self.contact_color_window_open = False

            imgui.same_line()

            if imgui.button("Cancel", imgui.ImVec2(80, 0)):
                self.contact_color_window_open = False

        imgui.end()

    def ui_main_menu(self):

        if imgui.begin_main_menu_bar():

            # File Dropdown
            if imgui.begin_menu('File', True):
                # Map submenu
                if imgui.begin_menu('Map', True):
                    # submenu
                    if imgui.begin_menu('Load', True):
                        self.map_list_menu()
                        if imgui.menu_item('Custom', '', False, True)[0]:
                            self.map_selection_dialog_open = True
                        imgui.end_menu()

                    if imgui.menu_item('Clear', '', False, True)[0]:
                        self.map_gl.clear_map()

                    imgui.end_menu()

                # Ini submenu
                if imgui.begin_menu('Ini', True):
                    if imgui.menu_item('Load', "", False, True)[0]:
                        # Start the non-blocking file dialog
                        self.open_ini_file_dialog()
                    if imgui.menu_item('Clear', '', False, True)[0]:
                        self.annotations.clear()
                    imgui.end_menu()

                if imgui.menu_item('Settings', "", self.settings_window_open, True)[0]:
                    self.settings_window_open = not self.settings_window_open

                imgui.end_menu()

            # Windows Dropdown
            if imgui.begin_menu('Windows', True):
                if imgui.menu_item('Server', '', self.server_window_open, True)[0]:
                    self.server_window_open = not self.server_window_open
                if imgui.menu_item('Layers', '', self.layers_window_open, True)[0]:
                    self.layers_window_open = not self.layers_window_open
                if imgui.menu_item('Notepad', '', self.notepad_window_open, True)[0]:
                    self.notepad_window_open = not self.notepad_window_open
                if imgui.menu_item('Track Labels', '', self.track_labels_window_open, True)[0]:
                    self.track_labels_window_open = not self.track_labels_window_open
                if imgui.menu_item('Scale Indicator', '', self.scale_indicator_window_open, True)[0]:
                    self.scale_indicator_window_open = not self.scale_indicator_window_open

                imgui.separator()

                if imgui.menu_item('Track Information', '', self.track_info_window_open, True)[0]:
                    self.track_info_window_open = not self.track_info_window_open
                if imgui.menu_item('Debug', '', self.debug_window_open, True)[0]:
                    self.debug_window_open = not self.debug_window_open
                if imgui.menu_item('FPS', '', self.fps_window_open, True)[0]:
                    self.fps_window_open = not self.fps_window_open

                imgui.end_menu()

            imgui.end_main_menu_bar()

    def map_list_menu(self):
        maps = self.map_gl.list_maps()
        for theatre, data in maps.items():
            if imgui.begin_menu(theatre, True):
                for map_entry in data["maps"]:
                    if imgui.menu_item(map_entry["style"], "", False, True)[0]:
                        self.map_gl.load_map(map_entry["path"], data["theatre_size_km"])
                imgui.end_menu()

    def map_selection_dialog(self):

        if self.map_selection_dialog_open:
            imgui.open_popup("Map Selection")

            # Get both the expanded state and the open state from begin_popup_modal
            modal_result = imgui.begin_popup_modal("Map Selection", True)
            expanded = modal_result[0]

            # Check if the modal was closed via the X button
            if len(modal_result) > 1 and modal_result[1] is not None:
                if not modal_result[1]:  # X button was clicked
                    self.map_selection_dialog_open = False
                    imgui.close_current_popup()

            if expanded:
                # Create input text field with folder path
                _, self.map_selection_dialog_path = imgui.input_text("##mapfiledialog", self.map_selection_dialog_path,
                                                                     imgui.InputTextFlags_.read_only.value)

                # Button to select map file
                imgui.same_line()
                if imgui.button("Select Map Image"):
                    # Start the non-blocking file dialog for map image
                    self.open_map_file_dialog()

                sizes = ["1024", "2048"]
                _, self.map_selection_dialog_size = imgui.combo("Theatre Size (km)", self.map_selection_dialog_size,
                                                                sizes)

                # Buttons row
                if imgui.button("Confirm"):
                    self.map_gl.load_map(self.map_selection_dialog_path, int(sizes[self.map_selection_dialog_size]))
                    self.map_selection_dialog_open = False
                    imgui.close_current_popup()

                imgui.same_line()

                if imgui.button("Cancel"):
                    self.map_selection_dialog_open = False
                    imgui.close_current_popup()

                imgui.end_popup()

    def ui_bottom_bar(self):

        bottom_flags = (imgui.WindowFlags_.no_resize.value | imgui.WindowFlags_.no_move.value
                        | imgui.WindowFlags_.no_title_bar.value | imgui.WindowFlags_.no_collapse.value)
        width = imgui.get_io().display_size[0]
        height = 50

        imgui.set_next_window_size(imgui.ImVec2(width, height))
        imgui.set_next_window_pos(imgui.ImVec2(0, imgui.get_io().display_size[1] - height))
        if imgui.begin("Bottom Bar", True, flags=bottom_flags):
            TextCentered(self._time.strftime("%H:%M:%SZ"))
            imgui.end()

    def fps_counter(self):
        if not self.fps_window_open:
            return
        _, open = imgui.begin("FPS", True)

        display_samples = 1000
        avg_samples = 1000

        fps_history = np.array(self._fps_history[-display_samples:], np.float32)
        imgui.plot_lines("FPS", fps_history, graph_size=(0, 128))

        # HACK: Calculate average only over valid samples (non-zero values from the end)
        fps_array = np.array(self._fps_history[-avg_samples:])
        fps_nonzero_mask = fps_array > 0
        fps_avg = np.mean(fps_array[fps_nonzero_mask]) if np.any(fps_nonzero_mask) else 0.0

        imgui.text(f"FPS: avg {fps_avg:6.2f} | cur {self.fps:6.2f}")

        # GPU Frame Time
        frame_time_history = np.array(self._frame_time_history[-display_samples:], np.float32)
        imgui.plot_lines("GPU Render Time (us)", frame_time_history, graph_size=(0, 128))

        gpu_array = np.array(self._frame_time_history[-avg_samples:])
        gpu_nonzero_mask = gpu_array > 0
        gpu_avg = np.mean(gpu_array[gpu_nonzero_mask]) if np.any(gpu_nonzero_mask) else 0.0

        imgui.text(f"GPU: avg {gpu_avg:7.1f} | cur {self._frame_time:7.1f} us")

        # CPU Frame Processing Time
        cpu_frame_time_history = np.array(self._cpu_frame_time_history[-display_samples:], np.float32)
        imgui.plot_lines("CPU Frame Process Time (us)", cpu_frame_time_history, graph_size=(0, 128))

        cpu_array = np.array(self._cpu_frame_time_history[-avg_samples:])
        cpu_nonzero_mask = cpu_array > 0
        cpu_avg = np.mean(cpu_array[cpu_nonzero_mask]) if np.any(cpu_nonzero_mask) else 0.0

        imgui.text(f"CPU: avg {cpu_avg:7.1f} | cur {self._cpu_frame_time:7.1f} us")

        imgui.end()

        if not open:
            self.fps_window_open = False

    def settings_window(self):

        if not self.settings_window_open:
            return

        _, open = imgui.begin("Settings", True, imgui.WindowFlags_.always_auto_resize.value)
        if imgui.begin_tab_bar("Settings Tabs"):
            if imgui.begin_tab_item("Map")[0]:
                self.settings_tab_map()
                imgui.end_tab_item()
            if imgui.begin_tab_item("Annotations")[0]:
                self.settings_tab_annotations()
                imgui.end_tab_item()
            if imgui.begin_tab_item("Radar")[0]:
                self.settings_tab_radar()
                imgui.end_tab_item()
            if imgui.begin_tab_item("Display")[0]:
                self.settings_tab_display()
                imgui.end_tab_item()
            imgui.end_tab_bar()
        imgui.end()

        if not open:
            self.logger.info("Settings window closed, Saving settings")
            self.settings_window_open = False
            config.app_config.save()

    def settings_tab_map(self):
        map_alpha = config.app_config.get_int("map", "map_alpha")
        map_background_color = config.app_config.get_color_normalized("map", "background_color")
        use_magnetic_north = config.app_config.get_bool("navigation", "use_magnetic_north")

        create_color_edit("Background Color", map_background_color, "map", "background_color")
        imgui.same_line()
        imgui.text_disabled("(?)")
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text_unformatted("Click on the color square to open a color picker.\n"
                                   "CTRL+click on individual component to input value.\n")
            imgui.end_tooltip()

        create_slider_int("Map Alpha", map_alpha, 0, 255, "map", "map_alpha")
        
        imgui.separator()
        imgui.text("Navigation Reference")
        create_checkbox("Use Magnetic North", use_magnetic_north, "navigation", "use_magnetic_north")
        imgui.same_line()
        imgui.text_disabled("(?)")
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text_unformatted("When enabled, all bearings and headings will be referenced to magnetic north.\n"
                                   "When disabled, bearings will be referenced to true/grid north.")
            imgui.end_tooltip()
        
        # Show current magnetic variation
        current_variation = self.map_gl.get_current_magnetic_variation()
        current_theatre = self.map_gl.get_current_theatre()
        
        if current_theatre:
            imgui.text(f"Theatre: {current_theatre}")
            if current_variation >= 0:
                imgui.text(f"Magnetic Variation: {current_variation:.1f}° E")
            else:
                imgui.text(f"Magnetic Variation: {abs(current_variation):.1f}° W")
        else:
            imgui.text("Theatre: Custom/Unknown")
            default_variation = config.app_config.get_float("navigation", "magnetic_variation_deg")
            if default_variation >= 0:
                imgui.text(f"Magnetic Variation: {default_variation:.1f}° E (default)")
            else:
                imgui.text(f"Magnetic Variation: {abs(default_variation):.1f}° W (default)")
        
        imgui.separator()
        imgui.text("Map Size")

    def settings_tab_annotations(self):
        ini_width = config.app_config.get_int("annotations", "ini_width")
        ini_color = config.app_config.get_color_normalized("annotations", "ini_color")
        ini_font_scale = config.app_config.get_float("annotations", "ini_font_scale")

        create_color_edit("Ini Color", ini_color, "annotations", "ini_color")
        create_slider_int("Ini Line Width", ini_width, 1, 40, "annotations", "ini_width")
        create_slider_float("Ini Font Scale", ini_font_scale, 20, 100, "annotations", "ini_font_scale")

    def settings_tab_radar(self):
        stoke_width = config.app_config.get_float("radar", "contact_stroke")
        shape_size = config.app_config.get_float("radar", "contact_size")
        font_scale = config.app_config.get_int("radar", "contact_font_scale")
        label_padding = config.app_config.get_int("radar", "contact_label_padding")
        center_point_size = config.app_config.get_float("radar", "center_point_size")
        update_interval = config.app_config.get_float("radar", "update_interval")
        bullseye_num_rings = config.app_config.get_int("radar", "bullseye_num_rings")
        bullseye_ring_distance = config.app_config.get_int("radar", "bullseye_ring_distance")

        changed = False

        stroke_changed, _ = create_slider_float("Contact Stroke Width", stoke_width, 1, 10.0, "radar", "contact_stroke")
        if stroke_changed:
            changed = True
        size_changed, _ = create_slider_float("Contact Shape Size", shape_size, 1, 40.0, "radar", "contact_size")
        if size_changed:
            changed = True
        font_changed, _ = create_slider_int("Contact Font Scale", font_scale, 10, 100, "radar", "contact_font_scale")
        if font_changed:
            changed = True
        padding_changed, _ = create_slider_int("Contact Label Padding", label_padding, 0, 20, "radar",
                                               "contact_label_padding")
        if padding_changed:
            changed = True
        center_changed, _ = create_slider_float("Center Point Size", center_point_size, 0, 6.0, "radar",
                                                "center_point_size")
        if center_changed:
            changed = True

        imgui.separator()
        create_slider_float("Radar Update Interval", update_interval, 0.0, 5.0, "radar", "update_interval")
        imgui.separator()

        # Refresh render arrays if contact settings changed
        if changed:
            if self.render_refresh_callback:
                self.render_refresh_callback()

        # Bullseye configuration section
        imgui.text("Bullseye Display Settings")
        changed_rings, _ = create_slider_int("Number of Rings", bullseye_num_rings, 1, 20, "radar",
                                             "bullseye_num_rings")
        changed_distance, _ = create_slider_int("Ring Distance (NM)", bullseye_ring_distance, 5, 100, "radar",
                                                "bullseye_ring_distance")

        # Refresh render arrays if bullseye settings changed
        if changed_rings or changed_distance:
            if self.render_refresh_callback:
                self.render_refresh_callback()

        imgui.separator()
        if imgui.button("Change Coalition Display Colors"):
            self.tacview_colors_window_open = True

    def settings_tab_display(self):
        # Make sure MSAA samples are one of the valid predefined values
        if (config.app_config.get_int("display", "msaa_samples") not in (4, 8, 16)):
            config.app_config.set("display", "msaa_samples", 4)

        imgui.text("MSAA (requires restart)")
        create_checkbox("Enable MSAA", config.app_config.get_bool("display", "msaa_enabled"), "display", "msaa_enabled")
        imgui.same_line()
        imgui.text_disabled("(?)")
        imgui.same_line()
        if imgui.radio_button("MSAA 4x", config.app_config.get_int("display", "msaa_samples") == 4):
            config.app_config.set("display", "msaa_samples", 4)
        imgui.same_line()
        if imgui.radio_button("MSAA 8x", config.app_config.get_int("display", "msaa_samples") == 8):
            config.app_config.set("display", "msaa_samples", 8)
        imgui.same_line()
        if imgui.radio_button("MSAA 16x", config.app_config.get_int("display", "msaa_samples") == 16):
            config.app_config.set("display", "msaa_samples", 16)
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text_unformatted("Enable Multi-Sample Anti-Aliasing (MSAA) for smoother edges.")
            imgui.end_tooltip()

    def layers_window(self):
        if not self.layers_window_open:
            return

        show_bullseye = config.app_config.get_bool("layers", "show_bullseye")
        show_fixed_wing = config.app_config.get_bool("layers", "show_fixed_wing")
        show_rotary_wing = config.app_config.get_bool("layers", "show_rotary_wing")
        show_ground = config.app_config.get_bool("layers", "show_ground")
        show_ships = config.app_config.get_bool("layers", "show_ships")
        show_missiles = config.app_config.get_bool("layers", "show_missiles")
        show_lock_lines = config.app_config.get_bool("layers", "show_lock_lines")

        _, open = imgui.begin("Layers", True, imgui.WindowFlags_.always_auto_resize.value)

        imgui.text("Enabled Map Layers")

        # Check if any layer visibility changed using the helper functions
        changed_bullseye, _ = create_checkbox("Bullseye", show_bullseye, "layers", "show_bullseye")
        changed_fixed_wing, _ = create_checkbox("Fixed Wing", show_fixed_wing, "layers", "show_fixed_wing")
        changed_rotary_wing, _ = create_checkbox("Rotary Wing", show_rotary_wing, "layers", "show_rotary_wing")
        changed_ground, _ = create_checkbox("Ground", show_ground, "layers", "show_ground")
        changed_ships, _ = create_checkbox("Ships", show_ships, "layers", "show_ships")
        changed_missiles, _ = create_checkbox("Missiles", show_missiles, "layers", "show_missiles")
        changed_lock_lines, _ = create_checkbox("Lock Lines", show_lock_lines, "layers", "show_lock_lines")

        # If any layer visibility changed, regenerate render arrays
        if any([
                changed_bullseye, changed_fixed_wing, changed_rotary_wing, changed_ground, changed_ships,
                changed_missiles, changed_lock_lines
        ]):
            if self.render_refresh_callback:
                self.render_refresh_callback()

        imgui.end()

        if not open:
            self.layers_window_open = False
            config.app_config.save()

    def server_window(self):
        if not self.server_window_open:
            return

        connected = False

        status, description = self.data_client.get_status()
        if status in [ThreadState.CONNECTED, ThreadState.CONNECTING]:
            connected = True

        _, open = imgui.begin("Server", True, imgui.WindowFlags_.always_auto_resize.value)

        if connected:
            imgui.begin_disabled()

        address_changed, address = imgui.input_text("Address##server_address",
                                                    config.app_config.get_str("server", "address"))

        port_changed, port = imgui.input_int("Port##server_port", config.app_config.get_int("server", "port"))
        imgui.same_line()
        if imgui.button("Default"):  # TODO: width 80?
            config.app_config.set_default("server", "port")

        pw_changed, password = imgui.input_text("Password##server_password", self.server_password)

        retries_changed, retries = imgui.input_int("Retries", config.app_config.get_int("server", "retries"))

        # TODO: Implement autoconnect
        # autoconnect = create_checkbox("Autoconnect", config.app_config.get_bool("server", "autoconnect"), "server",
        #                               "autoconnect")

        if connected:
            imgui.end_disabled()

        imgui.text("Status: ")
        imgui.same_line()

        imgui.text(f"{status.status_msg}  {description}")

        if imgui.button("Connect"):
            if self.reset_state_callback:
                self.reset_state_callback()
            self.data_client.connect(address, port, password, retries)
        imgui.same_line()
        if imgui.button("Disconnect"):
            self.data_client.disconnect()
            if self.reset_state_callback:
                self.reset_state_callback()
        imgui.end()

        if address_changed:
            config.app_config.set("server", "address", address)
        if port_changed:
            config.app_config.set("server", "port", port)
        if pw_changed:
            self.server_password = password
        if retries_changed:
            config.app_config.set("server", "retries", retries)

        if not open:
            self.server_window_open = False
            config.app_config.save()

    def notepad_window(self):
        if not self.notepad_window_open:
            return
        imgui.set_next_window_size_constraints(imgui.ImVec2(200, 200), imgui.ImVec2(float('inf'), float('inf')))
        _, open = imgui.begin("Notepad", True)
        notes = config.app_config.get_str("notepad", "notes")

        # Get window size
        width, height = imgui.get_content_region_avail()
        changed, notes = imgui.input_text_multiline("##notepad", notes, imgui.ImVec2(width, height),
                                                    imgui.InputTextFlags_.allow_tab_input.value)
        imgui.end()

        if changed:
            config.app_config.set("notepad", "notes", notes)
        if not open:
            self.notepad_window_open = False

    def debug_window(self):
        if not self.debug_window_open:
            return
        _, open = imgui.begin("Debug", True, imgui.WindowFlags_.always_auto_resize.value)
        mouse_pos = imgui.get_mouse_pos()
        tuple_mouse_pos = (mouse_pos.x, mouse_pos.y)
        mouse_pos_world = self.scene.screen_to_world((mouse_pos.x, mouse_pos.y))
        imgui.text(f"Mouse Pos: {tuple_mouse_pos}")
        imgui.text(f"Mouse Pos (World (m)): {mouse_pos_world}")
        imgui.text(f"Mouse Pos (World (ft)): {mouse_pos_world * METERS_TO_FT}")
        imgui.text(f"Pan: {self.scene._pan_screen}")
        imgui.text(f"Zoom: {self.scene.zoom_level}")
        imgui.text(f"Map Size: {self.scene.map_size_m}")
        if imgui.button("Load test ini"):
            self.annotations.load_ini(os.path.join(os.getcwd(), "Data", "test.ini"))

        nearest_object = self.gamestate.get_nearest_object(mouse_pos_world.to_tuple())
        if nearest_object:
            imgui.text(f"Nearest Object: {nearest_object.Name} ({nearest_object.object_id})")
            imgui.text(f"Object Pilot: {nearest_object.Pilot}")
            imgui.text(f"Position (World): {nearest_object.U, nearest_object.V}")
            imgui.text(f"Position (Screen): {self.scene.world_to_screen((nearest_object.U, nearest_object.V))}")

        imgui.end()
        if not open:
            self.debug_window_open = False

    def track_labels_window(self):

        if not self.track_labels_window_open:
            return

        _, open = imgui.begin("Track Labels", True, imgui.WindowFlags_.always_auto_resize.value)

        imgui.begin_tab_bar("Track Types")
        for track_type in GameObjectType:
            if imgui.begin_tab_item(track_type.display_name)[0]:

                labels = deserialize_track_labels(track_type.name, config.app_config.get_str(
                    "labels", track_type.name))  # TODO: this may be slow, consider caching
                if labels is None:
                    self.logger.error(f"Failed to load track labels {track_type.name}")
                    raise Exception(f"Failed to load track labels for {track_type.name}")
                    labels = TrackLabels(track_type)
                imgui.text(f"Track Type: {track_type.name}")

                imgui.text("Label Location")
                imgui.same_line()
                help_marker("You can have a different label on each side of the contact."
                            "Select the square to edit the label at that cardinal direction.")
                if imgui.begin_table("Label Location Table",
                                     3,
                                     inner_width=50,
                                     flags=imgui.TableFlags_.borders.value
                                     | imgui.TableFlags_.sizing_fixed_same.value
                                     | imgui.TableFlags_.no_host_extend_x.value):

                    for i in range(3):
                        imgui.table_next_row()
                        for j in range(3):
                            if i == 1 and j == 1:
                                continue  # Dont let the middle square be selectable, # TODO make this a contact preview
                            imgui.table_set_column_index(j)

                            location = get_label_loc_by_ui_coords((i, j))
                            label_name = ""
                            selected = (self.track_labels_selected_square == (i, j))
                            if labels.labels.get(location) is not None:
                                label_name = labels.labels[location].label_name

                            if imgui.selectable(f"{label_name}##{i}{j}",
                                                selected, imgui.SelectableFlags_.no_auto_close_popups.value,
                                                imgui.ImVec2(50, 50))[0]:
                                self.track_labels_selected_square = (i, j)
                                # print(f"Selected square ({i}, {j})")
                    imgui.end_table()

                selected_coords = get_label_loc_by_ui_coords(self.track_labels_selected_square)
                selected_label = labels.labels.get(selected_coords, TrackLabel("", "", False))

                imgui.text("Label Name")
                imgui.same_line()
                help_marker("The name of the label. This is only used for your reference in the UI")
                imgui.push_item_width(50)
                changed, label_name = imgui.input_text("##LabelName", selected_label.label_name)
                imgui.pop_item_width()
                if changed:
                    selected_label.label_name = label_name
                    if selected_coords not in labels.labels:
                        labels.labels[selected_coords] = selected_label
                    config.app_config.set("labels", track_type.name, serialize_track_labels(labels)[1])

                imgui.text("Show:")
                if imgui.radio_button("Always", selected_label.show_on_hover == False):
                    selected_label.show_on_hover = False
                    if selected_coords not in labels.labels:
                        labels.labels[selected_coords] = selected_label
                    config.app_config.set("labels", track_type.name, serialize_track_labels(labels)[1])

                imgui.same_line()
                if imgui.radio_button("On Hover", selected_label.show_on_hover == True):
                    selected_label.show_on_hover = True
                    if selected_coords not in labels.labels:
                        labels.labels[selected_coords] = selected_label
                    config.app_config.set("labels", track_type.name, serialize_track_labels(labels)[1])

                imgui.text("Label Contents")
                imgui.same_line()
                help_marker("Add the text to be displayed on the label. "
                            "This can be a static string or a formatted string with variables."
                            "Valid variables include: \n" + "\n".join(get_all_attributes(example_object).keys()))

                changed, user_input = imgui.input_text("##Label Contents", selected_label.label_format)
                if changed:
                    selected_label.label_format = user_input
                    if selected_coords not in labels.labels:
                        labels.labels[selected_coords] = selected_label
                    config.app_config.set("labels", track_type.name, serialize_track_labels(labels)[1])

                imgui.text("Preview")
                imgui.text(evaluate_input_format(user_input, example_object))

                if imgui.button("Delete Label"):
                    labels.labels.pop(get_label_loc_by_ui_coords(self.track_labels_selected_square))
                    config.app_config.set("labels", track_type.name, serialize_track_labels(labels)[1])

                imgui.end_tab_item()

        imgui.end_tab_bar()
        imgui.end()
        if not open:
            self.track_labels_window_open = False
            config.app_config.save()

    # TODO handle map and ini drag-drops

    def context_menu(self):

        if self.flag_open_context_menu:
            self.flag_open_context_menu = False

            mouse_pos = imgui.get_mouse_pos()
            mouse_pos_world = self.scene.screen_to_world((mouse_pos.x, mouse_pos.y))
            if self.context_object is None:
                self.context_object = self.gamestate.get_nearest_object(mouse_pos_world.to_tuple())
                self.most_recent_context_object = self.context_object

            imgui.open_popup(f"context_popup")

        if imgui.begin_popup(f"context_popup") and self.context_object is not None:
            imgui.text(f"{self.context_object.get_display_name()}")
            imgui.separator()
            if imgui.menu_item("Change Callsign", "", False)[0]:
                # Set flag to open the callsign change modal after context menu closes
                self.callsign_modal_open = True
                imgui.close_current_popup()

            if imgui.menu_item("Change Color", "", False)[0]:
                # Open the contact color window
                self.contact_color_window_open = True
                # Initialize the color editor with current contact color
                obj = self.context_object
                if obj:
                    if obj.override_color:
                        self.current_contact_color = list(obj.override_color)
                    else:
                        self.current_contact_color = list(obj.color_rgba)
                imgui.close_current_popup()

            imgui.end_popup()
        else:
            # If the popup was not opened, reset the context track
            self.context_object = None
            self.flag_open_context_menu = False

    def callsign_change_modal(self):
        """Modal dialog for changing the callsign of a game object."""

        # Open the modal if the flag is set
        if self.callsign_modal_open:
            imgui.open_popup("Change Callsign")
            self.callsign_modal_open = False  # Reset the flag
            # Initialize input text with current object name
            obj = self.most_recent_context_object
            if obj:
                self.callsign_original_text = obj.get_display_name()
                self.callsign_input_text = obj.get_display_name()

        # Center the modal
        center = imgui.get_main_viewport().get_center()
        imgui.set_next_window_pos(center, imgui.Cond_.appearing.value, imgui.ImVec2(0.5, 0.5))
        imgui.set_next_window_size(imgui.ImVec2(300, 120))

        if imgui.begin_popup_modal("Change Callsign", True, imgui.WindowFlags_.always_auto_resize.value)[0]:
            obj = self.most_recent_context_object

            # Text input for new callsign
            imgui.text("New Callsign:")
            changed, self.callsign_input_text = imgui.input_text("##callsign_input", self.callsign_input_text)

            # Set focus to the input field when the modal first opens
            if imgui.is_window_appearing():
                imgui.set_keyboard_focus_here(-1)

            # Handle Enter key press
            enter_pressed = imgui.is_key_pressed(imgui.Key.enter)

            imgui.separator()

            # Buttons
            if imgui.button("OK", imgui.ImVec2(80, 0)) or enter_pressed:
                # Apply the callsign change
                if obj and self.callsign_input_text.strip():
                    obj.override_name = self.callsign_input_text.strip()
                imgui.close_current_popup()

            imgui.same_line()

            if imgui.button("Cancel", imgui.ImVec2(80, 0)):
                # Close the modal without saving
                imgui.close_current_popup()
            imgui.end_popup()

    def scale_indicator_window(self):
        """Scale indicator showing distance gradations at 1,2,5,10,20,50,100,200 nm"""
        if not self.scale_indicator_window_open:
            return

        # Distance gradations in nautical miles
        scale_gradations_nm = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]

        # Find the largest scale gradation that fits in a reasonable window size
        max_window_width = 300  # Maximum width for the scale indicator

        # Calculate pixels per nautical mile based on current zoom
        # Using the scene's world_to_screen_distance method
        nm_in_meters = NM_TO_METERS
        pixels_per_nm = float(self.scene.world_to_screen_distance(nm_in_meters))  # type: ignore

        # Find the largest gradation that fits within our max window width
        selected_scale_nm = 1
        for scale_nm in scale_gradations_nm:
            scale_width_pixels = scale_nm * pixels_per_nm
            if scale_width_pixels <= max_window_width - 20:  # Leave some padding
                selected_scale_nm = scale_nm
            else:
                break

        # Calculate the actual pixel width for the selected scale
        scale_width_pixels = selected_scale_nm * pixels_per_nm

        # Set window size based on the scale width plus some padding
        # window_width = max(150, float(scale_width_pixels + 40))  # Add 40px padding
        window_width = max_window_width
        window_height = 50

        # Window flags for scale indicator - invisible unless being moved
        window_flags = (imgui.WindowFlags_.no_resize.value | imgui.WindowFlags_.no_title_bar.value
                        | imgui.WindowFlags_.no_scrollbar.value | imgui.WindowFlags_.no_scroll_with_mouse.value
                        | imgui.WindowFlags_.always_auto_resize.value)

        # Position in bottom-right corner by default
        if not hasattr(self, '_scale_indicator_pos_set'):
            viewport = imgui.get_main_viewport()
            # Calculate position ensuring it stays within viewport bounds
            pos_x = max(20, float(viewport.work_pos.x + viewport.work_size.x - max_window_width))
            pos_y = max(50, float(viewport.work_pos.y + viewport.work_size.y - window_height - 60))  # Above bottom bar
            imgui.set_next_window_pos(imgui.ImVec2(pos_x, pos_y))
            self._scale_indicator_pos_set = True

        # If not being dragged, make window background transparent and remove decorations
        pushed_bg = False
        if not self.scale_indicator_hovered:
            pushed_bg = True

            imgui.push_style_color(imgui.Col_.window_bg.value, imgui.ImVec4(0.0, 0.0, 0.0, 0.0))
            imgui.push_style_color(imgui.Col_.border.value, imgui.ImVec4(0.0, 0.0, 0.0, 0.0))
            window_flags |= imgui.WindowFlags_.no_background.value

        imgui.set_next_window_size(imgui.ImVec2(float(window_width), float(window_height)))

        result = imgui.begin("Scale Indicator", self.scale_indicator_window_open, window_flags)
        window_open = result[0] if isinstance(result, tuple) else result

        if len(result) > 1 and result[1] is not None:
            self.scale_indicator_window_open = result[1]

        if window_open:
            # Get current cursor position for drawing
            cursor_pos = imgui.get_cursor_screen_pos()
            draw_list = imgui.get_window_draw_list()

            # Draw the scale line
            line_start_x = float(cursor_pos.x + 10)
            line_y = float(cursor_pos.y + 25)
            line_end_x = float(line_start_x + scale_width_pixels)

            # Colors for the lines
            white_color = imgui.get_color_u32(imgui.ImVec4(1.0, 1.0, 1.0, 1.0))
            white_transparent = imgui.get_color_u32(imgui.ImVec4(1.0, 1.0, 1.0, 0.7))

            # Draw main scale line (white)
            draw_list.add_line(imgui.ImVec2(line_start_x, line_y), imgui.ImVec2(line_end_x, line_y), white_color, 2.0)

            # Draw tick marks at start and end
            tick_height = 8
            # Start tick
            draw_list.add_line(imgui.ImVec2(line_start_x, float(line_y - tick_height // 2)),
                               imgui.ImVec2(line_start_x, float(line_y + tick_height // 2)), white_color, 2.0)
            # End tick
            draw_list.add_line(imgui.ImVec2(line_end_x, float(line_y - tick_height // 2)),
                               imgui.ImVec2(line_end_x, float(line_y + tick_height // 2)), white_color, 2.0)

            # Add intermediate tick marks for smaller subdivisions
            if selected_scale_nm >= 10:
                # For scales 10nm and above, add marks every 5nm
                subdivision = 5
                while subdivision < selected_scale_nm:
                    subdivision_pixels = (subdivision / selected_scale_nm) * scale_width_pixels
                    tick_x = float(line_start_x + subdivision_pixels)
                    draw_list.add_line(imgui.ImVec2(tick_x, float(line_y - tick_height // 4)),
                                       imgui.ImVec2(tick_x, float(line_y + tick_height // 4)), white_transparent, 1.0)
                    subdivision += 5
            elif selected_scale_nm >= 5:
                # For 5nm scale, add mark at 2.5nm
                subdivision_pixels = (2.5 / selected_scale_nm) * scale_width_pixels
                tick_x = float(line_start_x + subdivision_pixels)
                draw_list.add_line(imgui.ImVec2(tick_x, float(line_y - tick_height // 4)),
                                   imgui.ImVec2(tick_x, float(line_y + tick_height // 4)), white_transparent, 1.0)
            elif selected_scale_nm == 2:
                # For 2nm scale, add mark at 1nm
                subdivision_pixels = (1.0 / selected_scale_nm) * scale_width_pixels
                tick_x = float(line_start_x + subdivision_pixels)
                draw_list.add_line(imgui.ImVec2(tick_x, float(line_y - tick_height // 4)),
                                   imgui.ImVec2(tick_x, float(line_y + tick_height // 4)), white_transparent, 1.0)

            # Draw text labels
            imgui.set_cursor_pos(imgui.ImVec2(10, 5))
            imgui.text("0")

            # Position the end label
            text_width = imgui.calc_text_size(f"{selected_scale_nm} nm").x
            imgui.set_cursor_pos(imgui.ImVec2(float(10 + scale_width_pixels - text_width), 5))
            imgui.text(f"{selected_scale_nm} nm")

        # Check if the window is being dragged - if so, show frame and title
        self.scale_indicator_hovered = (_in_bounds(imgui.get_mouse_pos(), imgui.get_window_pos(),
                                                   imgui.get_window_size())
                                        and imgui.is_mouse_dragging(imgui.MouseButton_.left.value))

        imgui.end()

        # Pop style colors if they were pushed
        if pushed_bg:
            imgui.pop_style_color(2)

    def _render_bullseye_polar_coordinates(self):
        """Render polar coordinates (bearing/range) relative to bullseye next to mouse cursor"""
        # Check if mouse is over any UI element
        io = imgui.get_io()
        if io.want_capture_mouse:
            return  # Don't show when mouse is over UI

        # Get current mouse position
        mouse_pos = imgui.get_mouse_pos()
        mouse_world_pos = self.scene.screen_to_world((mouse_pos.x, mouse_pos.y))

        # Handle BRAA line logic
        left_mouse_pressed = imgui.is_mouse_clicked(imgui.MouseButton_.left.value)
        left_mouse_down = imgui.is_mouse_down(imgui.MouseButton_.left.value)
        left_mouse_released = imgui.is_mouse_released(imgui.MouseButton_.left.value)

        # Start BRAA line on left mouse press
        if left_mouse_pressed and not self.braa_active:
            self.braa_active = True
            self.braa_start_world = mouse_world_pos.to_tuple()
            self.braa_start_screen = (mouse_pos.x, mouse_pos.y)

        # End BRAA line on left mouse release
        if left_mouse_released and self.braa_active:
            self.braa_active = False
            self.braa_start_world = None
            self.braa_start_screen = None

        # Determine coordinate reference point and colors
        if self.braa_active and self.braa_start_world:
            # BRAA mode: reference from start point
            reference_pos = self.braa_start_world
            coord_color = imgui.ImVec4(1.0, 0.5, 0.0, 1.0)  # Orange for BRAA
            bg_color = imgui.ImVec4(0.2, 0.1, 0.0, 0.8)  # Dark orange background

            # Draw BRAA line from start to current mouse position
            self._draw_braa_line()
        else:
            # Normal bullseye mode
            bullseye_pos = self.gamestate.get_bullseye_pos()
            if bullseye_pos == (0, 0):
                return  # No bullseye available
            reference_pos = bullseye_pos
            coord_color = imgui.ImVec4(1.0, 1.0, 1.0, 1.0)  # White for bullseye
            bg_color = imgui.ImVec4(0.0, 0.0, 0.0, 0.7)  # Dark background

        # Calculate polar coordinates relative to reference point
        from util.bms_math import world_distance, world_bearing
        distance_nm = world_distance(reference_pos, mouse_world_pos.to_tuple())
        bearing_deg = world_bearing(reference_pos, mouse_world_pos.to_tuple())

        # When magnetic north is enabled, the bullseye visual is already rotated to show magnetic north,
        # so we need to adjust the calculated bearing to account for this visual rotation
        use_magnetic_north = config.app_config.get_bool("navigation", "use_magnetic_north")
        if use_magnetic_north:
            mag_var_deg = config.app_config.get_float("navigation", "magnetic_variation_deg")
            # Subtract magnetic variation because the visual reference is already rotated
            bearing_deg = (bearing_deg - mag_var_deg) % 360

        # Format the coordinates (3-digit bearing, range in NM)
        bearing_str = f"{bearing_deg:03.0f}°"
        range_str = f"{distance_nm:.0f} NM"
        coord_text = f"{bearing_str} {range_str}"

        # Create an invisible window positioned next to the cursor
        offset_x, offset_y = 15, -10  # Offset from cursor to avoid blocking view
        window_pos = imgui.ImVec2(float(mouse_pos.x + offset_x), float(mouse_pos.y + offset_y))

        # Ensure the window stays within viewport bounds
        viewport = imgui.get_main_viewport()
        text_size = imgui.calc_text_size(coord_text)
        max_x = viewport.work_pos.x + viewport.work_size.x - text_size.x - 10
        max_y = viewport.work_pos.y + viewport.work_size.y - text_size.y - 10

        window_pos.x = min(max(window_pos.x, viewport.work_pos.x + 10), max_x)
        window_pos.y = min(max(window_pos.y, viewport.work_pos.y + 10), max_y)

        imgui.set_next_window_pos(window_pos)
        imgui.set_next_window_size(imgui.ImVec2(0, 0))  # Auto-size

        # Window flags for overlay - no interaction, no decoration
        window_flags = (imgui.WindowFlags_.no_title_bar.value | imgui.WindowFlags_.no_resize.value
                        | imgui.WindowFlags_.no_move.value | imgui.WindowFlags_.no_scrollbar.value
                        | imgui.WindowFlags_.no_scroll_with_mouse.value | imgui.WindowFlags_.always_auto_resize.value
                        | imgui.WindowFlags_.no_background.value | imgui.WindowFlags_.no_focus_on_appearing.value
                        | imgui.WindowFlags_.no_bring_to_front_on_focus.value | imgui.WindowFlags_.no_inputs.value)

        # Semi-transparent background for better text readability
        imgui.push_style_color(imgui.Col_.window_bg.value, bg_color)
        imgui.push_style_color(imgui.Col_.text.value, coord_color)

        if imgui.begin("Bullseye Coordinates", None, window_flags):
            imgui.text(coord_text)
        imgui.end()

        imgui.pop_style_color(2)

    def _draw_braa_line(self):
        """Draw BRAA line from start point to current mouse position"""
        if not self.braa_active or not self.braa_start_world:
            return

        # Get current mouse position in world coordinates
        mouse_pos = imgui.get_mouse_pos()
        mouse_world_pos = self.scene.screen_to_world((mouse_pos.x, mouse_pos.y))

        # Convert world positions to screen coordinates for drawing
        start_screen = self.scene.world_to_screen(self.braa_start_world)
        end_screen = self.scene.world_to_screen(mouse_world_pos.to_tuple())

        # Get the dockspace window's draw list to draw on the main viewport
        viewport = imgui.get_main_viewport()
        draw_list = imgui.get_foreground_draw_list()

        # Line color (orange for BRAA)
        line_color = imgui.get_color_u32(imgui.ImVec4(1.0, 0.5, 0.0, 0.8))

        # Draw the line
        draw_list.add_line(
            imgui.ImVec2(float(start_screen[0]), float(start_screen[1])),
            imgui.ImVec2(float(end_screen[0]), float(end_screen[1])),
            line_color,
            2.0  # Line thickness
        )

        # Draw start point marker (small circle)
        start_marker_color = imgui.get_color_u32(imgui.ImVec4(1.0, 0.2, 0.0, 1.0))
        draw_list.add_circle_filled(
            imgui.ImVec2(float(start_screen[0]), float(start_screen[1])),
            4.0,  # Radius
            start_marker_color)
