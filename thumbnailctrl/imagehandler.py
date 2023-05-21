"""
Handlers for loading and manipulating images.
"""
__all__ = [
    'ImageHandler',
    'NativeImageHandler',
    'CachingImageHandler',
    'MaxSizeImageHandler',
]

import functools
import math
import os
from enum import Enum, auto
from typing import Protocol, TypeAlias

import wx

from . import data

StrPath: TypeAlias = str | os.PathLike[str]


class IconSize(Enum):
    SMALL = auto()
    LARGE = auto()
    SYSTEM = auto()


class ImageHandler(Protocol):
    def load(self, image_path: StrPath) -> tuple[wx.Image, tuple[int, int], bool, bool]:
        """Load and image from file."""
        try:
            image = self.load_image(image_path)
        except:
            image = data._FILE_BROKEN.getImage()
            valid = False
        else:
            if not (valid := image.IsOk()):
                image = get_icon(image_path)
        size = image.GetSize()
        return image, (size[0], size[1]), image.HasAlpha(), valid

    def load_image(self, image_path: StrPath) -> wx.Image:
        ...

    def highlight(self, image: wx.Image, factor: float) -> wx.Image:
        ...

    def rotate(self, image: wx.Image, ccw_degrees: float) -> wx.Image:
        ...


class CachingImageHandler(ImageHandler):
    def __init__(self, handler: ImageHandler, cache_size: int) -> None:
        self.load_image = functools.lru_cache(maxsize=cache_size)(handler.load_image)
        self.highlight = handler.highlight
        self.rotate = handler.rotate


class MaxSizeImageHandler(ImageHandler):
    def __init__(
        self, handler: ImageHandler, max_w: int | None = None, max_h: int | None = None
    ) -> None:
        self.handler = handler
        self.max_w = max_w
        self.max_h = max_h
        self.highlight = handler.highlight
        self.rotate = handler.rotate

    def load_image(self, image_path: StrPath) -> wx.Image:
        image = self.handler.load_image(image_path)
        if image.IsOk():
            if self.max_w is None or self.max_h is None:
                screen_w, screen_h = wx.GetDisplaySize()
                max_w = self.max_w or screen_w
                max_h = self.max_h or screen_h
            else:
                max_w = self.max_w
                max_h = self.max_h
            if image.Width > max_w or image.Height > max_h:
                ratio = min(max_w / image.Width, max_h / image.Height)
                w = int(image.Width * ratio)
                h = int(image.Height * ratio)
                image.Rescale(w, h, wx.IMAGE_QUALITY_HIGH)
        return image


class NativeImageHandler(ImageHandler):
    """ImageHandler that loads and manipulates images using wxPython's built in
    image methods.
    """

    def load_image(self, image_path) -> wx.Image:
        # Temporarily disable logging, as images with errors or missing files
        # cause popups - we'll check that later with image.IsOk()
        no_log = wx.LogNull()
        try:
            return wx.Image(os.fspath(image_path))
        finally:
            del no_log  # Check if needed: making sure it gets deleted immediately


    def highlight(self, image: wx.Image, factor: float) -> wx.Image:
        """Adjust the brightness of an image by scaling the channels by a given
        factor.
        """
        return image.AdjustChannels(factor, factor, factor)

    def rotate(self, image: wx.Image, ccw_degrees: float) -> wx.Image:
        """Rotate an image counter-clockwise by a given angle in degress."""
        rads = math.radians(ccw_degrees)
        return image.Rotate(rads, image.GetSize(), True)


try:
    import ctypes
    import winreg
    from pathlib import Path

    import win32gui

    def enum_key_values(key: winreg.HKEYType):
        _, n, _ = winreg.QueryInfoKey(key)
        for i in range(n):
            yield winreg.EnumValue(key, i)

    def icon_to_image(icon: wx.Icon) -> wx.Image:
        """Convert a wx.Icon to a wx.Image."""
        bitmap = wx.Bitmap(wx.NullBitmap)
        bitmap.CopyFromIcon(icon)
        return bitmap.ConvertToImage()

    def get_icon_from_location(location: str) -> wx.Image | None:
        if ',' in location:
            location, index = location.split(',')
            index = int(index.strip())
            hLarge, hSmall = win32gui.ExtractIconEx(location, index)
            icon = wx.Icon()
            icon.CreateFromHICON(hLarge[0])
            win32gui.DestroyIcon(hSmall[0])
            #win32gui.DestroyIcon(hLarge[0])
            if icon.IsOk():
                return icon_to_image(icon)
            else:
                return None
        else:
            return wx.Image(location)

    def get_icon_explorer_exts(ext: str) -> wx.Image | None:
        """Get the file icon by looking at Explorer's Open With list."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                f'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext}\\OpenWithProgIds',
            ) as key:
                return get_icon_from_progids_key(key)
        except FileNotFoundError:
            pass

    def get_icon_openwith(ext: str) -> wx.Image | None:
        """Get the file icon by looking at the association's Open With list."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT, f'{ext}\\OpenWithProgIds'
            ) as key:
                return get_icon_from_progids_key(key)
        except FileNotFoundError:
            pass

    def get_icon_from_progids_key(key: winreg.HKEYType) -> wx.Image | None:
        for name, _, type_ in enum_key_values(key):
            if type_ == winreg.REG_NONE and name:
                if icon := get_icon_from_prog_id(name):
                    return icon
        return None

    def get_icon_from_prog_id(prog_id: str) -> wx.Image | None:
        indirect_locations = []
        try:
            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT, f'{prog_id}\\DefaultIcon'
            ) as key:
                for name, value, type_ in enum_key_values(key):
                    if not name and type_ == winreg.REG_SZ:
                        indirect_locations.append(value)
        except FileNotFoundError:
            pass
        locations = []
        for ilocation in indirect_locations:
            dll = ctypes.WinDLL('shlwapi.dll')
            res = ctypes.create_unicode_buffer(1024)
            loc = ctypes.c_wchar_p(ilocation)
            dll.SHLoadIndirectString(loc, ctypes.byref(res), 1024, None)
            locations.append(res.value)
        for location in locations:
            if (image := get_icon_from_location(location)):

                if image.IsOk():
                    return image

    def get_icon_from_association(ext: str) -> wx.Image | None:
        """Get the icon from the file associations's default icon."""
        try:
            assoc = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, ext)
            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT, f'{assoc}\\DefaultIcon'
            ) as key:
                for name, value, type_ in enum_key_values(key):
                    if not name and type_ == winreg.REG_SZ:  # Default value
                        return get_icon_from_location(value)
        except FileNotFoundError:
            pass

    def get_icon(path: StrPath, size: IconSize = IconSize.SYSTEM) -> wx.Image:
        path = Path(path)
        ext = path.suffix.lower()
        # First methods work with UWP apps, so try them first
        icon = get_icon_explorer_exts(ext)
        if not icon:
            icon = get_icon_openwith(ext)
        if not icon:
            icon = get_icon_from_association(ext)
        if not icon:
            icon = data._FILE_BROKEN.GetImage()
        return icon

except ImportError:

    def get_icon(path: StrPath, size: IconSize = IconSize.SYSTEM) -> wx.Image:
        return data._FILE_BROKEN.GetImage()
