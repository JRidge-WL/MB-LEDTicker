import os
import time
from scripts import getTime, validateSchema  # your custom modules

# --- Platform detection ---
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

# --- Fonts directory ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")

# --- Debug colours ---
DEBUG_COLOURS = [
    graphics.Color(255, 0, 0), graphics.Color(0, 255, 0), graphics.Color(0, 0, 255),
    graphics.Color(255, 255, 0), graphics.Color(255, 0, 255), graphics.Color(0, 255, 255),
    graphics.Color(255, 128, 0), graphics.Color(128, 0, 255)
]

# --- ClippedCanvas helper ---
class ClippedCanvas:
    def __init__(self, real_canvas, offset_x, offset_y, width, height):
        self._canvas = real_canvas
        self.offset_x, self.offset_y = offset_x, offset_y
        self.width, self.height = width, height

    def SetPixel(self, x, y, r, g, b):
        if 0 <= x < self.width and 0 <= y < self.height:
            self._canvas.SetPixel(self.offset_x + x, self.offset_y + y, r, g, b)

    def Clear(self):
        for lx in range(self.width):
            for ly in range(self.height):
                self._canvas.SetPixel(self.offset_x + lx, self.offset_y + ly, 0, 0, 0)

# --- Layout unpacker ---
def unpack_layout(layout: dict, panel_width: int, panel_height: int):
    def parse_dimension(value: str, total: int) -> int:
        if value.endswith("%"):
            return int(float(value[:-1]) / 100 * total)
        elif value.endswith("px"):
            return int(value[:-2])
        else:
            raise ValueError(f"Invalid dimension: {value}")

    def apply_alignment(x, y, w, h, horiz, vert):
        if horiz == "centre":
            x -= w // 2
        elif horiz == "right":
            x -= w
        if vert == "centre":
            y -= h // 2
        elif vert == "bottom":
            y -= h
        return x, y

    def recurse(objects, parent_w, parent_h, parent_x=0, parent_y=0):
        flat = []
        for obj in objects:
            x = parse_dimension(obj["x"], parent_w)
            y = parse_dimension(obj["y"], parent_h)
            w = parse_dimension(obj["width"], parent_w)
            h = parse_dimension(obj["height"], parent_h)

            abs_x, abs_y = parent_x + x, parent_y + y
            abs_x, abs_y = apply_alignment(abs_x, abs_y, w, h,
                                           obj.get("horizontal", "left"),
                                           obj.get("vertical", "top"))

            if obj["type"] == "Group":
                flat.extend(recurse(obj["objects"], w, h, abs_x, abs_y))
            else:
                flat.append({
                    "type": obj["type"], "x": abs_x, "y": abs_y,
                    "width": w, "height": h,
                    "text": obj.get("text"), "path": obj.get("path"),
                    "font": obj.get("font"), "fgColor": obj.get("fgColor"),
                    "bgColor": obj.get("bgColor"), "scrollSpeed": obj.get("scrollSpeed"),
                    "dataSource": obj.get("dataSource"), "dataParams": obj.get("dataParams")
                })
        return flat

    return recurse(layout["objects"], panel_width, panel_height)

# --- Drawing logic ---
def draw_layout(matrix, canvas, objects, fonts_cache=None, scroll_state=None, debug=False):
    if fonts_cache is None:
        fonts_cache = {}
    if scroll_state is None:
        scroll_state = {}

    canvas.Clear()

    for idx, obj in enumerate(objects):
        if obj["type"] not in ("Textbox", "ScrollingTextbox", "Alert"):
            continue

        font_name = obj.get("font", "4x6.bdf")
        font_path = font_name if os.path.isabs(font_name) else os.path.join('./fonts/', font_name)

        if font_path not in fonts_cache:
            f = graphics.Font()
            f.LoadFont(font_path)
            fonts_cache[font_path] = f
        font = fonts_cache[font_path]

        fg = obj.get("fgColor", "#FFFFFF")
        r, g, b = int(fg[1:3], 16), int(fg[3:5], 16), int(fg[5:7], 16)
        color = graphics.Color(r, g, b)

        text = obj.get("text", "")
        x0, y0, w, h = obj["x"], obj["y"], obj["width"], obj["height"]
        local = ClippedCanvas(canvas, x0, y0, w, h)
        y_baseline_local = h - 2

        if obj["type"] == "ScrollingTextbox":
            if idx not in scroll_state:
                scroll_state[idx] = w
            pos_local = scroll_state[idx]
            # draw directly on the real canvas, offset into the object's box
            text_len = graphics.DrawText(canvas, font,
                                        x0 + pos_local,
                                        y0 + y_baseline_local,
                                        color, text)
            scroll_state[idx] = pos_local - 1
            if pos_local + text_len < 0:
                scroll_state[idx] = w
        else:
            graphics.DrawText(canvas, font,
                  x0,
                  y0 + y_baseline_local,
                  color, text)

        if debug:
            dbg_color = DEBUG_COLOURS[idx % len(DEBUG_COLOURS)]
            for px in range(x0, x0 + w):
                canvas.SetPixel(px, y0, dbg_color.red, dbg_color.green, dbg_color.blue)
                canvas.SetPixel(px, y0 + h - 1, dbg_color.red, dbg_color.green, dbg_color.blue)
            for py in range(y0, y0 + h):
                canvas.SetPixel(x0, py, dbg_color.red, dbg_color.green, dbg_color.blue)
                canvas.SetPixel(x0 + w - 1, py, dbg_color.red, dbg_color.green, dbg_color.blue)

    canvas = matrix.SwapOnVSync(canvas)
    return canvas, scroll_state

# --- Main setup ---
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

layout = validateSchema.validate_layout("./layouts/1.json")
objects = unpack_layout(layout, panel_width=options.cols * options.chain_length,
                        panel_height=options.rows)

fonts_cache = {}
scroll_state = {}

while True:
    canvas, scroll_state = draw_layout(matrix, canvas, objects,
                                       fonts_cache=fonts_cache,
                                       scroll_state=scroll_state)
    time.sleep(0.03)