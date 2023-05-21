# wxthumbnailctrl
A wx control for viewing thumbnails of images. This is a control similar to
[wx.lib.agw.thumbnailctrl](https://docs.wxpython.org/wx.lib.agw.thumbnailctrl.html),
but written with a few more options and optimizations to suit my needs.

The exposed method names are in Python's PEP8 naming style, as opposed to wxPython's
CamelCase style, with the exception of inherited methods.

## Inheritance
`ThumbnailCtrl` derives from [`wx.ScrolledWindow`](https://docs.wxpython.org/wx.ScrolledWindow.html).

## Events
The events emitted by this class are all of type `ThumbnailEvent`, which beyond the usual `wx.Event`
based methods and properties provide the following attribute:
* `ThumbnailEvent.thumbs: list[Thumb]` - A list of the `Thumb` instances related to the event.

The following events are emitted by this class:
* `EVT_THUMBCTRL_SELECTION_CHANGED`: Signals that the selected thumbnails have changed via user input. Not fired when selection changes via tha API methods. The `.thumbs` attribute holds the resulting selected thumbnails.
* `EVT_THUMBCTRL_CONTEXT_MENU`: Fired when a global context menu is requested due to right-clicking anywhere not on a thumbnail.
* `EVT_THUMBCTRL_ITEM_CONTEXT_MENU`: Fired when a context menu is requested due to right-clicking on a thumbnail. The `.thumbs` attribute will contains all of the currently selected thumbnails.
* `EVT_THUMBCTRL_ITEM_ACTIVATED`: Fired when the currently focused thumbnail is activated via pressing the Enter / Return key.
* `EVT_THUMBCTRL_HOVER_CHANGED`: Fired when the item under the mouse cursor has changed.
* `EVT_THUMBCTRL_IMAGES_DROPPED`: Fired to notify that new images have been added to the control via a drag-and-drop operation.
* `EVT_THUMBCTRL_IMAGES_REMOVED`: Fired to notify that images have been removed from the control via a drag-and-drop operation.
* `EVT_THUMBCTRL_IMAGE_LOADING_STARTED`: Notifies that a thumbnail has begun loading from disk. Multiple instances of this will be fired (one for each file to load).
* `EVT_THUMBCTRL_IMAGE_LOADING_DONE`: Notifies that a thumbnail has been fully loaded from disk. Multiple instance of this will be fired (one for each file loaded).

## Configuring
Since `ThumbnailCtrl` has many options for configuring, configuration is exposed via the `ThumbnailCtrl.Option` dataclass, with the following attributes:

Each thumbnail has a thin border drawn to help it stand out from the background:
* `thumb_outline_color_deselected: tuple[int, int, int] | tuple[int, int, int, int] | wx.Colour`: This is the border color used if the thumbnail is not selected, defaulting to a light grey color.
* `thumb_outline_color_selected: tuple[int, int, int] | tuple[int, int, int, int] | wx.Colour`: This is the border color used if the thumbnail is selected, defaulting to a light blue color.

Each thumbnail can be highlighted by a box when hovered over via the mouse:
* `thumb_highlight_color_deselected: tuple[int, int, int] | tuple[int, int, int, int] | wx.Colour`: The color to use when the thumbnail is deselected, defaulting to a light blue color.
* `thumb_highlight_color_selected: tuple[int, int, int] | tuple[int, int, int, int] | wx.Colour`: The color to use when the thumbnail is selected, default to a a light blue color slightly darker than the deselected color.
* `thumb_highlight_selected_border_color: tuple[int, int, int] | tuple[int, int, int, int] | wx.Colour`: The edge of the highlight border can be customized for selected thumbnails. Defaults to a slighttly darker blue than the highlight color.
* `show_highlighted_area: bool`: Whether the highlight box should be drawn or now, defaults to `True`.
* `image_highligh_factor: float`: In addition to the drawn box, the image itself can have its brightness increased to make it stand out. This is a multiplicative factor (so `1.0` means no change, values less than `1.0` result in a darkening). Defaults to `1.01`.

Some other thumbnail drawing options:
* `show_image_shadow: bool`: A drop shadow can be drawn behind the thumbnails to give a small 3D effect. Defaults to `True`.
* `show_filenames: Callable[[Thumb], str] | Literal[False]`: If `False`, no filenames will be shown (below the thumbnail). Otherwise this is a callable taking the `Thumb` object and returning the text to use for the filename, defaulting to the equivalent of `pathlib.Path.name` for a `Thumb` object.
* `sort_key: Callable[[Thumb], Any] | None`: A key function (as would be passed to `list.sort`) used to provide automatic sorting of the thumbnails. Useful when allowing drag-and-drop, to automatically sort newly-added thumbnails. For example, the following could be used to sort by filename using the `natsort` library: `options.sort_key = natsort.os_sortkey_gen(key=lambda thumb: thumb.path)`.

Some basic colors can also be configured:
* `background_color: tuple[int, int, int] | tuple[int, int, int, int] | wx.Colour`: The background color to use for the control. Defaults to the `wx.Window` background color.
* `text_color: tuple[int, int, int] | tuple[int, int, int, int] | wx.Colour`: The color to use for text drawn (ie: for filenames). Defaults to the default `wx.Window` text color.

The tooltip shown when mousing over a thumbnail can be customized:
* `show_tooltip: bool`: Whether to show a tooltip or not, defaults to `True`.
* `tooltip_delay_ms: int`: How long to wait after hovering until the tooltip pops up, defaults to `1000` ms (`1` second).
* `tooltip_options: TooltipOption`: The options used when constructing the tooltip text (see `Thumb.get_tooltip`).

General size and spacing of the thumbnails can be configured:
* `thumb_spacing: int`: Minimum spacing (in pixels) to use between each thumbnail. Defaults to `10`.
* `thumb_size: tuple[int, int]`: The size of thumbnail to show, in pixels. Defaults to `96` by `80` pixels. Note the size of the thumbnails can be changed via zooming in and out, this is just the initial size.
* `zoom_rate: float`: The multiplicative factor to use when zooming in to determine the new thumbnail size. The inverse is used when zooming out (ie: the size is divided by the `zoom_rate`). Defaults to `1.4`, a `40%` increase in size.

Drag-and-drop can be configured:
* `allow_dragging: bool`: Determines if thumbnails are allowed to be dragged out of the control. When dropped on another target. Defaults to `False`. When dragging is enabled, if the target control accepts the files, the thumbnails will be removed from the control.
* `accepts_files: bool`: Determines if files are allowed to be dropped onto the control. When dropped, any images will be added to the control as thumbnails. Defaults to `False`.

How thumbnails are loaded can be configured:
* `image_handler: ImageHandler`: The object responsible for loading the images from disk. The default handler uses wxPython's image handling and loading methods to load images (see `ImageHandler`).
* `image_parallelism: int`: Images are loaded using a thread pool so as not to lock up the GUI. This customizes how many worker threads are used when loading, defaulting to `5`.

## The `Thumb` class
Thumbnails are stored internally via the `Thumb` class, a small dataclass holding the image itself and some stats about the image.  They have the following attributes and methods:
* `Thumb.path: Path`: The `pathlib.Path` instance pointing to the file on disk.
* `mtime: int`: The last modified time of the file.
* `size: int`: The size of the file.
* `dimensions: tuple[int, int]`: The dimensions of the image.
* `image: wx.Image`: The loaded image data.
* `alpha: bool`: Whether the image has an alpha-channel.
* `get_tooltip(self, options: TooltipOptions) -> str`: Called by the `ThumbnailCtrl` to get the tooltip text to use. This can be overidden to provide your own custom tooltips. The options available are:
  - `FILENAME`: Show the filename in the tooltip.
  - `SIZE`: Show the file size in the tooltip.
  - `MODIFIED`: Show the modification time in the tooltip.
  - `DIMENSIONS`: Show the image dimensions in the tooltip.
  - `TYPE`: Show the image file type in the tooltip.
  - `LABELS`: Show label text before each of the above, ex: `Filename: image.jpg`
  - `HIDE_MISSING`: Only show the above if the information is present. For example if the image wasn't loaded from a file on disk, `mtime` and `path` may be invalid, and so not shown.
  - `DEFAULT`: All of the above options.
* `get_bitmap(self, width: int, height: int) -> wx.Bitmap`: Use by the `ThumbnailCtrl` to get a `wx.Bitmap` version of the image scaled to the appropriate size for drawing on screen.

## The `ImageHandler` class
An `ImageHandler` is used to load images (usually from disk).  You can implement your own image handler to load images from elsewhere. For example, an `ImageHandler` could be written that handles URLs as image paths to grab images from the internet. All `ImageHandler` derived classes must implement the following protocol:
* `load_image(self, image_path: str | os.PathLike[str]) -> wx.Image`: Load the image located at `image_path`, returning it in a `wx.Image` instance.
* `highlight(self, image: wx.Image, factor: float) -> wx.Image`: Brighten the given image by the given factor.
* `rotate(self, image: wx.Image, ccw_degrees: float) -> wx.Image`: Rotate the given image counter-clockwise by `ccw_degrees` degrees, returning the result in a new `wx.Image` instance.

The default image handler, `NativeImageHandler`, simply loads the file using `wx.Image`. As such, it can handle any image supported by wxPython.

Some additional image handlers provide more functionality:
* `CachingImageHandler(self, handler: ImageHandler, cache_size: int)`: Create a image handler that caches the loading of images from another image handler. Caching is done via an LRU cache on the `load_image` method of the wrapped handler. This can be useful using a single control to switch between differing sets of thumbnails, keeping the images in memory between viewings.
* `MaxSizeImageHandler(self, handler: ImageHandler, max_w: int | None = None, max_h: int | None = None)`: Create an image handler that resizes loaded images so the are no larger than the specified size after loading. If the specified sizes are not provided, uses the screen dimensions as the maximum size. This can be useful to reduce memory used when loading a large number of thumbnails in a single control. For example, loading a 10k by 10k image and keeping it in memory is probably not needed when viewing it as a thumbnail. With the zoom feature of the control, the largest size needed is probably smaller than the screen size. However you can go smaller, to reduce the consumed memory even further, in which case zooming in past that size will result in scaled up images, even if the image on disk is larger.

Finally, if an image handler encounters an error loading an image, on Windows it will attempt to get an icon for the image type to use instead.

# The `ThumbnailCtrl`
The following public API is presented:
* `__init__(self, parent: wx.Window, id: int = wx.ID_ANY, pos: tuple[int, int] | wx.Point = wx.DefaultPosition, size: tuple[int, int] | wx.Size = wx.DefaultSize, style: int = 0, options: ThumbnailCtrl.Options = DEFAULT_OPTIONS)`: Create a new control. The standard wx parameters `parent`, `id`, `pos`, `size`, and `style` are as for any other `wx.Window` instance. The `options` parameter and its defaults are described above.
* `get_hovered(self) -> list[int]`: Return the indices of the thumbnails that are currently considered hovered over by the mouse. Note this is a list of indicies, not a single index - see `set_hovered`.
* `set_hovered(self, indices: Iterable[int]) -> None`: Set which thumbnails are considered to hovered over by the mouse. This can be used (along with `EVT_THUMBCTRL_HOVER_CHANGED`) to cause multiple images to be highlighted when mousing over a single image. And example use case could be highlighting all images that look similar when mousing over one of them. Calling this does not fire the `EVT_THUMBCTRL_HOVER_CHANGED` event.
* `zoom(self, *, out: bool = False) -> None`: Call this to cause the thumbnails to be zoomed in or out. Thumbnails will not be zoomed in so large that they cannot fit on the screen, nor will they be zoomed out smaller than 30 pixels in either dimension.
* `get_options(self) -> ThumbnailCtrl.Options`: Get a copy of the currently used configuration options.
* `set_options(self, options: ThumbnailCtrl.Options) -> None`: Set the configuration options for this control. Some options are validated for correct parameters (for example, `thumb_spacing` will be clamped to no smaller than `4` pixels). Note in many cases this will trigger a refresh of the control.
* `get_selections(self) -> set[int]`: Get the indices of the currently selected thumbnails.
* `is_selected(self, item: int) -> bool`: Tests if the thumbnail at the given index is selected. This can be faster than `if item in self.get_selections()`, as it avoids creating a copy of the internal state.
* `select(self, indicies: Iterable[int], *, toggle: bool = False) -> None`: Changes which thumbnails are currently selected. If `toggle` is `False` (the default), simply sets the selected thumnails to those that are specified. If `toggle` is `True`, instead toggles the selection state of each index provided. This *does* fire the `EVT_THUMBCTRL_SELECTION_CHANGED` event.
* `select_thumbs(self, thumbs: Iterable[Thumb]) -> None`: Similar to `select`, but without the toggling functionality and also does *not* fire a `EVT_THUMBCTRL_SELECTION_CHANGED` event.
* `select_all(self) -> None`: Equivalent to `self.select(range(len(self.get_thumbs())))`, selecting all thumbnails and firing the `EVT_THUMBCTRL_SELECTION_CHANGED` event.
* `focus(self, item: int) -> None`: Sets which thumbnail is considered to have focus for keyboard and mouse events.
* `get_focus(self) -> int`: Get the index of the thumbnail which is considered to have focus, or `-1` if none of them do.
* `scroll_to_thumb(self, index: int) -> None`: Scrolls the control to ensure the given thumbnail index is visible.
* `set_thumb_size(self, width: int, height: int) -> None`: A shorthand method for changing thumbnail size, rather than getting the `ThumbnailCtrl.Options` instance via `get_options`, changing the size, then setting via `set_options`.
* `HitTest(self, x: int, y: int) -> HitTest`: The only CamelCase method that is not wx-provided, to be similar to all other wx classes that provide a hit-test method. Given a mouse coordinates (client coordinates), for example as obtained via `wx.MouseEvent`, determines what thumbnail (if any) index the mouse is over, what row and column of the control the mouse is over, as well as some flags to further narrow down where in relation to that row and column the mouse is. The returned `HitTest` dataclass has the following attributes:
  - `HitTest.index: int`: The thumbnail index under the given point, or `-1` if none.
  - `HitTest.column: int`: The thumbnail column (starting at `0` on the far left) under the given point.
  - `HitTest.row: int`: The thumbnail row (starting at `0` at the top) under the given point.
  - `HitTest.flags: HitFlag`: One or more of `LEFT`, `RIGHT`, `ABOVE`, `BELOW`, `CENTER`, or `NOWHERE`. The flag `CENTER` means the point is over the area reserved for the thumbnail, while the directional ones indicate the point is closest to the given row and column, but not actually over the a thumbnail there. One case this can commonly occur is for mouse hit-tests over the last row when the row is not fully of images.
* `has_thumb(self, path: str | os.PathLike[str]) -> bool`: Test whether any of the `Thumb` thumbnail objects in the control have a path matching the givem path.
* `get_index(self, thumb: Thumb) -> int:` Get the index of the given `Thumb` object in the control, or `-1` if it is not in the control. Slightly faster than `self.get_thumbs().index(thumb)`, as it doesn't make a copy of the internal thumbnail storage.
* `get_count(self) -> int`: Get how many thumbnails are in the control. Slightly faster than `len(self.get_thumbs())` as it avoids copying the internal thumbnail storage.
* `get_thumb(self, index: int | str | os.PathLike[str]) -> Thumb`: Return the thumbnail object associated with the given index, or the thumbnail object with the given path. Raises a `KeyError` if there is not thumbnail at the index or with the given path.
* `set_thumb(self, index: int, thumb: Thumb) -> None`: Replace the thumbnail at the given index with a new thumbnail.
* `get_thumbs(self) -> list[Thumb]`: Return a (shallow) copy of the internally stored thumbnails.
* `set_thumbs(self, thumbs: Iterable[Thumb]) -> None`: Set what thumbnails are shown in the control. Triggers a control refresh.
* `add_thumbs(self, thumbs: list[Thumb], select: bool = False) -> None`: Add thumbnails into the control after all current thumbnails. If `select` is `True`, also sets the selection to those thumbnails, firing a `EVT_THUMBCTRL_SELECTION_CHANGED` event.
* `insert_thumbs(self, index: int, thumbs: list[Thumb], select: bool = False) -> None`: Like `add_thumbs`, but inserts the thumbnails before any thumbnail at position `index`.
* `remove_thumbs(self, thumbs: Iterable[Thumb]) -> None`: Remove the given thumbnails from the control. Raises a `KeyError` if any of the thumbnails are not present in the control.
* `__contains__(self, thumb: Thumb) -> bool`: Test if a thumbnail is in the control, as in `if thumb in control: ...`.
* `shutdown(self) -> None`: Can be called manually to stop the thread-pool used for loading thumbnails. Can be useful when changing the thumbnail contents to new thumbnails. While not strictly necessary (the control will still function properly in that case), if the control previously had many thumbnails (say, `1000+`) and was still loading them, this can free up the thread-pool to load the new images quicker. This will also prevent (most) of the `EVT_THUMBCTRL_IMAGE_LOADING` and `EVT_THUMBCTR_IMAGE_LOADING_DONE` events from firing from those previously queued images. Note this is called automatically on closing the control so in most cases this method is only needed if changing the contents of the control and many images are involved. Also note, if you bind to this controls `EVT_CLOSE` event handler, make sure you call this yourself if you do not call `event.Skip()`.
* `refresh_thumbs(self, indices: Iterable[int], reload: bool = False) -> None`: Force a redraw of the thumbnails at the given indices. If `reload` is `True`, also reload the images from disk. This can be useful for example if you have changed the contents of the file and want this to be reflected in the control.

