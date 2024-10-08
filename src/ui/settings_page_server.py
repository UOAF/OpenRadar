from concurrent.futures import thread
import re
from typing import Union, Optional, Dict

import pygame

from pygame_gui import UI_BUTTON_PRESSED
from pygame_gui.core import ObjectID, UIElement

from pygame_gui.elements import UIButton, UITextBox, UIScrollingContainer, UITextEntryLine, UILabel
from pygame_gui.core.interfaces import IContainerLikeInterface, IUIContainerInterface
from pygame_gui.core.interfaces import IUIManagerInterface, IUIElementInterface

import config
from trtt_client import ThreadState

from messages import DATA_THREAD_STATUS, UI_SETTINGS_PAGE_SERVER_CONNECT, UI_SETTINGS_PAGE_SERVER_DISCONNECT, UI_SETTINGS_PAGE_REQUEST_SERVER_STATUS

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
       
        container_top = self.get_container().get_relative_rect().top 
        container_width = self.get_container().get_size()[0] - 10
        container_height = self.get_container().get_size()[1] - 50        
        self.server_address_field = UITextEntryLine(relative_rect=pygame.Rect(self.get_container().get_relative_rect().left, 
                                                                              self.get_container().get_relative_rect().top+10, 
                                                                              container_width//2, 40),
                                                    initial_text='localhost:42674',
                                                    placeholder_text='Server address:port',
                                                    manager=self.ui_manager,
                                                    container=self,
                                                    object_id='#server_address_field',
                                                    anchors={'left': 'left',
                                                             'top': 'top'})

        self.server_info_text = UITextBox(relative_rect=pygame.Rect(0, self.get_container().get_relative_rect().top+10, 
                                                                   container_width//2, 30),
                                         html_text='Not connected',
                                         manager=self.ui_manager,
                                         container=self,
                                         object_id='#server_info_text',
                                         anchors={'left': 'left',
                                                  'top': 'top',
                                                  'left_target': self.server_address_field})

        self.connect_button = UIButton(relative_rect=pygame.Rect(0, 0, -1, 30),
                                      text='Connect',
                                      manager=self.ui_manager,
                                      container=self,
                                      object_id='#connect_button',
                                      anchors={'left': 'right',
                                               'right': 'right',
                                               'top_target': self.server_info_text,})

        self.disconnect_button = UIButton(relative_rect=pygame.Rect(0, 0, -1, 30),
                                       text="Disconnect",
                                       manager=self.ui_manager,
                                       container=self,
                                       object_id='#disconnect_button',
                                       anchors={'left': 'right',
                                               'right': 'right',
                                               'top_target': self.server_info_text,
                                               'right_target': self.connect_button})
        
        pygame.event.post(pygame.event.Event(UI_SETTINGS_PAGE_REQUEST_SERVER_STATUS))
        
    def process_event(self, event: pygame.Event) -> bool:
        consumed = super().process_event(event)
        
        if event.type == DATA_THREAD_STATUS:
            print(f"SettingsPageServer.process_event: {event.status}")
            thread_state: ThreadState = event.status
            thread_info: str = event.info
            color = thread_state.status_color
            self.server_info_text.set_text(f'<font color="{color}">{thread_state.status_msg}</font>  {thread_info}')
            consumed = True
            
        elif event.type == UI_BUTTON_PRESSED:
            if event.ui_element == self.connect_button:
                
                ip, port = self.server_address_field.get_text().rsplit(':', 1)
                if port is None or port == "":
                    port = 42674
                    self.server_address_field.set_text(f"{ip}:{port}")
                event_data = {'server':ip, 'port': int(port)}
                pygame.event.post(pygame.event.Event(UI_SETTINGS_PAGE_SERVER_CONNECT, event_data))
                consumed = True
            elif event.ui_element == self.disconnect_button:
                pygame.event.post(pygame.event.Event(UI_SETTINGS_PAGE_SERVER_DISCONNECT))
                consumed = True
        
        return consumed