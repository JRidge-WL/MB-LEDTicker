import os
import time

def is_raspberry_pi():
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
        return "Raspberry Pi" in cpuinfo or "BCM" in cpuinfo
    except FileNotFoundError:
        return False

if is_raspberry_pi():
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    print("Running on Pi - Using RGBMatrix library.")
else:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
    print("Running on non-Pi system: Emulating RGBMatrix library.")

# Resolve fonts directory relative to this file
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(PROJECT_ROOT, "..", "fonts")

# Simple colour palette for debug boxes
DEBUG_COLOURS = [
    graphics.Color(255, 0, 0),     # red
    graphics.Color(0, 255, 0),     # green
    graphics.Color(0, 0, 255),     # blue
    graphics.Color(255, 255, 0),   # yellow
    graphics.Color(255, 0, 255),   # magenta
    graphics.Color(0, 255, 255),   # cyan
    graphics.Color(255, 128, 0),   # orange
    graphics.Color(128, 0, 255),   # purple
]

class ClippedCanvas:
    """
    A small proxy canvas that:
    - Offsets drawing by (offset_x, offset_y)
    - Clips all pixels to a rectangle of width x height
    - Forwards SetPixel to the real canvas only within bounds
    """
    def __init__(self, real_canvas, offset_x, offset_y, width, height):
        self._canvas = real_canvas
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.width = width
        self.height = height

    def SetPixel(self, x, y, r, g, b):
        # Clip to local bounds
        if 0 <= x < self.width and 0 <= y < self.height:
            self._canvas.SetPixel(self.offset_x + x, self.offset_y + y, r, g, b)

    # Optional convenience methods, not required by graphics.DrawText,
    # but useful if you want to draw lines or clear inside the box.
    def Clear(self):
        for lx in range(self.width):
            for ly in range(self.height):
                self._canvas.SetPixel(self.offset_x + lx, self.offset_y + ly, 0, 0, 0)

def draw_layout(matrix, canvas, objects, fonts_cache=None, scroll_state=None, debug=True):
    """
    Draw text objects (Textbox, ScrollingTextbox, Alert) on the LED matrix,
    using clipped sub-canvases so nothing draws outside each object's box.
    """
    if fonts_cache is None:
        fonts_cache = {}
    if scroll_state is None:
        scroll_state = {}

    canvas.Clear()

    for idx, obj in enumerate(objects):
        if obj["type"] not in ("Textbox", "ScrollingTextbox", "Alert"):
            continue  # skip non-text for now

        # Get font name from object, default to 7x13.bdf
        font_name = obj.get("font", "7x13.bdf")

        # Build absolute path if not already absolute
        font_path = font_name
        if not os.path.isabs(font_name):
            font_path = os.path.join(FONTS_DIR, font_name)

        # Load font if not cached
        if font_path not in fonts_cache:
            f = graphics.Font()
            f.LoadFont(font_path)
            fonts_cache[font_path] = f
        font = fonts_cache[font_path]

        # Default to white if no fgColor
        fg = obj.get("fgColor", "#FFFFFF")
        r = int(fg[1:3], 16)
        g = int(fg[3:5], 16)
        b = int(fg[5:7], 16)
        color = graphics.Color(r, g, b)

        text = obj.get("text", "")

        # Object bounds
        x0, y0 = obj["x"], obj["y"]
        w, h = obj["width"], obj["height"]

        # Create a clipped canvas for this object
        local = ClippedCanvas(canvas, x0, y0, w, h)

        # Compute a baseline inside the local canvas
        # Note: graphics.DrawText draws with y at baseline; subtract 2 to keep text inside height.
        y_baseline_local = h - 2

        if obj["type"] == "ScrollingTextbox":
            # Track scroll position per object (in local coordinates)
            if idx not in scroll_state:
                scroll_state[idx] = w  # start from just outside the right edge

            pos_local = scroll_state[idx]
            text_len = graphics.DrawText(local, font, pos_local, y_baseline_local, color, text)
            scroll_state[idx] = pos_local - 1

            # Reset when text fully scrolled off to the left
            if pos_local + text_len < 0:
                scroll_state[idx] = w

        else:
            # Regular text or alert: draw at local x=0
            graphics.DrawText(local, font, 0, y_baseline_local, color, text)

        # --- Debug bounding box (on the real canvas) ---
        if debug:
            dbg_color = DEBUG_COLOURS[idx % len(DEBUG_COLOURS)]
            # top and bottom
            for px in range(x0, x0 + w):
                canvas.SetPixel(px, y0, dbg_color.red, dbg_color.green, dbg_color.blue)
                canvas.SetPixel(px, y0 + h - 1, dbg_color.red, dbg_color.green, dbg_color.blue)
            # left and right
            for py in range(y0, y0 + h):
                canvas.SetPixel(x0, py, dbg_color.red, dbg_color.green, dbg_color.blue)
                canvas.SetPixel(x0 + w - 1, py, dbg_color.red, dbg_color.green, dbg_color.blue)

    canvas = matrix.SwapOnVSync(canvas)
    return canvas, scroll_state