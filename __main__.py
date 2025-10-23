from scripts import getTime # Import all custom scripts
import time

import os

def is_raspberry_pi():
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
        return "Raspberry Pi" in cpuinfo or "BCM" in cpuinfo
    except FileNotFoundError:
        return False
    
if is_raspberry_pi():
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    print("Running on Raspberry Pi: using real RGBMatrix library.")
else:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
    print("Running on non-Pi system: using RGBMatrixEmulator.")

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

while True:
    canvas.Clear()
    # y=20 fits well within 32px height for 7x13 font
    len_msg = graphics.DrawText(canvas, font, pos, 20, textColor, f"{message} | {getTime.get_24hr_time('America/New_York')}")
    pos -= 1
    if pos + len_msg < 0:
        pos = canvas.width
    time.sleep(0.03)

    canvas = matrix.SwapOnVSync(canvas)