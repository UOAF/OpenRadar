from typing import Union, Dict, Optional

import pygame

from pygame_gui.core import ObjectID, UIElement
from pygame_gui.core.interfaces import IUIManagerInterface
from pygame_gui.core.interfaces import IContainerLikeInterface
from pygame_gui.core.gui_type_hints import RectLike
from pygame_gui.elements import UIPanel, UIButton, UILabel
from pygame_gui._constants import UI_BUTTON_PRESSED

from ui.settings_window import SettingsWindow

from pygame_gui.windows import UIConfirmationDialog

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
        self.settings_window = None
        
        self.layers_button = UIButton(
            pygame.Rect(border, border, button_size, button_size), 
            "",
            manager=self.ui_manager,
            container=self,
            object_id="#layers_button",
            tool_tip_text="Layers",
            anchors={'left': 'left', 'top': 'top'}
        )
        
        self.load_ini_button = UIButton(
            pygame.Rect(border, border, button_size, button_size), 
            "Load INI",
            manager=self.ui_manager,
            container=self,
            object_id="#ini_button",
            tool_tip_text="Load INI",
            anchors={'left': 'left', 'top': 'top', 'left_target': self.layers_button}
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
        
        consumed_event = super().process_event(event)

        if event.type == UI_BUTTON_PRESSED and event.ui_element == self.settings_button:
            if self.settings_window is None:
                self.settings_window = SettingsWindow(pygame.Rect(0, 0, 300, 300), self.ui_manager,
                    window_title="Settings",
                    object_id="#settings_window"
                )
            else:
                self.settings_window.kill()
                self.settings_window = None
            consumed_event = True

        if event.type == UI_BUTTON_PRESSED and event.ui_element == self.layers_button:
            pass

        return consumed_event
    

