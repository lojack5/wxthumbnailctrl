"""
Thumb class, encapsulating an image and its associated data, as
well as handling generating the thumbnail image.
"""
__all__ = [
    'Thumb',
    'TooltipOptions',
]

import datetime
import os
from dataclasses import InitVar, dataclass, field
from enum import Flag, auto
from pathlib import Path

import humanize
import wx

from . import imagehandler

_IMAGE_HANDLER = imagehandler.NativeImageHandler()


class TooltipOptions(Flag):
    NONE = 0
    FILENAME = auto()
    SIZE = auto()
    MODIFIED = auto()
    DIMENSIONS = auto()
    TYPE = auto()
    LABELS = auto()
    HIDE_MISSING = auto()

    DEFAULT = FILENAME | SIZE | MODIFIED | DIMENSIONS | TYPE | LABELS | HIDE_MISSING


class PathConversionDescriptor:
    def __set_name__(self, owner, name):
        self._name = '_' + name

    def __get__(self, instance, owner) -> Path:
        return getattr(instance, self._name)

    def __set__(self, instance, value: str | os.PathLike[str]) -> None:
        setattr(instance, self._name, Path(value))


@dataclass
class Thumb:
    path: PathConversionDescriptor = PathConversionDescriptor()
    mtime: int = -1
    size: int = -1
    _image: wx.Image = field(init=False, repr=False, hash=False)
    _dimensions: tuple[int, int] = field(
        init=False, repr=False, default=(0, 0), hash=False
    )
    _alpha: bool = field(init=False, repr=False, default=False, hash=False)
    _bitmap: wx.Bitmap | None = field(init=False, repr=False, default=None, hash=False)
    _valid_image: bool = field(init=False, repr=False, default=False, hash=False)
    text_color: wx.Colour | tuple[int, int, int] | str = field(
        default_factory=lambda: wx.NullColour, hash=False
    )
    load_from_system: InitVar[bool] = True

    def __post_init__(self, load_from_system) -> None:
        stat = None
        try:
            if self.mtime == -1 and load_from_system:
                stat = self.path.stat()
                self.mtime = stat.st_mtime_ns
            if self.size == -1 and load_from_system:
                stat = stat or self.path.stat()
                self.size = stat.st_size
        except FileNotFoundError:
            self.mtime = 0
            self.size = 0
        self._image = wx.Image(1, 1)

    @property
    def image(self) -> wx.Image:
        return self._image

    @property
    def alpha(self) -> bool:
        """Whether the image uses an alpha channel."""
        return self._alpha

    @property
    def dimensions(self) -> tuple[int, int]:
        """The dimensions of the image."""
        return self._dimensions

    def get_tooltip(self, options: TooltipOptions = TooltipOptions.DEFAULT) -> str:
        lines = []
        hide_missing = options & TooltipOptions.HIDE_MISSING
        show_label = options & TooltipOptions.LABELS
        if options & TooltipOptions.FILENAME:
            name = self.path.name
            if name or not hide_missing:
                if show_label:
                    lines.append(f'Filename: {name}')
                else:
                    lines.append(name)
        if options & TooltipOptions.SIZE:
            if self.size > 0 or not hide_missing:
                size = humanize.naturalsize(self.size)
                if show_label:
                    lines.append(f'Size: {size}')
                else:
                    lines.append(size)
        if options & TooltipOptions.MODIFIED:
            if self.mtime > 0 or not hide_missing:
                dt = datetime.datetime.fromtimestamp(self.mtime / 10**9)
                mtime = humanize.naturaltime(dt)
                if show_label:
                    lines.append(f'Modified: {mtime}')
                else:
                    lines.append(mtime)
        if options & TooltipOptions.DIMENSIONS:
            if self._dimensions != (0, 0) or not hide_missing:
                dimensions = ' x '.join(map(str, self._dimensions))
                if show_label:
                    lines.append(f'Dimensions: {dimensions}')
                else:
                    lines.append(dimensions)
        if options & TooltipOptions.TYPE and self._valid_image:
            handler: wx.ImageHandler | None = wx.Image.FindHandler(
                self._image.GetType()
            )
            if handler:
                _type = handler.GetName()
            else:
                _type = 'unknown'
            if show_label:
                lines.append(f'Type: {_type}')
            else:
                lines.append(_type)
        return '\n'.join(lines)

    def get_thumbnail(self, width: int, height: int) -> wx.Image:
        """Get a thumbnail of the image with the given size."""
        w, h = self._image.GetSize()
        if (w, h) != (width, height) and self._valid_image:
            scale = min(width / w, height / h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            return self._image.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
        return self._image

    def _would_resize_to(self, width: int, height: int) -> tuple[int, int]:
        """Calculate what size the bitmap would be resized to given a requested max
        size."""
        w, h = self._image.GetSize()
        if (w, h) != (width, height):
            scale = min(width / w, height / h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            return new_w, new_h
        return (w, h)

    def get_bitmap(self, width: int, height: int) -> wx.Bitmap:
        """Get a bitmap of the image with the given size."""
        if not self._bitmap or self._bitmap.GetSize() != self._would_resize_to(
            width, height
        ):
            self._bitmap = self.get_thumbnail(width, height).ConvertToBitmap()
        return self._bitmap

    def load(
        self, force: bool = False, handler: imagehandler.ImageHandler = _IMAGE_HANDLER
    ) -> None:
        """Load the image from disc. NOTE: Called from a thread,
        so atomic operations
        """
        if self._valid_image:
            if not force:
                return
            stat = self.path.stat()
            if (stat.st_mtime_ns, stat.st_size) == (self.mtime, self.size):
                return
        self._image, self._dimensions, self._alpha, self._valid_image = handler.load(
            self.path
        )
        #print('loaded self:', self.path, self._dimensions, self._valid_image)

    def rotate(
        self, ccw_angle: float, handler: imagehandler.ImageHandler = _IMAGE_HANDLER
    ) -> None:
        """Rotate the image counter-clockwise by an angle."""
        self._bitmap = None
        self._image = handler.rotate(self._image, ccw_angle)
        self._dimensions = tuple(self._image.GetSize())

    def highlight(
        self,
        width: int,
        height: int,
        factor: float,
        handler: imagehandler.ImageHandler = _IMAGE_HANDLER,
    ) -> wx.Bitmap:
        """Return a highlighted version of the thumbnail as a bitmap."""
        image = self.get_thumbnail(width, height)
        image = handler.highlight(image, factor)
        return image.ConvertToBitmap()

    def reflect(self, horizonal: bool = True, handler: imagehandler.ImageHandler = _IMAGE_HANDLER) -> None:
        self._bitmap = None
        self._image = handler.reflect(self._image, horizonal)
        self._dimensions = tuple(self._image.GetSize())
