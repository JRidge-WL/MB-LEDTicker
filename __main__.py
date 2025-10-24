from scripts import getTime, validateSchema # Import all custom scripts
from scripts.draw import draw_layout
import time
import os

def is_raspberry_pi():
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
        return "Raspberry Pi" in cpuinfo or "BCM" in cpuinfo
    except FileNotFoundError:
        return False

def unpack_layout(layout: dict, panel_width: int, panel_height: int):
    """
    Unpack a validated layout into a flat list of drawable objects with pixel coordinates.

    Args:
        layout (dict): The validated layout object (from validateSchema).
        panel_width (int): Width of the LED panel in pixels.
        panel_height (int): Height of the LED panel in pixels.

    Returns:
        list[dict]: Flat list of objects (Textbox, ScrollingTextbox, Image, Alert)
                    with resolved pixel positions and sizes.
    """

    def parse_dimension(value: str, total: int) -> int:
        """Convert '50%' or '32px' into an integer pixel value."""
        if value.endswith("%"):
            return int(float(value[:-1]) / 100 * total)
        elif value.endswith("px"):
            return int(value[:-2])
        else:
            raise ValueError(f"Invalid dimension: {value}")

    def apply_alignment(x, y, w, h, horiz, vert):
        """Adjust x,y based on horizontal/vertical origin."""
        if horiz == "centre":
            x = x - w // 2
        elif horiz == "right":
            x = x - w
        # left = default

        if vert == "centre":
            y = y - h // 2
        elif vert == "bottom":
            y = y - h
        # top = default

        return x, y

    def recurse(objects, parent_w, parent_h, parent_x=0, parent_y=0):
        flat = []
        for obj in objects:
            # Resolve dimensions relative to parent
            x = parse_dimension(obj["x"], parent_w)
            y = parse_dimension(obj["y"], parent_h)
            w = parse_dimension(obj["width"], parent_w)
            h = parse_dimension(obj["height"], parent_h)

            # Position relative to parent
            abs_x = parent_x + x
            abs_y = parent_y + y

            horiz = obj.get("horizontal", "left")
            vert = obj.get("vertical", "top")

            # Apply alignment
            abs_x, abs_y = apply_alignment(abs_x, abs_y, w, h, horiz, vert)

            if obj["type"] == "Group":
                # Recurse into children, using this group's box as new parent
                flat.extend(recurse(
                    obj["objects"],
                    parent_w=w,
                    parent_h=h,
                    parent_x=abs_x,
                    parent_y=abs_y
                ))
            else:
                # Leaf object: add to flat list
                flat.append({
                    "type": obj["type"],
                    "x": abs_x,
                    "y": abs_y,
                    "width": w,
                    "height": h,
                    "text": obj.get("text"),
                    "path": obj.get("path"),
                    "font": obj.get("font"),
                    "fgColor": obj.get("fgColor"),
                    "bgColor": obj.get("bgColor"),
                    "scrollSpeed": obj.get("scrollSpeed"),
                    "dataSource": obj.get("dataSource"),
                    "dataParams": obj.get("dataParams")
                })
        return flat

    return recurse(layout["objects"], panel_width, panel_height)

if is_raspberry_pi():
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    print("Running on Pi - Using RGBMatrix library.")
else:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
    print("Running on non-Pi system: Emulating RGBMatrix library.")

# Configuration for 8x1 panels of 64x32 each
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'  # Use 'regular' for emulator

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# Load font
font = graphics.Font()
font.LoadFont("./fonts/7x13.bdf")  # Ensure this path is correct

# Set text color
textColor = graphics.Color(255, 255, 255)

# Text to scroll
message = "Current time in Portland, USA!"
pos = canvas.width

layout = validateSchema.validate_layout("./layouts/1.json")
objects = unpack_layout(layout, panel_width=options.cols * options.chain_length, panel_height=options.rows)
matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()
scroll_state = {}

while True:
    canvas, scroll_state = draw_layout(matrix, canvas, objects, scroll_state=scroll_state)
    time.sleep(0.03)