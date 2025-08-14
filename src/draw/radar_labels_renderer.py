"""
RadarLabelsRenderer - A standalone class for rendering all radar track labels and text elements.

This class extracts all text rendering capabilities from the TrackRenderer, providing a clean
separation of concerns between shape/geometry rendering and text label rendering.
"""

import numpy as np
from typing import Dict, Optional

from draw.scene import Scene
from draw.text import TextRendererMsdf, make_text_renderer
from game_object_types import GameObjectType
from sensor_tracks import Track
from util.track_labels import (TrackLabelLocation, get_labels_for_class_type, evaluate_input_format)
from util.bms_math import NM_TO_METERS

import config


class RadarLabelsRenderer:
    """
    Handles all text rendering for radar tracks and related elements.
    
    This class manages:
    - Track labels for all object types based on configuration
    - Hover labels for currently hovered tracks
    - Bullseye ring distance labels
    - Any other radar-related text elements
    """

    def __init__(self, scene: Scene):
        """
        Initialize the RadarLabelsRenderer.
        
        Args:
            scene: The Scene object containing rendering context and camera information
        """
        self.scene = scene
        self._mgl_context = scene.mgl_context

        # Initialize the text renderer with radar-specific scale configuration
        self.text_renderer = make_text_renderer(self._mgl_context,
                                                "atlas",
                                                scene,
                                                scale_source=("radar", "contact_font_scale"))

        # Track the currently hovered game object for special rendering
        self._hovered_track: Optional[Track] = None

    def clear(self):
        """Clear any cached text rendering data."""
        # Clear the text renderer's instance batches to prevent text accumulation
        self.text_renderer.init_buffers()

    def set_hovered_track(self, track: Optional[Track]):
        """
        Set the currently hovered track for special label rendering.
        
        Args:
            track: The track that is currently being hovered, or None if no track is hovered
        """
        self._hovered_track = track

    def draw_track_labels(self, track: Track, track_type: GameObjectType):
        """
        Draw labels for a specific track based on its type and configuration.
        
        Args:
            track: The track object to render labels for
            track_type: The type of game object (used for label configuration lookup)
        """
        pos_x, pos_y = int(track.position_m[0]), int(track.position_m[1])

        # Get the label configuration for this track type
        labels = get_labels_for_class_type(track_type)

        if labels is None:
            return

        # Get offset for positioning labels relative to track icons
        offset = config.app_config.get_int("radar", "contact_size")
        font_scale = config.app_config.get_int("radar", "contact_font_scale")

        # Check if this track is currently hovered
        is_hovered = self._hovered_track is not None and self._hovered_track.id == track.id

        # Render each configured label at its specified location
        for location, track_label in labels.labels.items():
            # Skip labels that should only show on hover if not hovered
            if track_label.show_on_hover and not is_hovered:
                continue

            # Skip regular labels if hovered and there are hover-only labels
            if is_hovered and not track_label.show_on_hover:
                # Check if there are any hover-only labels for this location
                has_hover_labels = any(label.show_on_hover for label in labels.labels.values() if label != track_label)
                if has_hover_labels:
                    continue

            text = evaluate_input_format(track_label.label_format, track)
            if text is not None and text != "":
                self.text_renderer.draw_text(text,
                                             pos_x,
                                             pos_y,
                                             scale=font_scale,
                                             location=location,
                                             screen_offset=(offset, offset))

    def draw_bullseye_labels(self, track: Track):
        """
        Draw distance labels for bullseye rings.
        
        Args:
            track: The bullseye track object
        """
        NUM_RINGS = 6
        RING_DISTANCE_NM = 20

        font_scale = config.app_config.get_int("radar", "contact_font_scale")

        # Draw distance labels for each ring
        for i in range(NUM_RINGS):
            distance_nm = RING_DISTANCE_NM * (i + 1)
            self.text_renderer.draw_text(f"{distance_nm} NM",
                                         int(track.position_m[0]),
                                         int(track.position_m[1]),
                                         scale=font_scale,
                                         location=TrackLabelLocation.TOP_RIGHT)

    def draw_custom_text(self,
                         text: str,
                         x_world: int,
                         y_world: int,
                         scale: Optional[int] = None,
                         centered: bool = False,
                         location: TrackLabelLocation = TrackLabelLocation.CENTER,
                         location_offset: tuple[int, int] = (0, 0),
                         screen_offset: tuple[float, float] = (0.0, 0.0)):
        """
        Draw custom text at a specific world position.
        
        This method provides direct access to the text renderer for custom text elements.
        
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
            scale = config.app_config.get_int("radar", "contact_font_scale")

        self.text_renderer.draw_text(text,
                                     x_world,
                                     y_world,
                                     scale=scale,
                                     centered=centered,
                                     location=location,
                                     location_offset=location_offset,
                                     screen_offset=screen_offset)

    def render(self):
        """
        Render all queued text elements.
        
        This should be called once per frame after all text has been queued
        via the draw_* methods.
        """
        self.text_renderer.render()
