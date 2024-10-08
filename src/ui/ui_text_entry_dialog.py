
import warnings
from typing import Union, Optional

import pygame

from pygame_gui import UI_TEXT_ENTRY_CHANGED, UI_TEXT_ENTRY_FINISHED, UI_BUTTON_PRESSED

from pygame_gui.core.interfaces import IUIManagerInterface
from pygame_gui.core.gui_type_hints import RectLike
from pygame_gui.core import ObjectID

from pygame_gui.elements import UIWindow, UIButton, UITextEntryLine
from pygame_gui.elements import UILabel

from messages import UI_TEXT_ENTRY_DIALOG_TEXT_SUBMITTED

class UITextEntryDialog(UIWindow):
    """
    A colour picker window that gives us a small range of UI tools to pick a final colour.

    :param rect: The size and position of the colour picker window. Includes the size of shadow,
                 border and title bar.
    :param manager: The manager for the whole of the UI. If not provided or set to None,
                    it will try to use the first UIManager that was created by your application.
    :param initial_colour: The starting colour for the colour picker, defaults to black.
    :param window_title: The title for the window, defaults to 'Colour Picker'
    :param object_id: The object ID for the window, used for theming - defaults to
                      '#colour_picker_dialog'
    :param visible: Whether the element is visible by default.
    """
    def __init__(self, rect: RectLike,
                 manager: Optional[IUIManagerInterface] = None,
                 *,
                 initial_colour: pygame.Color = pygame.Color(0, 0, 0, 255),
                 window_title: str = "Text Entry",
                 object_id: Union[ObjectID, str] = ObjectID('#text_entry_dialog', None),
                 visible: int = 1,
                 always_on_top: bool = False):

        super().__init__(rect, manager,
                         window_display_title=window_title,
                         element_id=['text_entry_dialog'],
                         object_id=object_id,
                         resizable=True,
                         visible=visible,
                         always_on_top=always_on_top)

        minimum_dimensions = (200, 110)
        if self.relative_rect.width < minimum_dimensions[0] or self.relative_rect.height < minimum_dimensions[1]:
            warn_string = ("Initial size: " + str(self.relative_rect.size) +
                           " is less than minimum dimensions: " + str(minimum_dimensions))
            warnings.warn(warn_string, UserWarning)
        self.set_minimum_dimensions(minimum_dimensions)
        
        container_width, _ = self.get_container().get_size()
        
        self.cancel_button = UIButton(relative_rect=pygame.Rect(-10, -40, -1, 30),
                                      text='pygame-gui.Cancel',
                                      manager=self.ui_manager,
                                      container=self,
                                      object_id='#cancel_button',
                                      anchors={'left': 'right',
                                               'right': 'right',
                                               'top': 'bottom',
                                               'bottom': 'bottom'})

        self.ok_button = UIButton(relative_rect=pygame.Rect(-10, -40, -1, 30),
                                  text='pygame-gui.OK',
                                  manager=self.ui_manager,
                                  container=self,
                                  object_id='#ok_button',
                                  anchors={'left': 'right',
                                           'right': 'right',
                                           'top': 'bottom',
                                           'bottom': 'bottom',
                                           'right_target': self.cancel_button})
        
        self.current_text = ""
        
        self.text_field = UITextEntryLine(
            relative_rect=pygame.Rect(0, 0, container_width, 30),
            manager=self.ui_manager,
            container=self,
            object_id='#text_field',
            anchors={'left': 'left',
                     'right': 'right',
                     'top': 'top',
                     'bottom': 'bottom'}
        )
        
        self.center()
    
    def center(self):
        if self.rect is not None and self.ui_manager is not None:
            self.rect.center = self.ui_manager.get_root_container().get_rect().center
            self.set_position(self.rect.topleft)
        
    def process_event(self, event: pygame.event.Event) -> bool:
        """                 
        Handles events that this UI element is interested in. 

        :param event: The pygame Event to process.

        :return: True if event is consumed by this element and should not be passed on to other
                 elements.

        """
        consumed_event = super().process_event(event)
        if event.type == UI_BUTTON_PRESSED and event.ui_element == self.cancel_button:
            self.kill()
            

        if ((event.type == UI_BUTTON_PRESSED and event.ui_element == self.ok_button )  or
            (event.type == UI_TEXT_ENTRY_FINISHED and event.ui_element == self.text_field )):
            # new event
            event_data = {'text': self.current_text,
                          'ui_element': self,
                          'ui_object_id': self.most_specific_combined_id}
            pygame.event.post(pygame.event.Event(UI_TEXT_ENTRY_DIALOG_TEXT_SUBMITTED, event_data))
            self.kill()
            
        if event.type == UI_TEXT_ENTRY_CHANGED and event.ui_element == self.text_field:
            self.current_text = event.text

        return consumed_event