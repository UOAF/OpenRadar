"""
ImGuiRadarLabelsRenderer - A new ImGui-based implementation for rendering radar track labels.

This class uses ImGui for text rendering instead of OpenGL/MSDF, providing:
- Better text quality and performance
- Easier text styling and formatting
- Built-in caching through ImGui's system
- Integration with the existing dockspace window
"""

import numpy as np
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
import hashlib

from imgui_bundle import imgui
from draw.scene import Scene
from game_object import GameObject
from game_object_types import GameObjectType
from game_state import GameState
from sensor_tracks import Track
from util.track_labels import (TrackLabelLocation, TrackLabels, get_labels_for_class_type, evaluate_input_format)
from util.bms_math import NM_TO_METERS

import config


@dataclass
class CachedTextLabel:
    """
    Represents a cached text label with position and content information.
    """
    text: str
    x_screen: float
    y_screen: float
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    font_scale: float = 1.0
    location: TrackLabelLocation = TrackLabelLocation.CENTER
    # Hash of the text content to detect changes
    content_hash: str = ""
    # Object ID to track which object this label belongs to
    object_id: str = ""


class ImGuiRadarLabelsRenderer:
    """
    ImGui-based radar labels renderer with intelligent caching.
    
    This class provides:
    - ImGui text rendering for better quality and performance
    - Content-based caching - text is only recomputed when it changes
    - Position-only updates when text content remains the same
    - Integration with the transparent dockspace window
    """

    def __init__(self, scene: Scene):
        """
        Initialize the ImGuiRadarLabelsRenderer.
        
        Args:
            scene: The Scene object containing rendering context and camera information
        """
        self.scene = scene

        # Cache for text labels - keyed by object_id + location
        self._text_cache: Dict[str, CachedTextLabel] = {}

        # Track the currently hovered game object for special rendering
        self._hovered_object: GameObject | None = None

        # Font scaling factor
        self._base_font_scale = 1.0

        # Window flags for the transparent overlay
        self._overlay_flags = (imgui.WindowFlags_.no_decoration.value | imgui.WindowFlags_.no_move.value
                               | imgui.WindowFlags_.no_resize.value | imgui.WindowFlags_.no_scrollbar.value
                               | imgui.WindowFlags_.no_scroll_with_mouse.value | imgui.WindowFlags_.no_collapse.value
                               | imgui.WindowFlags_.no_nav.value | imgui.WindowFlags_.no_bring_to_front_on_focus.value
                               | imgui.WindowFlags_.no_focus_on_appearing.value | imgui.WindowFlags_.no_inputs.value)

    def clear(self):
        """Clear the text cache to force regeneration of all labels."""
        self._text_cache.clear()

    def set_hovered_obj(self, obj: GameObject | None):
        """
        Set the currently hovered object for special label rendering.

        Args:
            obj: The object that is currently being hovered, or None if no object is hovered
        """
        self._hovered_object = obj

    def _compute_content_hash(self, text: str, obj: GameObject, location: TrackLabelLocation) -> str:
        """
        Compute a hash of the label content to detect changes.
        
        Args:
            text: The text content
            obj: The game object
            location: The label location
            
        Returns:
            A hash string representing the content
        """
        # Include relevant object properties that might affect the text
        content_str = f"{text}_{obj.object_id}_{location.value}_{obj.U}_{obj.V}"
        return hashlib.md5(content_str.encode()).hexdigest()[:8]

    def _world_to_screen_coordinates(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Convert world coordinates to screen coordinates using the scene's transformation.
        
        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            
        Returns:
            Tuple of (screen_x, screen_y)
        """
        screen_pos = self.scene.world_to_screen((world_x, world_y))
        return float(screen_pos.x), float(screen_pos.y)

    def _apply_label_offset(self, x_screen: float, y_screen: float, location: TrackLabelLocation, offset: int,
                            text_size: Tuple[float, float]) -> Tuple[float, float]:
        """
        Apply location-based offset to screen coordinates.
        
        Args:
            x_screen: Base screen X coordinate
            y_screen: Base screen Y coordinate  
            location: Label location relative to the base position
            offset: Base offset distance in pixels
            text_size: (width, height) of the text in pixels
            
        Returns:
            Tuple of adjusted (x, y) screen coordinates
        """
        text_width, text_height = text_size

        # Define offset multipliers for each location
        offset_map = {
            TrackLabelLocation.TOP_LEFT: (-offset - text_width, -offset - text_height),
            TrackLabelLocation.TOP_CENTER: (-text_width / 2, -offset - text_height),
            TrackLabelLocation.TOP_RIGHT: (offset, -offset - text_height),
            TrackLabelLocation.LEFT: (-offset - text_width, -text_height / 2),
            TrackLabelLocation.CENTER: (-text_width / 2, -text_height / 2),
            TrackLabelLocation.RIGHT: (offset, -text_height / 2),
            TrackLabelLocation.BOTTOM_LEFT: (-offset - text_width, offset),
            TrackLabelLocation.BOTTOM_CENTER: (-text_width / 2, offset),
            TrackLabelLocation.BOTTOM_RIGHT: (offset, offset),
        }

        dx, dy = offset_map.get(location, (0, 0))
        return x_screen + dx, y_screen + dy

    def _update_or_create_cached_label(self, obj: GameObject, location: TrackLabelLocation, text: str,
                                       font_scale: float) -> CachedTextLabel:
        """
        Update an existing cached label or create a new one.
        
        Args:
            obj: The game object
            location: Label location
            text: Text content
            font_scale: Font scaling factor
            
        Returns:
            The cached label (updated or newly created)
        """
        cache_key = f"{obj.object_id}_{location.value}"
        content_hash = self._compute_content_hash(text, obj, location)

        # Convert world position to screen position
        screen_x, screen_y = self._world_to_screen_coordinates(obj.U, obj.V)

        # Check if we have a cached label
        if cache_key in self._text_cache:
            cached_label = self._text_cache[cache_key]

            # If content hasn't changed, just update position
            if cached_label.content_hash == content_hash:
                cached_label.x_screen = screen_x
                cached_label.y_screen = screen_y
                return cached_label

        # Content changed or new label - create/update cache entry
        cached_label = CachedTextLabel(text=text,
                                       x_screen=screen_x,
                                       y_screen=screen_y,
                                       font_scale=font_scale,
                                       location=location,
                                       content_hash=content_hash,
                                       object_id=obj.object_id)

        self._text_cache[cache_key] = cached_label
        return cached_label

    def draw_track_labels(self, obj: GameObject, labels: TrackLabels, offset: int, font_scale: float):
        """
        Draw labels for a specific track based on its type and configuration.
        
        Args:
            obj: The game object to render labels for
            labels: The track labels configuration
            offset: Offset distance from the track center
            font_scale: Font scaling factor
        """
        # Render each configured label at its specified location
        for location, track_label in labels.labels.items():
            text = evaluate_input_format(track_label.label_format, obj)

            if text is not None and text != "":
                # Update or create cached label
                cached_label = self._update_or_create_cached_label(obj, location, text, font_scale)

                # Calculate text size for positioning
                text_size = imgui.calc_text_size(text)

                # Apply location-based offset
                final_x, final_y = self._apply_label_offset(cached_label.x_screen, cached_label.y_screen, location,
                                                            offset, (text_size.x, text_size.y))

                # Update the cached position
                cached_label.x_screen = final_x
                cached_label.y_screen = final_y

    def draw_all_ac_labels(self, gamestate: GameState):
        """
        Draw labels for all aircraft in the game state.
        
        Args:
            gamestate: Current game state containing all objects
        """
        fixed_wing_objs = gamestate.objects[GameObjectType.FIXEDWING]

        # Get the label configuration for this track type
        labels = get_labels_for_class_type(GameObjectType.FIXEDWING)

        # Get offset for positioning labels relative to track icons
        offset = config.app_config.get_int("radar", "contact_size")
        label_padding = config.app_config.get_int("radar", "contact_label_padding")
        total_offset = offset + label_padding
        font_scale = config.app_config.get_float("radar", "contact_font_scale") / 100.0  # Convert to ImGui scale

        if labels is not None:
            for obj in fixed_wing_objs.values():
                self.draw_track_labels(obj, labels, total_offset, font_scale)

    def draw_custom_text(self,
                         text: str,
                         x_world: int,
                         y_world: int,
                         scale: Optional[float] = None,
                         centered: bool = False,
                         location: TrackLabelLocation = TrackLabelLocation.CENTER,
                         location_offset: tuple[int, int] = (0, 0),
                         screen_offset: tuple[float, float] = (0.0, 0.0)):
        """
        Draw custom text at a specific world position.
        
        Args:
            text: The text string to render
            x_world: World X coordinate
            y_world: World Y coordinate  
            scale: Font scale (uses radar default if None)
            centered: Whether to center the text
            location: Text positioning relative to coordinates
            location_offset: Additional offset in world units
            screen_offset: Additional offset in screen pixels
        """
        if scale is None:
            scale = config.app_config.get_float("radar", "contact_font_scale") / 100.0

        screen_x, screen_y = self._world_to_screen_coordinates(x_world, y_world)

        # Apply screen offset
        screen_x += screen_offset[0]
        screen_y += screen_offset[1]

        # Create cache entry for custom text
        cache_key = f"custom_{x_world}_{y_world}_{text}"

        cached_label = CachedTextLabel(text=text,
                                       x_screen=screen_x,
                                       y_screen=screen_y,
                                       font_scale=scale,
                                       location=location,
                                       content_hash=hashlib.md5(text.encode()).hexdigest()[:8],
                                       object_id=cache_key)

        self._text_cache[cache_key] = cached_label

    def render(self):
        """
        Render all cached text labels using ImGui.
        
        This should be called once per frame after all text has been queued
        via the draw_* methods. It uses a transparent overlay window to draw
        text at absolute screen positions.
        """
        if not self._text_cache:
            return

        # Get viewport for full-screen overlay
        viewport = imgui.get_main_viewport()

        # Set up transparent overlay window covering the entire viewport
        imgui.set_next_window_pos(viewport.work_pos)
        imgui.set_next_window_size(viewport.work_size)

        # Make window completely transparent and non-interactive for labels
        imgui.push_style_color(imgui.Col_.window_bg.value, imgui.ImVec4(0.0, 0.0, 0.0, 0.0))
        imgui.push_style_color(imgui.Col_.border.value, imgui.ImVec4(0.0, 0.0, 0.0, 0.0))
        imgui.push_style_var(imgui.StyleVar_.window_padding.value, imgui.ImVec2(0.0, 0.0))
        imgui.push_style_var(imgui.StyleVar_.window_border_size.value, 0.0)

        # Begin the overlay window
        if imgui.begin("RadarLabelsOverlay", None, self._overlay_flags):
            draw_list = imgui.get_window_draw_list()

            # Render each cached label
            for cached_label in self._text_cache.values():
                # Get text color (white by default)
                text_color = imgui.get_color_u32(
                    imgui.ImVec4(cached_label.color[0], cached_label.color[1], cached_label.color[2],
                                 cached_label.color[3]))

                # Add text to the draw list at the specified position
                draw_list.add_text(imgui.ImVec2(cached_label.x_screen, cached_label.y_screen), text_color,
                                   cached_label.text)

        imgui.end()

        # Pop style modifications
        imgui.pop_style_var(2)
        imgui.pop_style_color(2)

    def cleanup_stale_cache_entries(self, active_object_ids: set[str]):
        """
        Remove cache entries for objects that no longer exist.
        
        Args:
            active_object_ids: Set of currently active object IDs
        """
        # Find cache entries for objects that no longer exist
        stale_keys = []
        for cache_key, cached_label in self._text_cache.items():
            if cached_label.object_id not in active_object_ids:
                # Keep special entries like bullseye and custom text
                if not cached_label.object_id.startswith(('bullseye_', 'custom_')):
                    stale_keys.append(cache_key)

        # Remove stale entries
        for key in stale_keys:
            del self._text_cache[key]
