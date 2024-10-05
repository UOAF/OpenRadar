from typing import Union, Optional, Dict

import pygame

from pygame_gui.core import ObjectID, UIElement
from pygame_gui.core.interfaces import IUIManagerInterface
from pygame_gui.core.interfaces import IContainerLikeInterface
from pygame_gui.core.gui_type_hints import RectLike
from pygame_gui.elements import UIPanel, UIButton, UILabel
from pygame_gui._constants import UI_BUTTON_PRESSED, UI_BUTTON_ON_HOVERED

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

        self.buttons = [("Change Callsign", self.change_callsign),
                        ("Change Color", self.change_color)]

        UIButton(
            pygame.Rect(2, 2, 120, 30), 
            "Change Callsign",
            manager=self.ui_manager,
            container=self,
            object_id=f"#change_callsign",
            anchors={'left': 'left', 'top': 'top'}                
        )
        UIButton(
            pygame.Rect(2, 32, 120, 32), 
            "Change Color",
            manager=self.ui_manager,
            container=self,
            object_id=f"#change_color",
            anchors={'left': 'left', 'top': 'top'}                
        )     
        

    def change_callsign(self):
        self.prompt_text()

    def change_color(self):
        pass

    def prompt_color(self) -> pygame.Color:
        pygame_gui.windows(
            object_id="#color_dialog",
            element_id="color_dialog",
            container=self,
            rect=pygame.Rect(0, 0, 200, 200),
            manager=self.ui_manager,
            visible=1,
            element_relative_position=(0.5, 0.5),
            starting_height=1,
            layer_starting_height=1,
            layer=1,
            element_ids=["#color_dialog"]
        )

    def prompt_text(self) -> str:
        pass
        # self.ui_manager.create_ui_element(
        #     object_id="#text_dialog",
        #     element_id="text_dialog",
        #     container=self,
        #     rect=pygame.Rect(0, 0, 200, 200),
        #     manager=self.ui_manager,
        #     visible=1,
        #     element_relative_position=(0.5, 0.5),
        #     starting_height=1,
        #     layer_starting_height=1,
        #     layer=1,
        #     element_ids=["#text_dialog"]
        # )

    def on_button_click(self, label):
        print(f"Button '{label}' clicked for unit {self.unit}")

    def process_event(self, event: pygame.Event) -> bool:
        consumed = super().process_event(event)
    
        if event.type == UI_BUTTON_PRESSED:
            for button in self.buttons:
                if event.ui_element == button[0]:
                    button[1]()
                    consumed = True
                    break
                  
        if event.type == pygame.MOUSEMOTION and self.rect is not None:
            mouse_x = event.pos[0]
            mouse_y = event.pos[1]
            x1, y1 = self.rect.topleft
            x2, y2 = self.rect.bottomright
            if not (x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2):
                self.kill()
    
        return consumed
