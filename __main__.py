import os
import time
from scripts import validateSchema  # your custom modules
import statistics, warnings, math, asyncio
import re, math
import scripts.api
from scripts.api import getTime, getNews, getTeams # regex
from collections import deque
from datetime import datetime
from PIL import Image, ImageDraw

NewsParser = scripts.api.getNews.NewsParser()
TeamsParser = scripts.api.getTeams.TeamsParser()

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
async def unpack_layout(layout: dict, panel_width: int, panel_height: int):
    def parse_dimension(value: str, total: int) -> int:
        if value.endswith("%"):
            return int(float(value[:-1]) / 100 * total)
        elif value.endswith("px"):
            return int(value[:-2])
        else:
            raise ValueError(f"Invalid dimension: {value}")

    def apply_alignment(x, y, w, h, horiz, vert):
        if horiz == "center":
            x -= w // 2
        elif horiz == "right":
            x -= w
        if vert == "center":
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
                    "dataSource": obj.get("dataSource"), "dataParams": obj.get("dataParams"),
                    "onScrollEnd": obj.get("onScrollEnd"),
                    "text_align": obj.get("text_align", "left")
                })
        return flat

    return recurse(layout["objects"], panel_width, panel_height)

# --- Check API Calls ---
async def checkAPICalls(inputText, returnText = True):

    api_list = re.findall(r'\{(.*?)\}', inputText)
    replace_list = []
    outputText = inputText

    if len(api_list) == 0:
        return inputText # No API calls, so display the text as-is

    for item in api_list:
        vars = item.split(':')
        
        api_module = globals()[vars[0]]
        func_to_call = getattr(api_module, vars[1])
        if len(vars) > 2:
            argument = vars[2]
            replacementText = func_to_call(argument)
        else:
            replacementText = func_to_call()

        if returnText:
            outputText = outputText.replace("{" + item + "}", replacementText)

    if not returnText:
        return
    
    return outputText

def draw_colour_text(canvas, font, x, y, default_color, text):
    """
    Replacement for draw_colour_text that supports inline [fg:#RRGGBB] and [bg:#RRGGBB] tags.
    Returns the total visual width of the rendered text.
    """
    # 1. Setup Parser Logic
    pattern = r'(\[(?:fg|bg):(?:#[0-9a-fA-F]{6}|none)\])'
    parts = re.split(pattern, text)
    
    def hex_to_col(hex_str):
        if not hex_str or hex_str == "none": return default_color
        return graphics.Color(int(hex_str[1:3], 16), int(hex_str[3:5], 16), int(hex_str[5:7], 16))

    current_x = x
    curr_fg = default_color
    curr_bg = None
    total_visual_width = 0

    for part in parts:
        if not part:
            continue
            
        # Check if part is a tag
        tag_match = re.match(r'\[(fg|bg):(.*)\]', part)
        if tag_match:
            tag_type, val = tag_match.groups()
            if tag_type == "fg":
                curr_fg = hex_to_col(val)
            elif tag_type == "bg":
                curr_bg = hex_to_col(val)
            # Note: bg support depends on your specific matrix implementation 
            # standard rpi-rgb-led-matrix DrawText only supports fg color.
            continue
        
        # It's actual text
        # draw_colour_text returns the width of the text drawn

        # draw the bg colour behind the text

        if curr_bg:
            bg_width = graphics.DrawText(canvas, font, int(current_x), int(y), curr_fg, part) + 2
            bg_height = font.height + 2

            for bg_y in range(bg_height):
                graphics.DrawLine(canvas, int(current_x - 1), int(y - bg_y + 1), int(current_x + bg_width), int(y - bg_y + 1), curr_bg)

        width = graphics.DrawText(canvas, font, int(current_x), int(y), curr_fg, part)

        current_x += width
        total_visual_width += width

    return total_visual_width

# --- Drawing logic ---

