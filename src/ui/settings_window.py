import warnings
from typing import Union, Optional, Dict


import pygame

from pygame_gui.core import ObjectID
from pygame_gui.core.interfaces import IUIManagerInterface
from pygame_gui.elements import UIWindow, UIButton, UITextBox, UITabContainer
from pygame_gui.core.gui_type_hints import RectLike

from pygame_gui.windows import UIConfirmationDialog

class SettingsWindow(UIWindow):
    
    def __init__(self, rect: RectLike,
                 manager: Optional[IUIManagerInterface] = None,
                 *,
                 window_title: str = 'pygame-gui.SettingsWindow',
                 blocking: bool = True,
                 object_id: Union[ObjectID, str] = ObjectID('#SettingsWindow', None),
                 visible: int = 1,
                 always_on_top: bool = True
                 ):

        super().__init__(rect, manager,
                         window_display_title=window_title,
                         element_id=['confirmation_dialog'],
                         object_id=object_id,
                         resizable=True,
                         visible=visible,
                         always_on_top=always_on_top)

        minimum_dimensions = (260, 200)
        if self.relative_rect.width < minimum_dimensions[0] or self.relative_rect.height < minimum_dimensions[1]:
            warn_string = ("Initial size: " + str(self.relative_rect.size) +
                           " is less than minimum dimensions: " + str(minimum_dimensions))
            warnings.warn(warn_string, UserWarning)
        self.set_minimum_dimensions(minimum_dimensions)


        self.settings_tabs = UITabContainer(relative_rect=pygame.Rect(0, 0, 0, 0),
                                            manager = self.ui_manager,
                                            container=self,
                                            object_id='#settings_tabs',
                                            anchors={'left': 'left',
                                                     'right': 'right',
                                                     'top': 'top',
                                                     'bottom': 'bottom'})

        # self.cancel_button = UIButton(relative_rect=pygame.Rect(-10, -40, -1, 30),
        #                               text='pygame-gui.Cancel',
        #                               manager=self.ui_manager,
        #                               container=self,
        #                               object_id='#cancel_button',
        #                               anchors={'left': 'right',
        #                                        'right': 'right',
        #                                        'top': 'bottom',
        #                                        'bottom': 'bottom'})

        # self.confirm_button = UIButton(relative_rect=pygame.Rect(-10, -40, -1, 30),
        #                                text=action_short_name,
        #                                manager=self.ui_manager,
        #                                container=self,
        #                                object_id='#confirm_button',
        #                                anchors={'left': 'right',
        #                                         'right': 'right',
        #                                         'top': 'bottom',
        #                                         'bottom': 'bottom',
        #                                         'left_target': self.cancel_button,
        #                                         'right_target': self.cancel_button})

        # text_width = self.get_container().get_size()[0] - 10
        # text_height = self.get_container().get_size()[1] - 50
        # self.confirmation_text = UITextBox(html_text=action_long_desc,
        #                                    relative_rect=pygame.Rect(5, 5,
        #                                                              text_width,
        #                                                              text_height),
        #                                    manager=self.ui_manager,
        #                                    container=self,
        #                                    anchors={'left': 'left',
        #                                             'right': 'right',
        #                                             'top': 'top',
        #                                             'bottom': 'bottom'},
        #                                    text_kwargs=action_long_desc_text_kwargs)

        self.set_blocking(blocking)