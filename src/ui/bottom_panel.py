from typing import Union, Dict, Optional

import pygame

from pygame_gui.core import ObjectID, UIElement
from pygame_gui.core.interfaces import IUIManagerInterface
from pygame_gui.core.interfaces import IContainerLikeInterface
from pygame_gui.core.gui_type_hints import RectLike
from pygame_gui.elements import UIPanel, UIButton, UILabel

class BottomUIPanel(UIPanel):
    
    def __init__(self,
                 relative_rect: RectLike,
                 starting_height: int = 1,
                 manager: Optional[IUIManagerInterface] = None,
                 *,
                 element_id: str = 'panel',
                 margins: Optional[Dict[str, int]] = None,
                 container: Optional[IContainerLikeInterface] = None,
                 parent_element: Optional[UIElement] = None,
                 object_id: Optional[Union[ObjectID, str]] = None,
                 anchors: Optional[Dict[str, Union[str, UIElement]]] = None,
                 visible: int = 1
                 ):
        
        super().__init__(relative_rect, starting_height, manager,
                            element_id=element_id,
                            margins=margins,
                            container=container,
                            parent_element=parent_element,
                            object_id=object_id,
                            anchors=anchors,
                            visible=visible)
        
        _, self.height = self.relative_rect.size
        _, button_size = self.get_container().get_size()
        border = self.border_width if self.border_width is not None else 0
        
        self.settings_button = UIButton(
            pygame.Rect(border-button_size, border, button_size, button_size), 
            "",
            manager=self.ui_manager,
            container=self,
            object_id="#settings_button",
            tool_tip_text="Settings",
            anchors={'right': 'right', 'top': 'top'}
        )

        self.layers_button = UIButton(
            pygame.Rect(border, border, button_size, button_size), 
            "",
            manager=self.ui_manager,
            container=self,
            object_id="#layers_button",
            tool_tip_text="Layers",
            anchors={'left': 'left', 'top': 'top'}
        )
        
        self.clock_label = UILabel(
            pygame.Rect(border, border, 100, 40),
            text="00:00:00",
            manager=self.ui_manager,
            container=self,
            object_id="#clock_label",
            anchors={'centerx': 'centerx', 'centery': 'centery'}
        )
            
    def resize(self, width, height):
        self.set_dimensions((width, self.height))

    def process_event(self, event: pygame.Event) -> bool:
        return super().process_event(event)
    