async def draw_layout(matrix, canvas, objects, fonts_cache=None, scroll_state=None, debug=False, dt=0):
    global _COLOR_CACHE
    if fonts_cache is None: fonts_cache = {}
    if scroll_state is None: scroll_state = {}

    for idx, obj in enumerate(objects):
        obj_type = obj.get("type")
        if obj_type not in ("Textbox", "ScrollingTextbox", "Alert"):
            continue

        # 1. OPTIMIZED: Pre-parsed font lookup
        font_name = obj.get("font", "4x6.bdf")
        # Optimization: Use a simple key; do path logic once outside this loop
        font = fonts_cache.get(font_name) 
        if not font:
            font_path = font_name if font_name.startswith('/') else f'./fonts/{font_name}'
            f = graphics.Font()
            f.LoadFont(font_path)
            fonts_cache[font_name] = f
            font = f

        # 2. OPTIMIZED: Cached Color Parsing
        fg_hex = obj.get("fgColor", "#FFFFFF")
        if fg_hex not in _COLOR_CACHE:
            r, g, b = int(fg_hex[1:3], 16), int(fg_hex[3:5], 16), int(fg_hex[5:7], 16)
            _COLOR_CACHE[fg_hex] = graphics.Color(r, g, b)
        color = _COLOR_CACHE[fg_hex]

        # 3. CRITICAL: Throttled API Calls
        # Only call checkAPICalls if the text has placeholders like {api_val}
        # Ideally, move this out of the render loop to a background task
        raw_text = obj.get("text", "")
        text = await checkAPICalls(raw_text) if "{" in raw_text else raw_text

        # 4. Dimensions and Baseline
        x0, y0, w, h = obj["x"], obj["y"], obj["width"], obj["height"]
        # CharacterWidth is expensive; for static text, cache this in the 'obj'
        if "cached_width" not in obj or obj.get("_last_text") != text:
            obj["cached_width"] = sum(font.CharacterWidth(ord(c)) for c in text)
            obj["_last_text"] = text
        
        text_width = obj["cached_width"]
        y_baseline = y0 + ((h + font.height) // 2 - 1)

        if obj_type == "ScrollingTextbox":
            if idx not in scroll_state:
                scroll_state[idx] = w
                # Only trigger onScrollEnd once, not every frame
            
            pos_local = scroll_state[idx]
            draw_colour_text(canvas, font, int(x0 + pos_local), y_baseline, color, text)
            
            # Use dt to ensure smooth scrolling regardless of frame rate
            scroll_state[idx] -= (30 * dt)
            if (pos_local + text_width) < 0:
                scroll_state[idx] = w
                onScrollEnd = obj.get("onScrollEnd")
                if onScrollEnd: await checkAPICalls(onScrollEnd, False)

        else:
            # Static Text alignment
            align = obj.get("text_align", "left")
            x_off = 0
            if align == "center": x_off = (w - text_width) // 2
            elif align == "right": x_off = w - text_width

            draw_colour_text(canvas, font, x0 + x_off, y_baseline, color, text)

        # 5. Debug Boxes (Keep simple)
        if debug:
            draw_debug_rect(canvas, x0, y0, w, h, idx)

    return matrix.SwapOnVSync(canvas), scroll_state, fonts_cache

async def draw_sun_gradient(matrix, canvas):
    now = datetime.now()
    day_ratio = (now.hour * 3600 + now.minute * 60 + now.second) / 86400.0

    # 1. Setup Constants
    night_col = (15, 15, 60)
    day_yellow = (255, 255, 0)
    sunset_pink = (255, 20, 147)
    
    width = matrix.width
    half_width = width / 2
    glow_radius = width * 0.3
    
    # 2. Position Calculation
    start_time, end_time = 0.25, 0.875
    progress = (day_ratio - start_time) / (end_time - start_time)
    sun_x = int(width * progress)

    # 3. DRAW GRADIENT (One pass across width)
    for x in range(width):
        dx = abs(x - sun_x)
        if dx > half_width:
            dx = width - dx
            
        dist = min(1.0, dx / glow_radius)

        if dist < 0.3:
            r, g, b = day_yellow
        elif dist < 0.7:
            t = (dist - 0.3) / 0.4
            r = int(day_yellow[0] + t * (sunset_pink[0] - day_yellow[0]))
            g = int(day_yellow[1] + t * (sunset_pink[1] - day_yellow[1]))
            b = int(day_yellow[2] + t * (sunset_pink[2] - day_yellow[2]))
        else:
            t = (dist - 0.7) / 0.3
            r = int(sunset_pink[0] + t * (night_col[0] - sunset_pink[0]))
            g = int(sunset_pink[1] + t * (night_col[1] - sunset_pink[1]))
            b = int(sunset_pink[2] + t * (night_col[2] - sunset_pink[2]))
        
        # Set the vertical column (assuming height is small, otherwise loop y)
        canvas.SetPixel(x, 0, r, g, b)

    # 4. DRAW SUN (Once, on top of gradient)
    # Using a fixed coordinate mask for a radius 2 circle to avoid sqrt math
    sun_mask = [
        (0, -2), 
        (-1, -1), (0, -1), (1, -1),
        (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
        (-1, 1), (0, 1), (1, 1),
        (0, 2)
    ]
    
    for ox, oy in sun_mask:
        # modulo width handles the wrap-around for the sun body itself
        canvas.SetPixel((sun_x + ox) % width, oy, 255, 255, 0)
        
    return canvas

# Misc. Variables
TARGET_FPS = 100
TARGET_FRAME_TIME = 1.0 / (TARGET_FPS*1.1)
ACTUAL_FRAME_TIMES = deque(maxlen=10000)
ACTUAL_FPS = 0
_COLOR_CACHE = {}

async def draw():
    global ACTUAL_FRAME_TIMES, ACTUAL_FPS, _COLOR_CACHE

    # Init variables required for draw

    # --- Main setup ---
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 8
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 4

    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    layout = validateSchema.validate_layout("./layouts/1.json")
    objects = await unpack_layout(layout, panel_width=options.cols * options.chain_length,
                            panel_height=options.rows)

    fonts_cache = {}
    scroll_state = {}

    # The main draw loop

    frame_end_time = time.perf_counter()

    while True:
        frame_start_time = time.perf_counter()
        
        # 1. Precise Delta Time
        dt = frame_start_time - frame_end_time
        
        # 2. Safe Performance Metrics (Avoids StatisticsError on empty list)
        if len(ACTUAL_FRAME_TIMES) > (TARGET_FPS / 5):
            # fmean is faster than mean for floating point data
            # current_fps uses the last 10 frames for responsiveness
            current_fps = 1 / statistics.fmean(list(ACTUAL_FRAME_TIMES)[-10:])
            avg_fps = 1 / statistics.fmean(ACTUAL_FRAME_TIMES)
            print(f"Current FPS: {current_fps:3.0f} | Average FPS: {avg_fps:5.1f}", end='\r', flush=True)

        # 3. Application Logic (Preserved)

        canvas.Clear() # Clear the canvas before any of our drawing functions.

        canvas = await draw_sun_gradient(matrix, canvas)

        canvas, scroll_state, fonts_cache = await draw_layout(
            matrix, 
            canvas, 
            objects, 
            fonts_cache=fonts_cache, 
            scroll_state=scroll_state, 
            dt=TARGET_FRAME_TIME
        )

        matrix.SwapOnVSync(canvas)

        
        # 4. Frame Rate Limiting
        frame_end_time = time.perf_counter()
        render_duration = frame_end_time - frame_start_time
        sleep_time = TARGET_FRAME_TIME - render_duration
        
        if sleep_time > 0:
            # Relinquishes control to the event loop
            await asyncio.sleep(sleep_time)
        
        # 5. Record final cycle time (including sleep) for accurate FPS tracking
        ACTUAL_FRAME_TIMES.append(time.perf_counter() - frame_start_time)

async def update():

    while True:
        await NewsParser.refresh_news_feed()
        await asyncio.sleep(0.5)
    # Background updates that should be run seperately to the draw loop to not affect FPS.

async def main():

    # Runs both update & draw funcs

    await NewsParser.refresh_news_feed() # do this now so it starts with news.

    task_draw = asyncio.create_task(draw())
    task_update = asyncio.create_task(update())

        # Keep the main loop running indefinitely while the tasks execute concurrently
    try:
        # Wait for all tasks to complete (which they won't, due to while True, keeping main alive)
        await asyncio.gather(task_draw, task_update)
    except asyncio.CancelledError:
        # Handle cleanup if tasks are cancelled
        pass


# The entry point of the script
if __name__ == "__main__":
    try:
        # This starts the asyncio event loop and runs your function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Loop terminated by user (Ctrl+C).")