from typing import Union, Optional, Dict

import pygame

from pygame_gui import UI_COLOUR_PICKER_COLOUR_PICKED
from pygame_gui.core import ObjectID, UIElement
from pygame_gui.core.interfaces import IUIManagerInterface
from pygame_gui.core.interfaces import IContainerLikeInterface
from pygame_gui.elements import UIPanel, UIButton, UILabel
from pygame_gui._constants import UI_BUTTON_PRESSED, UI_WINDOW_CLOSE

from pygame_gui.windows import UIColourPickerDialog

from ui.ui_text_entry_dialog import UITextEntryDialog
from messages import UI_TEXT_ENTRY_DIALOG_TEXT_SUBMITTED
import game_objects

class ContextMenu(UIPanel):
    
    def __init__(self,
                 position: tuple[int, int],
                 unit: game_objects.GameObject,
                 starting_height: int = 1,
                 manager: Optional[IUIManagerInterface] = None,
                 *,
                 element_id: str = 'contextmenu',
                 margins: Optional[Dict[str, int]] = None,
                 container: Optional[IContainerLikeInterface] = None,
                 parent_element: Optional[UIElement] = None,
                 object_id: Optional[Union[ObjectID, str]] = None,
                 anchors: Optional[Dict[str, Union[str, UIElement]]] = None,
                 visible: int = 1
                 ):
        
        relative_rect = pygame.Rect(position, (125, 70))
        
        super().__init__(relative_rect, starting_height, manager,
                            element_id=element_id,
                            margins=margins,
                            container=container,
                            parent_element=parent_element,
                            object_id=object_id,
                            anchors=anchors,
                            visible=visible)

        self.unit = unit
        self.callsign_entry = None
        self.awaiting_callsign = False
        self.color_entry = None
        self.awaiting_color = False
        
        button_height = 30
        button_width, _ = self.get_container().get_size()
        self.get_container().get_abs_rect()
        margin = (self.relative_rect.width - button_width) //2
                
        UILabel(
            pygame.Rect(margin, margin, button_width, button_height), 
            f"{unit.get_display_name()}",
            manager=self.ui_manager,
            container=self,
            object_id=f"#callsign",
            anchors={'left': 'left', 'top': 'top'}                
        )

        self.change_callsign_button = UIButton(
            pygame.Rect(margin, button_height*1 + margin, button_width, button_height), 
            "Change Callsign",
            manager=self.ui_manager,
            container=self,
            object_id=f"#change_callsign",
            anchors={'left': 'left', 'top': 'top'}                
        )
        
        self.change_color_button = UIButton(
            pygame.Rect(margin, button_height*2 + margin, button_width, button_height), 
            "Change Color",
            manager=self.ui_manager,
            container=self,
            object_id=f"#change_color",
            anchors={'left': 'left', 'top': 'top'}                
        )     
        
        self.set_dimensions((self.relative_rect.width, button_height*3 + margin*2))
        

    def change_callsign(self):
        self.callsign_entry = UITextEntryDialog(pygame.Rect((0,0), (200,100)), 
                                                manager=self.ui_manager, 
                                                window_title="Enter new callsign", 
                                                object_id="#callsign_dialog")
        self.awaiting_callsign = True

    def change_color(self):
        self.color_entry = UIColourPickerDialog(pygame.Rect((0,0), (200,100)), 
                                                manager=self.ui_manager, 
                                                window_title="Select new color", 
                                                object_id="#color_dialog")
        self.awaiting_color = True

    def process_event(self, event: pygame.Event) -> bool:
        consumed = super().process_event(event)
    
        if event.type == UI_BUTTON_PRESSED:
            if event.ui_element == self.change_callsign_button:
                self.change_callsign()
                consumed = True
            elif event.ui_element == self.change_color_button:
                self.change_color()
                consumed = True
                         
        if event.type == pygame.MOUSEMOTION and self.rect is not None:
            mouse_x = event.pos[0]
            mouse_y = event.pos[1]
            x1, y1 = self.rect.topleft
            x2, y2 = self.rect.bottomright
            if not (x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2) and not (self.awaiting_callsign or self.awaiting_color):
                self.kill()
                
        # Callsign Entry Events
        if event.type == UI_TEXT_ENTRY_DIALOG_TEXT_SUBMITTED and event.ui_object_id == "#callsign_dialog":
            self.unit.override_name = event.text
            self.awaiting_callsign = False
            self.kill()
                    
        if self.callsign_entry is not None and (event.type == UI_WINDOW_CLOSE and
                                                event.ui_element == self.callsign_entry):
            self.callsign_entry = None
            self.awaiting_callsign = False
    
        # Color Picker Events
        if event.type == UI_COLOUR_PICKER_COLOUR_PICKED and event.ui_element == self.color_entry:
            self.unit.override_color = event.colour
            self.awaiting_color = False
            self.kill()

        return consumed
