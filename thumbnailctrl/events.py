"""
Events associated withe ThumbnailCtrl
"""
__all__ = [
    'EVT_THUMBCTRL_SELECTION_CHANGED',
    'EVT_THUMBCTRL_CONTEXT_MENU',
    'EVT_THUMBCTRL_ITEM_CONTEXT_MENU',
    'EVT_THUMBCTRL_ITEM_ACTIVATED',
    'EVT_THUMBCTRL_HOVER_CHANGED',
    'EVT_THUMBCTRL_IMAGES_DROPPED',
    'EVT_THUMBCTRL_IMAGES_REMOVED',
    'EVT_THUMBCTRL_IMAGE_LOADING_STARTED',
    'EVT_THUMBCTRL_IMAGE_LOADING_DONE',
    'EVT_THUMBCTRL_LABEL_EDIT_END',
    'ThumbnailEvent',
]

from typing import TYPE_CHECKING

import wx

if TYPE_CHECKING:
    from .thumb import Thumb
else:
    Thumb = 'Thumb'


thumbEVT_THUMBCTRL_SELECTION_CHANGED = wx.NewEventType()
thumbEVT_THUMBCTRL_CONTEXT_MENU = wx.NewEventType()
thumbEVT_THUMBCTRL_ITEM_CONTEXT_MENU = wx.NewEventType()
thumbEVT_THUMBCTRL_ITEM_ACTIVATED = wx.NewEventType()
thumbEVT_THUMBCTRL_HOVER_CHANGED = wx.NewEventType()
thumbEVT_THUMBCTRL_IMAGES_DROPPED = wx.NewEventType()
thumbEVT_THUMBCTRL_IMAGES_REMOVED = wx.NewEventType()
thumbEVT_THUMBCTRL_IMAGE_LOADING_STARTED = wx.NewEventType()
thumbEVT_THUMBCTRL_IMAGE_LOADING_DONE = wx.NewEventType()
thumbEVT_THUMBCTRL_LABEL_EDIT_END = wx.NewEventType()


EVT_THUMBCTRL_SELECTION_CHANGED = wx.PyEventBinder(
    thumbEVT_THUMBCTRL_SELECTION_CHANGED, 1
)
EVT_THUMBCTRL_CONTEXT_MENU = wx.PyEventBinder(thumbEVT_THUMBCTRL_CONTEXT_MENU, 1)
EVT_THUMBCTRL_ITEM_CONTEXT_MENU = wx.PyEventBinder(
    thumbEVT_THUMBCTRL_ITEM_CONTEXT_MENU, 1
)
EVT_THUMBCTRL_ITEM_ACTIVATED = wx.PyEventBinder(thumbEVT_THUMBCTRL_ITEM_ACTIVATED, 1)
EVT_THUMBCTRL_HOVER_CHANGED = wx.PyEventBinder(thumbEVT_THUMBCTRL_HOVER_CHANGED, 1)
EVT_THUMBCTRL_IMAGES_DROPPED = wx.PyEventBinder(thumbEVT_THUMBCTRL_IMAGES_DROPPED, 1)
EVT_THUMBCTRL_IMAGES_REMOVED = wx.PyEventBinder(thumbEVT_THUMBCTRL_IMAGES_REMOVED, 1)
EVT_THUMBCTRL_IMAGE_LOADING_STARTED = wx.PyEventBinder(
    thumbEVT_THUMBCTRL_IMAGE_LOADING_STARTED, 1
)
EVT_THUMBCTRL_IMAGE_LOADING_DONE = wx.PyEventBinder(
    thumbEVT_THUMBCTRL_IMAGE_LOADING_DONE, 1
)
EVT_THUMBCTRL_LABEL_EDIT_END = wx.PyEventBinder(thumbEVT_THUMBCTRL_LABEL_EDIT_END, 1)


class ThumbnailEvent(wx.CommandEvent):
    """Class used to send notification of changes in a ThumbnailCtrl"""

    def __init__(
        self,
        evt_type,
        event_id: int = wx.ID_ANY,
        thumbs: list[Thumb] | None = None,
        key_code: int | None = None,
    ):
        super().__init__(evt_type, event_id)
        self.thumbs = thumbs if thumbs else []
        self.key_code = key_code
