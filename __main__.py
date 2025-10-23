from scripts import getTime # Import all custom scripts
import time

import platform

try:
    # Check if running on Raspberry Pi
    if platform.system() == "Linux" and "arm" in platform.machine():
        from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
        print("Running on Raspberry Pi: using real RGBMatrix library.")
    else:
        raise ImportError("Not on Pi")
except ImportError:
    # Fallback to emulator
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
    print("Running on non-Pi system: using RGBMatrixEmulator.")

# Configuration for 8x1 panels of 64x32 each
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 2
options.parallel = 1
options.hardware_mapping = 'regular'  # Use 'regular' for emulator

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# Load font
font = graphics.Font()
font.LoadFont("./fonts/7x13.bdf")  # Ensure this path is correct

# Set text color
textColor = graphics.Color(255, 0, 0)  # Red

# Text to scroll
message = "Current time in Portland, USA!"
pos = canvas.width

while True:
    canvas.Clear()
    # y=20 fits well within 32px height for 7x13 font
    len_msg = graphics.DrawText(canvas, font, pos, 20, textColor, f"{message} | {getTime.get_24hr_time('America/Los_Angeles')}")
    pos -= 1
    if pos + len_msg < 0:
        pos = canvas.width
    time.sleep(0.03)

    canvas = matrix.SwapOnVSync(canvas)