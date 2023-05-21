"""
Pulls everything together in the thumbnail control.
"""
from __future__ import annotations

__all__ = [
    'ThumbnailControl',
]

import concurrent.futures as futures
import dataclasses
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Callable, Literal, TypeAlias, cast
from enum import Flag, auto

import wx

from . import data, events, imagehandler
from .events import *
from .thumb import Thumb, TooltipOptions

Position: TypeAlias = tuple[int, int] | wx.Point
Size: TypeAlias = tuple[int, int] | wx.Size
RGB: TypeAlias = tuple[int, int, int]
RGBA: TypeAlias = tuple[int, int, int, int]
AnyColor: TypeAlias = RGB | RGBA | str | wx.Colour
StrPath: TypeAlias = str | os.PathLike[str]


def is_null_color(color: AnyColor) -> bool:
    """Helper to if a color is equivalent to wx.NullColor"""
    if isinstance(color, wx.Colour):
        return color is wx.NullColour
    if isinstance(color, tuple):
        return color[:3] == [wx.NullColour.red, wx.NullColour.green, wx.NullColour.blue]
    return False


class HitFlag(Flag):
    NOWHERE = auto()
    LEFT = auto()
    RIGHT = auto()
    ABOVE = auto()
    BELOW = auto()
    CENTER = auto()


@dataclasses.dataclass(frozen=True, slots=True)
class HitTest:
    index: int
    column: int
    row: int
    flags: HitFlag


class ThumbnailDropTarget(wx.FileDropTarget):
    def __init__(self, control: ThumbnailControl) -> None:
        super().__init__()
        self.SetDefaultAction(wx.DragMove)
        self.control = control

    def OnDropFiles(self, x: int, y: int, filenames: list[str]) -> bool:
        thumbs = []
        for filename in filenames:
            thumb = Thumb(filename)
            if thumb.path.suffix.lower() not in self.control.extensions:
                return False
            elif self.control.has_thumb(thumb.path):
                return False
            thumbs.append(thumb)
        if not thumbs:
            return False
        test = self.control.HitTest(x, y)
        if test.flags & HitFlag.CENTER:
            # On top an existing thumbnail, put them after it
            self.control.insert_thumbs(test.index, thumbs, select=True)
        elif test.flags & HitFlag.ABOVE:
            # Above all thumbnails
            self.control.insert_thumbs(0, thumbs, select=True)
        elif test.flags & HitFlag.BELOW:
            self.control.add_thumbs(thumbs, select=True)
        elif test.flags & HitFlag.LEFT:
            self.control.insert_thumbs(test.index, thumbs, select=True)
        elif test.flags & HitFlag.RIGHT:
            self.control.insert_thumbs(test.index + 1, thumbs, select=True)
        else:
            self.control.add_thumbs(thumbs, select=True)
        # Check if the control accepted the thumbnails
        thumbs = [thumb for thumb in thumbs if thumb in self.control.get_thumbs()]
        if not thumbs:
            return False
        event = ThumbnailEvent(
            events.thumbEVT_THUMBCTRL_IMAGES_DROPPED, self.control.GetId(), thumbs
        )
        self.control.GetEventHandler().ProcessEvent(event)
        return True


DEFAULT_IMAGE_HANDLER = imagehandler.NativeImageHandler()


