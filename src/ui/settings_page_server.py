import warnings
from typing import Union, Optional, Dict

import pygame

from pygame_gui.core import ObjectID, UIElement

from pygame_gui.elements import UIButton, UITextBox, UIScrollingContainer, UITextEntryLine
from pygame_gui.core.interfaces import IContainerLikeInterface, IUIContainerInterface
from pygame_gui.core.interfaces import IUIManagerInterface, IUIElementInterface

class SettingsPageServer(UIScrollingContainer):
    """
    A confirmation dialog that lets a user choose between continuing on a path they've chosen or
    cancelling. It's good practice to give a very brief description of the action they are
    confirming on the button they click to confirm it i.e. 'Delete' for a file deletion operation
    or, 'Rename' for a file rename operation.

    :param rect: The size and position of the window, includes the menu bar across the top.
    :param action_long_desc: Long-ish description of action. Can make use of HTML to
                             style the text.
    :param manager: The UIManager that manages this UIElement. If not provided or set to None,
                    it will try to use the first UIManager that was created by your application.
    :param window_title: The title of the  window.
    :param action_short_name: Short, one or two-word description of action for button.
    :param blocking: Whether this window should block all other mouse interactions with the GUI
                     until it is closed.
    :param object_id: A custom defined ID for fine-tuning of theming. Defaults to
                      '#confirmation_dialog'.
    :param visible: Whether the element is visible by default.
    :param action_long_desc_text_kwargs: a dictionary of variable arguments to pass to the translated string
                                         useful when you have multiple translations that need variables inserted
                                         in the middle.
    """


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
        