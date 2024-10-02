import warnings
from typing import Union, Optional, Dict

import pygame

from pygame_gui.core import ObjectID, UIElement

from pygame_gui.elements import UIButton, UITextBox, UIScrollingContainer, UITextEntryLine
from pygame_gui.core.interfaces import IContainerLikeInterface, IUIContainerInterface
from pygame_gui.core.interfaces import IUIManagerInterface, IUIElementInterface

class SettingsPageServer(UIScrollingContainer):

    def __init__(self,
                 relative_rect: pygame.Rect,
                 manager: Optional[IUIManagerInterface] = None,
                 *,
                 starting_height: int = 1,
                 container: Optional[IContainerLikeInterface] = None,
                 parent_element: Optional[UIElement] = None,
                 object_id: Optional[Union[ObjectID, str]] = None,
                 anchors: Optional[Dict[str, Union[str, UIElement]]] = None,
                 visible: int = 1):

        super().__init__(relative_rect,
                         allow_scroll_x=False,
                         manager=manager,
                         starting_height=starting_height,
                         container=container,
                         parent_element=parent_element,
                         object_id=object_id,
                         anchors=anchors,
                         visible=visible)
        
        self.cancel_button = UIButton(relative_rect=pygame.Rect(-10, -40, -1, 30),
                                      text='pygame-gui.Cancel',
                                      manager=self.ui_manager,
                                      container=self,
                                      object_id='#cancel_button',
                                      anchors={'left': 'right',
                                               'right': 'right',
                                               'top': 'bottom',
                                               'bottom': 'bottom'})

        self.confirm_button = UIButton(relative_rect=pygame.Rect(-10, -40, -1, 30),
                                       text="do it",
                                       manager=self.ui_manager,
                                       container=self,
                                       object_id='#confirm_button',
                                       anchors={'left': 'right',
                                                'right': 'right',
                                                'top': 'bottom',
                                                'bottom': 'bottom',
                                                'left_target': self.cancel_button,
                                                'right_target': self.cancel_button})

        text_width = self.get_container().get_size()[0] - 10
        text_height = self.get_container().get_size()[1] - 50
        self.confirmation_text = UITextBox(html_text="herllo world",
                                           relative_rect=pygame.Rect(5, 5,
                                                                     text_width,
                                                                     text_height),
                                           manager=self.ui_manager,
                                           container=self,
                                           anchors={'left': 'left',
                                                    'right': 'right',
                                                    'top': 'top',
                                                    'bottom': 'bottom'})

    def init_server_button(self):
        server_button_rect = pygame.Rect((0, 0), (100, 40))
        server_button_rect.bottomleft = (10, -5)
        self.server_button = UIButton(relative_rect=server_button_rect,
                                            text='Server',
                                            manager=self.ui_manager,
                                            container=self,
                                            anchors={'left': 'left',
                                                     'bottom': 'bottom'})
        

        server_address_text_rect = pygame.Rect((0, 0), (180, 40))
        self.server_address_text = UITextEntryLine(relative_rect=server_address_text_rect,
                                                                      manager=self.ui_manager,
                                                                      container=self,
                                                                      anchors={'left': 'left',
                                                                               'top': 'top'})
        
    # def handle_server_button(self, event):
    #     if self.server_panel.visible:
    #         self.server_panel.hide()
    #         self.server_button.unselect()
    #     else:
    #         self.server_panel.show()
    #         self.server_button.select()
        