class ThumbnailControl(wx.ScrolledWindow):
    extensions: frozenset[str] = frozenset(
        {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif'}
    )

    @dataclasses.dataclass(slots=True)
    class Options:
        @staticmethod
        def format_filename(thumb: Thumb) -> str:
            """The default filename formatter"""
            return thumb.path.name

        """The various options associated with a ThumbnailControl"""
        # Thumbnail drawing options
        thumb_outline_color_deselected: AnyColor = dataclasses.field(
            default_factory=lambda: wx.LIGHT_GREY
        )
        """Color used to outline the images, if any.  Helps improve visibility.
        """
        thumb_outline_color_selected: AnyColor = (153, 209, 255)
        """Color used to outline a selected image, if any."""
        thumb_highlight_color_deselected: AnyColor = (229, 243, 255)
        """Color of the highlighted area when hovering over a deselected
         thumbnail.
         """
        thumb_highlight_color_selected: AnyColor = (204, 232, 255)
        """Color of the highlighted area when hobering over a selected thumbnail."""
        thumb_highlight_selected_border_color: AnyColor = (153, 209, 255)
        """Color of the edge of the highlighted area when hovering over a selected
        thumbnail.
        """
        background_color: AnyColor = dataclasses.field(
            default_factory=lambda: wx.NullColour
        )
        """Background color of the control. Defaults to that of a ListCtrl."""

        show_highlighted_area: bool = True
        """Whether a highlighted should be drawn when hovering over an image."""
        image_highlight_factor: float = 1.01
        """How much an image should be brightened when hovering over it. This is a
        mutltiplicative factor.
        """

        show_image_shadow: bool = True
        """Draw a shadow under the thumbnails for a 3D effect."""
        show_filenames: Callable[[Thumb], str] | Literal[False] = format_filename
        """Whether filenames should be included under the thumbnail."""
        show_tooltip: bool = True
        """Whether a tooltip should popup with more image information."""
        tooltip_delay_ms: int = 1000
        """Delay before a tooltip is shown on hover."""
        tooltip_options: TooltipOptions = TooltipOptions.DEFAULT
        """What information should be included in the tooltip."""

        text_color: AnyColor = dataclasses.field(default_factory=lambda: wx.NullColour)

        # Geometry
        thumb_spacing: int = 10
        """How much spacing to reserve between thumbnails. Minimum of 4."""
        thumb_size: tuple[int, int] = (96, 80)
        """Thumbnail size in pixels. Minimum of 30x30, maximum is limited by the window
        size.
        """

        allow_dragging: bool = False
        """Set to allow dragging images out of the control to any valid drop target."""
        accepts_files: bool = False
        """Set to allow dropping images onto the control."""

        zoom_rate: float = 1.4
        """How much to zoom in/out when zooming with the mousewheel, keyboard, or API.
        """

        sort_key: Callable[[Thumb], Any] | None = None
        """Optional function to use as a key for sorting the thumbnails."""

        single_select: bool = False
        """Whether multiple thumbnails can be selected at once (via the UI)."""

        image_handler: imagehandler.ImageHandler = DEFAULT_IMAGE_HANDLER
        """What image loader to use."""

        image_parallelism: int = 5
        """How many images to load simultaneously."""

    DEFAULT_OPTIONS = Options()

    # Internal state variables:
    __slots__ = (
        '__options',
        '__thumbs',
        '__shadow',
        '__hovered_idx',
        '__focused_idx',
        '__selections',
        '__thread',
        '__thread_active',
        '__cols',
        '__rows',
        '__thumb_paint_size',
        '__tip_window',
    )
    __options: Options
    __thumbs: list[Thumb]
    __shadow: wx.MemoryDC
    __hovered_idx: set[int]
    __focused_idx: int
    __keyboard_selection_start: int
    __drag_selecting_start: tuple[int, int] | None
    __drag_selecting_end: tuple[int, int]
    __selections: set[int]
    __executor: futures.ThreadPoolExecutor
    __cols: int
    __rows: int
    __thumb_paint_size: tuple[int, int]
    __tip_window: wx.ToolTip

    def __init__(
        self,
        parent,
        id: int = wx.ID_ANY,
        pos: Position = wx.DefaultPosition,
        size: Size = wx.DefaultSize,
        style: int | None = None,
        options: Options = DEFAULT_OPTIONS,
    ):
        if style is None:
            super().__init__(parent, id, pos, size)
        else:
            super().__init__(parent, id, pos, size, style=style)
        self.SetDoubleBuffered(True)
        # Initialize state
        self.__thumbs = []
        self.__hovered_idx = set()
        self.__focused_idx = -1
        self.__keyboard_selection_start = -1
        self.__drag_selecting_start = None
        self.__drag_selecting_end = (0, 0)
        self.__selections = set()
        self.__cols = 1
        self.__rows = 1
        self.__executor = futures.ThreadPoolExecutor(max_workers=5)
        self.__tip_window = wx.ToolTip('')
        self.__tip_window.Enable(False)
        self.SetToolTip(self.__tip_window)
        self.__shadow = wx.MemoryDC(data.getShadow()[2])
        self.__thumb_paint_size = options.thumb_size  # estimate
        # Bind events: Resize and painting
        self.Bind(wx.EVT_SIZE, self.__on_size)
        self.Bind(wx.EVT_PAINT, self.__on_paint)
        self.Bind(wx.EVT_KILL_FOCUS, self.__on_lose_focus)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        # Bind events: Mouse
        self.Bind(wx.EVT_LEFT_DOWN, self.__on_mouse_down)
        self.Bind(wx.EVT_LEFT_UP, self.__on_mouse_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self.__on_double_click)
        self.Bind(wx.EVT_RIGHT_DOWN, self.__on_mouse_down)
        self.Bind(wx.EVT_RIGHT_UP, self.__on_mouse_up)
        self.Bind(wx.EVT_MOTION, self.__on_mouse_move)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_mouse_leave)
        self.Bind(wx.EVT_MOUSEWHEEL, self.__on_mouse_wheel)
        self.Bind(wx.EVT_SCROLLWIN, self.__on_scroll)
        # Keyboard navigation
        self.Bind(wx.EVT_CHAR, self.__on_char)
        self.Bind(wx.EVT_KEY_DOWN, self.__on_key)
        # For thread management
        self.Bind(wx.EVT_CLOSE, self.__on_close)
        # Initialize size parameters, images, etc
        self.set_options(options)

    def __on_close(self, event: wx.CloseEvent) -> None:
        self.__executor.shutdown(wait=False, cancel_futures=True)

    def __load_thumb(self, thumb: Thumb, handler: imagehandler.ImageHandler, force: bool) -> None:
        """Thread to load images.  Refreshed the window every n images loaded."""
        _id = self.GetId()
        wx.PostEvent(
            self, ThumbnailEvent(events.thumbEVT_THUMBCTRL_IMAGE_LOADING_STARTED, _id, [thumb])
        )
        thumb.load(force, handler=handler)
        wx.CallAfter(self.__refresh_by_thumb, thumb)
        wx.PostEvent(
            self, ThumbnailEvent(events.thumbEVT_THUMBCTRL_IMAGE_LOADING_DONE, _id, [thumb])
        )

    def __load(self, thumbs: Iterable[Thumb] | None = None, force: bool = False) -> None:
        """Updates the control fully: reloads all thumbnails and recalculates sizes
        used for painting, then refreshed.
        """
        if thumbs is None:
            thumbs = self.__thumbs
        # Stop any existing jobs
        self.__executor.shutdown(wait=False, cancel_futures=True)
        self.__executor = futures.ThreadPoolExecutor(max_workers=self.__options.image_parallelism)
        for thumb in thumbs:
            self.__executor.submit(
                self.__load_thumb, thumb, self.__options.image_handler, force
            )
        # And refresh
        self.__calc_sizes()
        self.Refresh()

    def __get_filename_height(self) -> int:
        """Detemine the height in pixels needed for the filename text"""
        dc = wx.MemoryDC()
        bitmap = wx.Bitmap(30, 30)
        dc.SelectObject(bitmap)
        _, text_h = dc.GetTextExtent('ATLWI')  # "tall" letters
        dc.SelectObject(wx.NullBitmap)
        dc.Destroy()
        del dc
        return text_h + 4  # 4px spacing between image and text

    def __calc_sizes(self, check: bool = True) -> None:
        """Precalculates the sizes of some elements for painting, as well as
        the virtual size of this window for scrolling. If check is True,
        resizes to allow any parent windows to do layout, then recalculates
        """
        width = cast(int, self.GetClientSize()[0])
        # Calculate the paint size needed for each thumbnail:
        spacing = self.__options.thumb_spacing
        paint_x, paint_y = self.__options.thumb_size
        paint_x += spacing  # Half on each side
        paint_y += spacing
        # Compute how many columns we can fit, and how many rows we need, recall
        # We need one extra "spacing" to go around the outside
        cols = (width - spacing) // paint_x
        self.__cols = max(cols, 1)
        rows, extra = divmod(len(self.__thumbs), self.__cols)
        if extra:  # A few more need to go in a partial row
            rows += 1
        self.__rows = max(rows, 1)
        # Add in extra height for filenames:
        if self.__options.show_filenames:
            paint_y += self.__get_filename_height()
        # Final size: cols * paint_x + padding around the outside, plus some
        # space for a scrollbar
        minx = paint_x + self.__options.thumb_spacing + 16
        miny = paint_y + self.__options.thumb_spacing
        self.SetVirtualSize(
            max(self.__cols * paint_x + self.__options.thumb_spacing + 16, minx),
            max(self.__rows * paint_y + self.__options.thumb_spacing, miny),
        )
        # Minimum size is to fit one thumbnail
        self.SetSizeHints(minx, miny)
        self.SetScrollRate(paint_x, paint_y // 9)
        self.__thumb_paint_size = (paint_x, paint_y)
        if check and width != self.GetClientSize()[0]:
            self.__calc_sizes(False)

    def __get_thumb_text_color(self, thumb: Thumb) -> AnyColor:
        if is_null_color(thumb.text_color):
            return self.__options.text_color
        return thumb.text_color

    def __get_paint_rect(self, initial_rect: wx.Rect | None = None) -> wx.Rect:
        """Get the painting rectangle for this window, used for handling EVT_PAINT."""
        size: wx.Size = self.GetClientSize()
        # Start as the size of the window
        if not initial_rect:
            rect = wx.Rect(0, 0, *size)
        else:
            rect = initial_rect
        # And "scroll" it to the current scroll position
        rect.x, rect.y = self.GetViewStart()  # In scroll units
        dx, dy = self.GetScrollPixelsPerUnit()
        rect.x *= dx  # Now in pixels
        rect.y *= dy  # Now in pixels
        return rect

    def __get_thumb_rect(self, index: int) -> wx.Rect:
        """Helper for refreshing just a specific thumbnail."""
        paint_x, paint_y = self.__thumb_paint_size
        client_w, _ = self.GetClientSize()
        extra_space = client_w - self.__options.thumb_spacing - self.__cols * paint_x
        extra_pad = extra_space // (self.__cols + 1)
        paint_x += extra_pad // 2
        x = (self.__options.thumb_spacing + extra_pad) // 2
        y = self.__options.thumb_spacing // 2
        row, col = divmod(index, self.__cols)
        thumb_x = x + col * paint_x
        thumb_y = y + row * paint_y
        rect = wx.Rect(thumb_x, thumb_y, paint_x, paint_y)
        tl = rect.GetTopLeft()
        br = rect.GetBottomRight()
        tl = self.CalcScrolledPosition(tl)
        br = self.CalcScrolledPosition(br)
        return wx.Rect(tl, br)

    def __paint_thumbnail(self, bitmap: wx.Bitmap, thumb: Thumb, index: int) -> None:
        """Draw a specific thumbnail with its decorations and padding onto a bitmap."""
        dc = wx.MemoryDC()
        dc.SelectObject(bitmap)
        # 1: Draw the background
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush(self.GetBackgroundColour(), wx.BRUSHSTYLE_SOLID))
        bitmap_size = bitmap.GetSize()
        dc.DrawRectangle(0, 0, *bitmap_size)
        # 2: Draw the selection / hightlight / focus if needed
        hovered = index in self.__hovered_idx
        selected = index in self.__selections
        focused = index == self.__focused_idx
        x = y = self.__options.thumb_spacing // 2
        selection_rect = wx.Rect(
            x // 2, y // 2, bitmap_size[0] - (x // 2) - 1, bitmap_size[1] - (y // 2) - 1
        )
        if self.__options.show_highlighted_area:
            # Highlighted area
            if hovered and selected:
                pen_color = self.__options.thumb_highlight_selected_border_color
                brush_color = self.__options.thumb_highlight_color_selected
                join = wx.JOIN_ROUND
            elif hovered and not selected:
                pen_color = self.__options.thumb_highlight_color_deselected
                brush_color = self.__options.thumb_highlight_color_deselected
                join = None
            elif selected:
                pen_color = wx.NullColour
                brush_color = self.__options.thumb_highlight_color_selected
                join = None
            else:
                pen_color = wx.NullColour
                brush_color = wx.NullColour
                join = None
            if not is_null_color(pen_color):
                pen = wx.Pen(pen_color, 1, wx.PENSTYLE_SOLID)
                if join is not None:
                    pen.SetJoin(join)
            else:
                pen = wx.TRANSPARENT_PEN
            if not is_null_color(brush_color):
                brush = wx.Brush(brush_color, wx.BRUSHSTYLE_SOLID)
            else:
                brush = wx.TRANSPARENT_BRUSH
            dc.SetPen(pen)
            dc.SetBrush(brush)
            dc.DrawRoundedRectangle(selection_rect, 2)
        # And the dotted box for focused items
        if focused and self.HasFocus():
            renderer: wx.RendererNative = wx.RendererNative.Get()
            renderer.DrawFocusRect(self, dc, selection_rect, 0)
        # 3: Draw the image decorations: shadow, outline, highlight
        thumb_size = self.__options.thumb_size
        if hovered and (factor := self.__options.image_highlight_factor) != 1.0:
            image = thumb.highlight(*thumb_size, factor)
        else:
            image = thumb.get_bitmap(*thumb_size)
        image_w, image_h = cast(tuple[int, int], image.GetSize())
        image_rect = wx.Rect(
            x + (thumb_size[0] - image_w) // 2,  # Center horizontally
            y + (thumb_size[1] - image_h) // 2,  # Center vertically
            *image.GetSize(),
        )
        if not thumb.alpha:
            # Outline and drop shadows only for non-transparent images
            if self.__options.show_image_shadow:
                # Drop shadow is 500x500, so we'll stretch it to fit
                # Corners:
                dc.Blit(image_rect.right, image_rect.y, 5, 5, self.__shadow, 495, 0)
                dc.Blit(image_rect.left, image_rect.bottom, 5, 5, self.__shadow, 0, 495)
                dc.Blit(
                    image_rect.right, image_rect.bottom, 5, 5, self.__shadow, 495, 495
                )
                # Edges:
                dc.StretchBlit(
                    image_rect.right,
                    image_rect.y + 5,
                    5,
                    image_h - 6,
                    self.__shadow,
                    495,
                    5,
                    5,
                    490,
                )
                dc.StretchBlit(
                    image_rect.x + 5,
                    image_rect.bottom,
                    image_w - 6,
                    5,
                    self.__shadow,
                    5,
                    495,
                    490,
                    5,
                )
            if selected:
                outline_color = self.__options.thumb_outline_color_selected
            else:
                outline_color = self.__options.thumb_outline_color_deselected
            if not is_null_color(outline_color):
                dc.SetPen(wx.Pen(outline_color, 0, wx.PENSTYLE_SOLID))
                dc.SetBrush(wx.TRANSPARENT_BRUSH)
                dc.DrawRectangle(
                    image_rect.x - 1,
                    image_rect.y - 1,
                    image_rect.width + 2,
                    image_rect.height + 2,
                )
        # 4: Draw the image
        dc.DrawBitmap(image, image_rect.x, image_rect.y, useMask=True)
        # 5: Draw the filename
        if self.__options.show_filenames:
            text = fulltext = self.__options.show_filenames(thumb)
            max_width = selection_rect.width - self.__options.thumb_spacing
            text_x, text_y = dc.GetTextExtent(text)
            for lop in range(1, len(text)):
                if text_x <= max_width:
                    break
                text = fulltext[:-lop].rstrip('. \t') + '...'
                text_x, _ = dc.GetTextExtent(text)
            else:
                text = ''
            if text:
                dc.SetFont(wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT))
                dc.SetTextForeground(self.__get_thumb_text_color(thumb))
                image_rect.y = min(bitmap_size[1] - text_y - 4, image_rect.bottom + 7)
                image_rect.height = text_y
                dc.DrawLabel(text, image_rect, wx.ALIGN_CENTER)
                # dc.DrawText(text, selection_rect.x + offset, image_rect.bottom + 2)
        # Done
        dc.SelectObject(wx.NullBitmap)
        dc.Destroy()
        del dc

    def __refresh_by_thumb(self, *thumbs: Thumb) -> None:
        """Calls Update on the region for the given Thumbs.  NOTE: This is called from a
        thread via wx.CallLater, so we might get old data after we've changed the saved
        thumbs.
        """
        indices = []
        for thumb in thumbs:
            try:  # thread guarding
                indices.append(self.__thumbs.index(thumb))
            except ValueError:
                pass
        self.__refresh_by_index(*indices)

    def __refresh_by_index(self, *indices: int) -> None:
        """ "Calls update on the region for the Thumbs at the given indices"""
        n = len(self.__thumbs)
        valid = (i for i in indices if 0 <= i < n)
        rects = list(map(self.__get_thumb_rect, valid))
        for rect in rects:
            self.RefreshRect(rect)

    # Draw: Start of painting
    def __on_paint(self, event: wx.PaintEvent) -> None:
        """wx.EVT_PAINT handler. A lot longer than the simpele logic would suggest
        because we want to optimize draw time:
        - Only draw visible items
        - Only draw in invalidated regions
        """
        dc = wx.BufferedPaintDC(self)
        self.PrepareDC(dc)
        # Quick out
        if not self.__thumbs:
            dc.Clear()
            return
        # Get only the area that needs repainting
        region_iterator = wx.RegionIterator(self.GetUpdateRegion())
        # TODO: Optimize futher than just this?
        paint_rects = []
        max_paint_rect = self.__get_paint_rect()
        while region_iterator.HaveRects():
            rect = region_iterator.GetRect()
            tl = rect.GetTopLeft()
            br = rect.GetBottomRight()
            tl = self.CalcUnscrolledPosition(tl)
            br = self.CalcUnscrolledPosition(br)
            rect = wx.Rect(tl, br)
            rect.Intersect(max_paint_rect)
            if not rect.IsEmpty():
                paint_rects.append(rect)
            region_iterator.Next()
        if not paint_rects:
            return
        # Faster than calling .Union each time
        ux = min(rect.x for rect in paint_rects)
        uy = min(rect.y for rect in paint_rects)
        ul = max(rect.left for rect in paint_rects)
        ub = max(rect.bottom for rect in paint_rects)
        union_rect = wx.Rect((ux, uy), (ul, ub))
        # 1: Draw the thumbnails
        paint_x, paint_y = self.__thumb_paint_size
        client_w, client_h = self.GetClientSize()
        extra_space = client_w - self.__options.thumb_spacing - self.__cols * paint_x
        extra_pad = extra_space // (self.__cols + 1)
        paint_x += extra_pad // 2
        x = (self.__options.thumb_spacing + extra_pad) // 2
        y = self.__options.thumb_spacing // 2
        # Optimization so we dont enumerate over the whole thumblist,
        # which could be slow if very long
        start_col = max(0, (union_rect.x - x) // paint_x)
        end_col = min(self.__cols, (union_rect.right - x) // paint_x + 1)
        start_row = max(0, (union_rect.y - y) // paint_y)
        end_row = min(self.__rows, (union_rect.bottom - y) // paint_y + 1)
        start_i = start_row * self.__cols + start_col
        end_i = end_row * self.__cols + end_col
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush(self.GetBackgroundColour(), wx.BRUSHSTYLE_SOLID))
        for i, thumb in enumerate(self.__thumbs[start_i:end_i], start_i):
            row, col = divmod(i, self.__cols)
            thumb_x = x + col * paint_x
            thumb_y = y + row * paint_y
            thumb_rect = wx.Rect(thumb_x, thumb_y, paint_x, paint_y)
            for rect in paint_rects:
                if rect.Intersects(thumb_rect):
                    break
            else:
                continue  # Not in any of the update areas
            # Draw the background
            dc.DrawRectangle(thumb_x, thumb_y, paint_x, paint_y)
            # And the image on top
            bitmap = wx.Bitmap(*self.__thumb_paint_size)
            self.__paint_thumbnail(bitmap, thumb, i)
            dc.DrawBitmap(bitmap, thumb_x + extra_pad // 2, thumb_y)

        # Maybe not fully drawn on the last row though... deal with it after
        drawn_w = self.__cols * paint_x
        drawn_h = self.__rows * paint_y
        drawn_rect = wx.Rect(x, y, drawn_w, drawn_h)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush(self.GetBackgroundColour(), wx.BRUSHSTYLE_SOLID))
        # 2: Draw the outside padding
        w = max(client_w, drawn_rect.width)
        h = max(client_h, drawn_rect.height)
        dc.DrawRectangle(0, 0, w, drawn_rect.y)  # Top
        dc.DrawRectangle(0, 0, drawn_rect.x, h + 50)  # Left
        dc.DrawRectangle(
            drawn_rect.GetRight(), 0, w - drawn_rect.GetRight(), h + 50
        )  # Right
        dc.DrawRectangle(
            0, drawn_rect.GetBottom(), w, h - drawn_rect.GetBottom() + 50
        )  # Bottom
        # 3: And fill in any "missing" thumbnails
        extra = len(self.__thumbs) % self.__cols
        if extra:
            drawn_rect.x += extra * paint_x
            drawn_rect.y = drawn_rect.bottom - paint_y
            dc.DrawRectangle(drawn_rect)
        # 4: Draw any drag selection box if needed
        if self.__drag_selecting_start:
            # Don't use __drag_selection_rect - it's in the wrong coordinates
            left = min(self.__drag_selecting_start[0], self.__drag_selecting_end[0])
            right = max(self.__drag_selecting_start[0], self.__drag_selecting_end[0])
            top = min(self.__drag_selecting_start[1], self.__drag_selecting_end[1])
            bottom = max(self.__drag_selecting_start[1], self.__drag_selecting_end[1])
            tl = (left, top)
            br = (right, bottom)
            rect = wx.Rect(left, top, right - left, bottom - top)
            for paint_rect in paint_rects:
                if paint_rect.Intersects(rect):
                    dc.SetPen(wx.Pen(wx.BLACK, 1, wx.PENSTYLE_SHORT_DASH))
                    dc.SetBrush(wx.TRANSPARENT_BRUSH)
                    dc.DrawRoundedRectangle(rect, 2)
                    break

    def __on_size(self, event: wx.SizeEvent | None = None) -> None:
        """Handle window resizing."""
        self.__calc_sizes()
        self.scroll_to_thumb(self.__focused_idx)
        self.Refresh()

    def __on_lose_focus(self, event: wx.FocusEvent) -> None:
        """Handle losing focus."""
        self.__drag_selecting_start = None
        self.__refresh_by_index(self.__focused_idx)

    def __on_mouse_down(self, event: wx.MouseEvent) -> None:
        """Handle left clicking pressed down."""
        last_focus = self.__focused_idx
        test = self.HitTest(*event.GetPosition())
        if test.flags == HitFlag.CENTER:
            self.__focused_idx = test.index
        else:
            self.__focused_idx = -1
        if event.ControlDown():  # Toggle selection
            if self.__focused_idx != -1:
                if self.__options.single_select:
                    if self.__focused_idx in self.__selections:
                        self.select([])
                    else:
                        self.select([self.__focused_idx])
                else:
                    self.select([self.__focused_idx], toggle=True)
        elif event.ShiftDown() and not self.__options.single_select:
            # Range selection
            if self.__focused_idx != -1:
                begin_index = min(self.__focused_idx, last_focus)
                end_index = max(self.__focused_idx, last_focus)
                self.select(range(begin_index, end_index + 1))
            self.__focused_idx = last_focus  # But keep focus on the last item
        else:  # Select
            if self.__focused_idx == -1:
                self.select([])
            else:
                # For down click, if the item is already selected, we don't
                # singly select it until mouse up to allow for dragging
                if self.__focused_idx in self.__selections:
                    # Already selected, don't deselect others until mouse up
                    # to allow for dragging
                    self.__focused_idx = last_focus
                else:
                    self.select([self.__focused_idx])
        self.SetFocus()  # Window was clicked, so grab focus

    def __drag_selection_rect(self) -> wx.Rect | None:
        if not self.__drag_selecting_start:
            return None
        left = min(self.__drag_selecting_start[0], self.__drag_selecting_end[0])
        right = max(self.__drag_selecting_start[0], self.__drag_selecting_end[0])
        top = min(self.__drag_selecting_start[1], self.__drag_selecting_end[1])
        bottom = max(self.__drag_selecting_start[1], self.__drag_selecting_end[1])
        tl = self.CalcScrolledPosition(left, top)
        br = self.CalcScrolledPosition(right, bottom)
        return wx.Rect(tl[0], tl[1], br[0] - tl[0], br[1] - tl[1])

    def __stop_drag_selection(self) -> None:
        if self.HasCapture():
            self.ReleaseMouse()
        rect = self.__drag_selection_rect()
        if rect is not None:
            self.__drag_selecting_start = None
            self.RefreshRect(rect)

    def __on_mouse_up(self, event: wx.MouseEvent) -> None:
        """Handle releasing the mouse"""
        if self.__drag_selecting_start:
            # Context menu's can cause a spurrious EVT_MOUSE_MOTION with
            # IsDragging() = True to fire when clicking on the window off
            # the context menu
            if self.__drag_selecting_end != self.__drag_selecting_start:
                self.__stop_drag_selection()
                return
            else:
                # Wans't actually a drag, or the user is *really* precise
                # with the mouse
                self.__stop_drag_selection()
        test = self.HitTest(*event.GetPosition())
        if event.LeftUp() and not (event.ControlDown() or event.ShiftDown()):
            if test.flags == HitFlag.CENTER:
                self.__focused_idx = test.index
                self.select([test.index])
        elif event.RightUp():
            if test.index == -1 or test.flags != HitFlag.CENTER:
                self.__send_context_menu()
            else:
                self.__send_item_context_menu()

    def __on_double_click(self, event: wx.MouseEvent) -> None:
        """Handle double clicking."""
        # Focus / redrawing already handled by the mouse down/up handlers
        self.__send_item_activated()

    def __on_mouse_move(self, event: wx.MouseEvent) -> None:
        """Mouse moved: Handle hover effects and dragging."""
        draggable = self.__options.allow_dragging
        if draggable and event.Dragging() and self.__selections and not self.__drag_selecting_start:
            # Setup a drop source to send those files
            files = wx.FileDataObject()
            for i in self.__selections:
                files.AddFile(os.fspath(self.__thumbs[i].path))
            source = wx.DropSource(self)
            source.SetData(files)
            result = source.DoDragDrop(wx.Drag_DefaultMove)
            if result == wx.DragMove:
                # The drop target accepted a move, so remove the items:
                removed = [self.__thumbs[i] for i in self.__selections]
                self.__thumbs = [
                    thumb
                    for i, thumb in enumerate(self.__thumbs)
                    if i not in self.__selections
                ]
                self.__focused_idx = -1
                self.select([])
                self.__load()  # Thumbs removed, need to recalc size
                newevent = events.ThumbnailEvent(events.thumbEVT_THUMBCTRL_IMAGES_REMOVED, self.GetId(), thumbs=removed)
                self.GetEventHandler().ProcessEvent(newevent)
            # Otherwise a copy or a cancel, we don't need to do anything
        elif event.Dragging() and not self.__options.single_select:
            # Dragging to select
            if not self.HasCapture():
                self.CaptureMouse()
            x, y = event.GetPosition()
            if not (client_rect := self.GetClientRect()).Contains(x, y):
                # TODO: only triggers when the mouse moves...
                # How to use SendAutoScrollEvents?
                # In the meantime could use a timer.
                if y < client_rect.GetTop():
                    self.ScrollLines(-1)
                elif y > client_rect.GetBottom():
                    self.ScrollLines(1)
            x, y = self.CalcUnscrolledPosition(x, y)
            #x, y = self.CalcUnscrolledPosition(x, y)
            if not self.__drag_selecting_start:
                self.__drag_selecting_end = (x, y)
                self.__drag_selecting_start = (x, y)
            else:
                # Selection region:
                left = min(self.__drag_selecting_start[0], x)
                right = max(self.__drag_selecting_start[0], x)
                top = min(self.__drag_selecting_start[1], y)
                bottom = max(self.__drag_selecting_start[1], y)
                test_start = self.HitTest(*self.CalcScrolledPosition(left, top))
                test_end = self.HitTest(*self.CalcScrolledPosition(right, bottom))
                start_col = test_start.column
                if test_start.flags & HitFlag.RIGHT:
                    start_col += 1
                end_col = test_end.column
                if test_end.flags & HitFlag.LEFT:
                    end_col -= 1
                start_row = test_start.row
                if test_start.flags & HitFlag.BELOW:
                    start_row += 1
                end_row = test_end.row
                if test_end.flags & HitFlag.ABOVE:
                    end_row -= 1
                selections = []
                nthumbs = len(self.__thumbs)
                for row in range(start_row, end_row + 1):
                    for col in range(start_col, end_col + 1):
                        index = row * self.__cols + col
                        if index < nthumbs:
                            selections.append(index)
                self.select(selections)
                # Refresh region
                rect1 = self.__drag_selection_rect()
                self.__drag_selecting_end = (x, y)
                rect2 = self.__drag_selection_rect()
                rect = rect2.Union(rect1) # type: ignore (we know they're not None)
                self.RefreshRect(rect)
        else:
            if not event.Dragging() and self.__drag_selecting_start is not None:
                self.__stop_drag_selection()
            event.Skip()
            self.__do_hover_detection(*event.GetPosition())

    def __do_hover_detection(self, x: int, y: int) -> None:
        """Handle detection of the hover target"""
        test = self.HitTest(x, y)
        if test.flags != HitFlag.CENTER:
            hover = -1
        else:
            hover = test.index
        if self.__options.show_tooltip:
            if hover in self.__hovered_idx:
                self.__tip_window.SetDelay(self.__options.tooltip_delay_ms)
            elif hover != -1:
                self.__tip_window.Enable(False)
                tip = self.__thumbs[hover].get_tooltip(self.__options.tooltip_options)
                self.__tip_window.SetTip(tip)
                self.__tip_window.SetDelay(self.__options.tooltip_delay_ms)
                self.__tip_window.Enable(True)
            else:
                self.__tip_window.Enable(False)
        if hover not in self.__hovered_idx:  # Hover changed, need to redraw
            self.__refresh_by_index(hover, *self.__hovered_idx)
            self.__hovered_idx = {hover} if hover != -1 else set()
            self.__send_hover()

    def __on_mouse_leave(self, event: wx.MouseEvent) -> None:
        """Mouse left the window"""
        if not self.__hovered_idx:
            return
        # Otherwise, we have to redraw
        hover = self.__hovered_idx
        self.__hovered_idx = set()
        self.__refresh_by_index(*hover)
        self.__send_hover()

    def __on_mouse_wheel(self, event: wx.MouseEvent) -> None:
        """Mouse wheel moved -> Zoom / Scroll"""
        if event.ControlDown():  # Zoom!
            if event.GetWheelRotation() > 0:
                self.zoom(out=False)
            else:
                self.zoom(out=True)
        else:
            # ScrolledWindow animates too slowly, so roll our own:
            if event.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL:
                # Scroll
                lines = (
                    event.GetWheelRotation()
                    // event.GetWheelDelta()
                    * event.GetLinesPerAction()
                )
                xstart, ystart = self.GetViewStart()
                w, h = self.GetClientSize()
                self.Scroll(xstart, ystart - lines)
                self.SetScrollPos(
                    wx.VERTICAL,
                    self.GetScrollPos(wx.VERTICAL)
                    - event.GetWheelRotation() // event.GetWheelDelta(),
                )
                # Hover detect
                self.__do_hover_detection(*event.GetPosition())
                # Redraw leaving/entering area:
                # The amount scrolled might have been limited by the ends of
                # of the scrollbar
                _, yend = self.GetViewStart()
                lines = yend - ystart
                _, dy = self.GetScrollPixelsPerUnit()
                px_y = -lines * dy
                leaving_rect = wx.Rect(xstart, ystart - 20, w, px_y + 20)
                entering_rect = wx.Rect(xstart, ystart + h, w, px_y + 20)
                # Update drag selection
                if self.__drag_selecting_start:
                    self.RefreshRect(self.__drag_selection_rect())
                if lines > 0:
                    self.RefreshRect(leaving_rect)
                else:
                    self.RefreshRect(entering_rect)
            else:
                event.Skip()

    def __on_scroll(self, event: wx.ScrollWinEvent) -> None:
        event.Skip()
        x, y = wx.GetMousePosition()
        x, y = self.ScreenToClient(x, y)
        self.__do_hover_detection(x, y)

    def __send_selection_changed(self) -> None:
        """Send a selection changed event"""
        if not self.__drag_selecting_start:
            # When drag selecting, allow the focus item to move out of sight
            self.scroll_to_thumb(self.__focused_idx)
        new_event = ThumbnailEvent(
            events.thumbEVT_THUMBCTRL_SELECTION_CHANGED, self.GetId(),
            [self.__thumbs[i] for i in self.__selections]
        )
        self.GetEventHandler().ProcessEvent(new_event)

    def __send_context_menu(self) -> None:
        """Send a context menu event (not on items)"""
        new_event = ThumbnailEvent(
            events.thumbEVT_THUMBCTRL_CONTEXT_MENU,
            self.GetId(),
            [self.__thumbs[i] for i in self.__selections],
        )
        self.GetEventHandler().ProcessEvent(new_event)

    def __send_item_context_menu(self) -> None:
        """Send an item context menu event"""
        new_event = ThumbnailEvent(
            events.thumbEVT_THUMBCTRL_ITEM_CONTEXT_MENU,
            self.GetId(),
            [self.__thumbs[i] for i in self.__selections],
        )
        self.GetEventHandler().ProcessEvent(new_event)

    def __send_item_activated(self) -> None:
        """Send an item activated event"""
        if self.__focused_idx != -1:
            new_event = ThumbnailEvent(
                events.thumbEVT_THUMBCTRL_ITEM_ACTIVATED,
                self.GetId(),
                [self.__thumbs[self.__focused_idx]],
            )
            self.GetEventHandler().ProcessEvent(new_event)

    def __send_hover(self) -> None:
        """Send a hover changed event"""
        items = [self.__thumbs[idx] for idx in self.__hovered_idx]
        new_event = ThumbnailEvent(
            events.thumbEVT_THUMBCTRL_HOVER_CHANGED, self.GetId(), items
        )
        self.GetEventHandler().ProcessEvent(new_event)

    def __on_char(self, event: wx.KeyEvent) -> None:
        """Handle keyboard input"""
        if self.__focused_idx == -1:
            # Nothing focused, allow the superclass to handle it
            event.Skip()
            return
        keycode = event.GetKeyCode()
        focused = self.__focused_idx
        row, col = divmod(focused, self.__cols)
        # Compute columns to scroll on a page scroll, consistent with how much
        # the superclass would do it
        page_u = self.GetScrollPageSize(wx.VERTICAL)
        page_y = page_u * self.GetScrollPixelsPerUnit()[1]
        page_rows = page_y // self.__thumb_paint_size[1]

        # Move the focus (+selection depending on key modifiers)
        def up(i):
            nonlocal row
            row = max(row - i, 0)

        def down(i):
            nonlocal row
            row = min(row + i, self.__rows - 1)

        if keycode in (wx.WXK_UP, wx.WXK_NUMPAD_UP):
            up(1)
        elif keycode in (wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN):
            down(1)
        elif keycode in (wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT):
            col -= 1
            if col < 0 and row > 0:
                col = self.__cols - 1
                row -= 1
            col = max(col, 0)
        elif keycode in (wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT):
            col += 1
            if col >= self.__cols and row < self.__rows - 1:
                col = 0
                row += 1  # Will be corrected below
            col = min(col, self.__cols - 1)
        elif keycode in (wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP):
            if event.ShiftDown():
                up(page_rows * 4)
            else:
                up(page_rows)
        elif keycode in (wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN):
            if event.ShiftDown():
                down(page_rows * 4)
            else:
                down(page_rows)
        elif keycode in (wx.WXK_HOME, wx.WXK_NUMPAD_HOME):
            row = col = 0
        elif keycode in (wx.WXK_END, wx.WXK_NUMPAD_END):
            # Will be corrected below
            row = self.__rows
            col = self.__cols
        elif keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.__send_item_activated()
        elif keycode in (wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE):
            self.select([focused], toggle=True)
        else:
            # Allow other keys to be handled by other handlers
            event.Skip()
            return
        # Cancel any drag selecting
        self.__drag_selecting_start = None
        # Finish movement handling
        new_idx = row * self.__cols + col
        new_idx = min(new_idx, len(self.__thumbs) - 1)
        if new_idx == self.__focused_idx:
            return
        if event.ShiftDown() and not self.__options.single_select:
            # Changing selection, keep focus
            if self.__keyboard_selection_start == -1:
                self.__keyboard_selection_start = focused
            start = min(new_idx, self.__keyboard_selection_start)
            end = max(new_idx, self.__keyboard_selection_start)
            self.__focused_idx = new_idx
            self.__select(set(range(start, end + 1)))
        elif event.ControlDown():  # Move focus
            self.focus(new_idx)
        else:  # Move selection and focus
            # Not self.focus, so we avoid a double refresh
            self.__focused_idx = new_idx
            self.select([new_idx])
        self.scroll_to_thumb(new_idx)

    def __on_key(self, event: wx.KeyEvent) -> None:
        """A Key was pressed"""
        # Only handle keys that don't end up in EVT_CHAR
        self.__drag_selecting_start = None
        keycode = event.GetKeyCode()
        if keycode in (wx.WXK_ADD, wx.WXK_NUMPAD_ADD):
            self.zoom()
        elif keycode in (wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT):
            self.zoom(out=True)
        elif (
            event.ControlDown()
            and keycode == ord('A')
            and not self.__options.single_select
        ):
            self.select_all()
        else:
            event.Skip()

    def __select(self, indices: set[int], toggle: bool = False, *, inform: bool = True) -> None:
        """Internal select thumbnails, no checking / changing keyboard selection start
        """
        if toggle:
            new_selection = self.__selections.symmetric_difference(indices)
        else:
            new_selection = indices
        if new_selection == self.__selections:
            return
        elif self.__options.single_select and len(new_selection) > 1:
            new_selection = {self.__focused_idx}
        delta = self.__selections.symmetric_difference(new_selection)
        self.__selections = new_selection
        for i in delta:
            self.RefreshRect(self.__get_thumb_rect(i))
        # self.__refresh_by_index(*delta) -> need to make __send_selection_changed()
        # not do a full refresh first
        if inform:
            self.__send_selection_changed()

    def __setup_dragging(self, options: Options) -> None:
        if options.accepts_files:
            self.SetDropTarget(ThumbnailDropTarget(self))
        else:
            self.SetDropTarget(None)

    def __do_sort(self) -> None:
        """Sorts the thumbnails and refreshes the view."""
        if self.__options.sort_key:
            sort_key = self.__options.sort_key
            sorted_original = list(
                sorted(enumerate(self.__thumbs), key=lambda i_th: sort_key(i_th[1]))
            )
            self.__thumbs = [th for _, th in sorted_original]
            remap = {old_i: new_i for new_i, (old_i, _) in enumerate(sorted_original)}
            changes = set[int]()
            if self.__focused_idx != -1:
                new_focus = remap[self.__focused_idx]
                if new_focus != self.__focused_idx:
                    changes.update((self.__focused_idx, new_focus))
                    self.__focused_idx = new_focus
            new_hover = {remap[idx] for idx in self.__hovered_idx}
            changes.update(new_hover.symmetric_difference(self.__hovered_idx))
            self.__hovered_idx = new_hover
            if self.__keyboard_selection_start != -1:
                new_keyboard = remap[self.__keyboard_selection_start]
                if new_keyboard != self.__keyboard_selection_start:
                    changes.update((self.__keyboard_selection_start, new_keyboard))
                    self.__keyboard_selection_start = new_keyboard
            new_selections = set(map(remap.__getitem__, self.__selections))
            changes.update(new_selections.symmetric_difference(self.__selections))
            self.__selections = new_selections
            self.__refresh_by_index(*changes)

    def get_hovered(self) -> list[int]:
        """Returns the index of the item the mouse is hovering over"""
        return list(self.__hovered_idx)

    def set_hovered(self, indices: Iterable[int]) -> None:
        """Sets which items to consider being hovered over"""
        valid = {i for i in indices if 0 <= i < len(self.__thumbs)}
        changes = self.__hovered_idx.symmetric_difference(valid)
        self.__hovered_idx = valid
        self.__refresh_by_index(*changes)

    def zoom(self, *, out: bool = False) -> None:
        """Zoom the thumbnails in/out"""
        rate = self.__options.zoom_rate
        if rate == 1.0:
            return
        client_w, client_h = self.GetClientSize()
        rate = 1 / rate if out else rate
        w, h = self.__options.thumb_size
        new_w = w * rate
        new_h = h * rate
        spacing = self.__options.thumb_spacing
        if new_w + spacing > client_w:
            # Too wide to fit one image
            new_w = client_w - spacing
            new_h = new_w * h / w
        if new_h + spacing > client_h:
            # Too tall
            new_h = client_h - spacing
            new_w = new_h * w / h
        if new_w < 30:
            # Too thin
            new_w = 30
            new_h = new_w * h / w
        if new_h < 30:
            # Too short
            new_h = 30
            new_w = new_h * w / h
        self.set_thumb_size(int(new_w), int(new_h))
        self.__on_size()
        self.Refresh()

    def get_options(self) -> Options:
        """Returns the current configuration options for this window."""
        return self.Options(**dataclasses.asdict(self.__options))

    def set_options(self, options: Options) -> None:
        """Update the options for this window. Triggers a refresh."""
        # Value validation
        options.thumb_spacing = max(options.thumb_spacing, 4)
        if is_null_color(options.background_color):
            options.background_color = wx.SystemSettings.GetColour(
                wx.SYS_COLOUR_LISTBOX
            )
        if is_null_color(options.text_color):
            options.text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_CAPTIONTEXT)
        options.image_parallelism = max(options.image_parallelism, 1)
        # What updates are needed:
        curr_options = getattr(self, '__options', self.Options())
        self.__options = self.Options(**dataclasses.asdict(options)) # make a copy
        self.SetBackgroundColour(options.background_color)
        self.__setup_dragging(options)
        if curr_options.sort_key != options.sort_key:
            self.__do_sort()
        if curr_options.thumb_size != options.thumb_size or curr_options.thumb_spacing != options.thumb_spacing:
            self.set_thumb_size(*options.thumb_size) # leads to __calc_sizes
        elif curr_options.show_filenames != options.show_filenames:
            self.__calc_sizes()
        if options.single_select:
            self.__selections = {self.__selections.pop()} if self.__selections else set()
            self.__keyboard_selection_start = -1
        if curr_options.image_handler is not options.image_handler:
            self.__load(force=True)
        else:
            self.__load()
        self.Refresh()

    def get_selections(self) -> set[int]:
        """Returns the nth selected item, or the focused item."""
        return set(self.__selections)  # A copy

    def is_selected(self, item: int) -> bool:
        """Check if the given thumbnail (by index) is selected"""
        return item in self.__selections

    def select(self, indices: Iterable[int], *, toggle: bool = False) -> None:
        """Change the selected thumbnails"""
        valid = {index for index in indices if -1 < index < len(self.__thumbs)}
        self.__keyboard_selection_start = -1
        self.__select(valid, toggle)

    def select_thumbs(self, thumbs: Iterable[Thumb]) -> None:
        indicies = {self.__thumbs.index(thumb) for thumb in thumbs if thumb in self.__thumbs}
        self.__keyboard_selection_start = -1
        self.__select(indicies, inform=False)

    def select_all(self) -> None:
        self.select(range(len(self.__thumbs)))

    def focus(self, item: int) -> None:
        """Change the focused thumbnail"""
        if item == self.__focused_idx:
            return
        previous = self.__focused_idx
        self.__focused_idx = item
        self.__keyboard_selection_start = -1
        self.__refresh_by_index(previous, item)

    def get_focus(self) -> int:
        return self.__focused_idx

    def scroll_to_thumb(self, index: int) -> None:
        """Scrolls so the currently selecte item is visible."""
        # Check if anything's selected
        if index == -1:
            return
        # Check if the selected item is in the paint rectangle
        paint_rect = self.__get_paint_rect()
        row = index // self.__cols
        thumb_height = self.__thumb_paint_size[1]
        top = row * thumb_height
        bottom = top + thumb_height
        if top < paint_rect.GetTop():
            scroll_y = top  # scroll up
        elif bottom > paint_rect.GetBottom():
            scroll_y = bottom - paint_rect.height  # scroll down
        else:
            return
        # Do the scrolling
        _, dy = self.GetScrollPixelsPerUnit()
        scroll_units, extra = divmod(scroll_y, dy)
        if extra:
            scroll_units += 1
        x, _ = self.GetViewStart()
        self.Scroll(x, scroll_units)

    def set_thumb_size(self, width: int, height: int) -> None:
        """Set the thumbnail size in pixels, and refresh the control."""
        # Validate
        if width < 30:
            height = int(30 * height / width)
            width = 30
        if height < 30:
            width = int(30 * width / height)
            height = 30
        if (width, height) == self.__options.thumb_size:
            return
        self.__options.thumb_size = (width, height)
        # Recalc the sizes
        self.__calc_sizes()

    def HitTest(self, x: int, y: int) -> HitTest:
        """Determine the thumbnail close to a given position over the scrolled window
        (ie: what a MouseEvent.GetPosition would give). Flags will be a combination of:
         wx.LEFT -> to the left of the thumbnail
         wx.RIGHT -> to the right of the thumbnail
         wx.TOP -> above the thumbnail
         wx.BOTTOM -> below the thumbnail
         wx.CENTER -> directly over the thumbnail
        """
        x, y = self.CalcUnscrolledPosition(x, y)
        paint_x, paint_y = self.__thumb_paint_size
        client_w, _ = self.GetClientSize()
        extra_space = client_w - self.__options.thumb_spacing - self.__cols * paint_x
        extra_pad = extra_space // (self.__cols + 1)
        paint_x += extra_pad // 2
        col = (x - self.__options.thumb_spacing - extra_pad) // paint_x
        row = (y - self.__options.thumb_spacing // 2) // paint_y
        flags = HitFlag.NOWHERE
        index = -1
        if col < 0:
            col = 0
            flags |= HitFlag.LEFT
        if col >= self.__cols:
            col = self.__cols - 1
            flags |= HitFlag.RIGHT
        if row < 0:
            row = 0
            flags |= HitFlag.ABOVE
        if row >= self.__rows:
            row = self.__rows - 1
            flags |= HitFlag.BELOW
        index = row * self.__cols + col
        # Deal with extra spacing
        thumb_left = (self.__options.thumb_spacing + extra_pad) // 2 + col * paint_x
        thumb_top = self.__options.thumb_spacing // 2 + row * paint_y
        if x < thumb_left:
            flags |= HitFlag.LEFT
        elif x > thumb_left + paint_x:
            flags |= HitFlag.RIGHT
        if y < thumb_top:
            flags |= HitFlag.ABOVE
        elif y > thumb_top + paint_y:
            flags |= HitFlag.BELOW
        # Deal with incomplete last row:
        if index < len(self.__thumbs) and flags == HitFlag.NOWHERE:
            # Actually over an existing thumbnail
            flags = HitFlag.CENTER
        return HitTest(index, col, row, flags)

    def has_thumb(self, path: StrPath) -> bool:
        """Check if this control has a thumbnail for the given path."""
        path = Path(path)
        for thumb in self.__thumbs:
            if thumb.path == path:
                return True
        return False

    def get_index(self, thumb: Thumb) -> int:
        if thumb in self.__thumbs:
            return self.__thumbs.index(thumb)
        return -1

    def get_count(self) -> int:
        return len(self.__thumbs)

    def get_thumb(self, index: int | StrPath) -> Thumb:
        if isinstance(index, int):
            return self.__thumbs[index]
        else:
            index = Path(index)
            for thumb in self.__thumbs:
                if thumb.path == index:
                    return thumb
        raise KeyError(index)

    def set_thumb(self, index: int, thumb: Thumb) -> None:
        self.__thumbs[index] = thumb
        self.__load([thumb])

    def get_thumbs(self) -> list[Thumb]:
        return list(self.__thumbs)  # A copy

    def set_thumbs(self, thumbs: Iterable[Thumb]) -> None:
        self.__thumbs = list(thumbs)
        self.__selections = set()
        self.__focused_idx = -1
        self.__hovered_idx = set()
        self.__keyboard_selection_start = -1
        self.__do_sort()
        self.Scroll(0, 0)
        self.__load()

    def add_thumbs(self, thumbs: list[Thumb], select: bool = False) -> None:
        """Add thumbnails to the end of the view, optionally selecting them"""
        self.__thumbs.extend(thumbs)
        if select:
            end = len(self.__thumbs)
            start = end - len(thumbs)
            self.__selections = set(range(start, end))
        self.__do_sort()
        self.__load(thumbs)
        if select:
            self.__send_selection_changed()
        self.scroll_to_thumb(max(self.__selections))

    def insert_thumbs(
        self, index: int, thumbs: list[Thumb], select: bool = False
    ) -> None:
        """Insert thumnails to to the view at a position, optionally selecting them"""
        index = max(index, 0)
        index = min(index, len(self.__thumbs))
        self.__thumbs[index:index] = thumbs
        if select:
            self.select(range(index, index + len(thumbs)))
        self.__do_sort()
        self.__load(thumbs)
        if select:
            self.scroll_to_thumb(index + len(thumbs) - 1)

    def remove_thumbs(self, thumbs: Iterable[Thumb]) -> None:
        """Remove the given thumbnails from the view."""
        for thumb in thumbs:
            if thumb not in self.__thumbs:
                raise KeyError(f'{thumb}: Thumbnail not present')
            self.__thumbs.remove(thumb)
        # A lot need to be reset, but not everything
        self.__selections = set()
        self.__focused_idx = -1
        self.__hovered_idx = set()
        self.__keyboard_selection_start = -1
        self.__drag_selecting_start = None
        self.__calc_sizes()
        self.Refresh()

    def __contains__(self, thumb: Thumb) -> bool:
        return thumb in self.__thumbs

    def shutdown(self) -> None:
        """Shutdown threads."""
        self.__executor.shutdown(wait=False, cancel_futures=True)

    def refresh_thumbs(self, indices: Iterable[int], reload: bool = False) -> None:
        if reload:
            n = len(self.__thumbs)
            self.__load((self.__thumbs[i] for i in indices if 0 <= i < n))
        else:
            self.__refresh_by_index(*indices)

