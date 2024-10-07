from typing import Union, Dict, Optional

import pygame

from pygame_gui.core import ObjectID, UIElement
from pygame_gui.core.interfaces import IUIManagerInterface
from pygame_gui.core.interfaces import IContainerLikeInterface
from pygame_gui.core.gui_type_hints import RectLike
from pygame_gui.elements import UIPanel, UIButton
from pygame_gui._constants import UI_BUTTON_PRESSED

import game_objects

class LayersUIPanel(UIPanel):
    
    def __init__(self,
                 relative_rect: RectLike | None = None,
                 starting_height: int = 1,
                 manager: Optional[IUIManagerInterface] = None,
                 *,
                 element_id: str = 'LayersUIPanel',
                 margins: Optional[Dict[str, int]] = None,
                 container: Optional[IContainerLikeInterface] = None,
                 parent_element: Optional[UIElement] = None,
                 object_id: Optional[Union[ObjectID, str]] = None,
                 anchors: Optional[Dict[str, Union[str, UIElement]]] = None,
                 visible: int = 1
                 ):
        
        if relative_rect is None:
            relative_rect = pygame.Rect(0, 0, 74, 2000)
        
        super().__init__(relative_rect, starting_height, manager,
                            element_id=element_id,
                            margins=margins,
                            container=container,
                            parent_element=parent_element,
                            object_id=object_id,
                            anchors=anchors,
                            visible=visible)

        button_size, _ = self.get_container().get_size()
        self.get_container().get_abs_rect()
        margin = (self.relative_rect.width - button_size) //2
        
        self.sea_layer = UIButton(
            pygame.Rect(margin, margin-button_size, button_size, button_size), 
            "Sea",
            manager=self.ui_manager,
            container=self,
            object_id="#sea_layer_button",
            tool_tip_text="Sea Layer",
            anchors={"centerx": "centerx",
                    'bottom': 'bottom'}
        )
        
        self.ground_layer = UIButton(
            pygame.Rect(margin, -button_size, button_size, button_size), 
            "Ground",
            manager=self.ui_manager,
            container=self,
            object_id="#ground_layer_button",
            tool_tip_text="Ground Layer",
            anchors={'left': 'left', 'bottom': 'bottom',
                     'bottom_target': self.sea_layer}
        )
        
        self.sam_layer = UIButton(
            pygame.Rect(margin, -button_size, button_size, button_size), 
            "SAM (WIP)",
            manager=self.ui_manager,
            container=self,
            object_id="#ground_layer_button",
            tool_tip_text="Ground Layer",
            anchors={'left': 'left', 'bottom': 'bottom',
                     'bottom_target': self.ground_layer}
        )
        
        self.missile_layer = UIButton(
            pygame.Rect(margin, -button_size, button_size, button_size), 
            "Missile",
            manager=self.ui_manager,
            container=self,
            object_id="#missile_layer_button",
            tool_tip_text="Missile Layer",
            anchors={'left': 'left', 'bottom': 'bottom',
                     'bottom_target': self.sam_layer}
        )
        
        self.air_layer = UIButton(
            pygame.Rect(margin, -button_size, button_size, button_size), 
            "Air",
            manager=self.ui_manager,
            container=self,
            object_id="#air_layer_button",
            tool_tip_text="Air Layer",
            anchors={'left': 'left', 'bottom': 'bottom',
                     'bottom_target': self.missile_layer}
        )
        self.layers = {self.sea_layer:  game_objects.surfaceVessel, 
                        self.ground_layer: game_objects.groundUnit,
                        self.sam_layer: None, 
                        self.missile_layer: game_objects.missile, 
                        self.air_layer: game_objects.fixedWing}

        for layer in self.layers:
            
            if self.layers[layer] is not None and self.layers[layer].hide_class == False:
                layer.select()

        num_buttons = len(self.layers)
        height = num_buttons * button_size + margin * 2
        self.set_dimensions((relative_rect[2], height))
        self.set_relative_position((relative_rect[0], -height))


    def process_event(self, event: pygame.Event) -> bool:
        
        consumed_event = super().process_event(event)
        
        if event.type == UI_BUTTON_PRESSED:
            if event.ui_element == self.sea_layer:
                self.toggle_layer_visibility(self.sea_layer, self.layers[self.sea_layer])
            elif event.ui_element == self.ground_layer:
                self.toggle_layer_visibility(self.ground_layer, self.layers[self.ground_layer])
            elif event.ui_element == self.sam_layer:
                pass
            elif event.ui_element == self.missile_layer:
                self.toggle_layer_visibility(self.missile_layer, self.layers[self.missile_layer])
            elif event.ui_element == self.air_layer:
                self.toggle_layer_visibility(self.air_layer, self.layers[self.air_layer])

        return consumed_event
    
    def toggle_layer_visibility(self, layer, object_class):
        if object_class is None:
            return
        
        if object_class.hide_class == True:
            object_class.hide_class = False
            layer.select()
        else:
            object_class.hide_class = True
            layer.unselect()


