import sys
from io import TextIOWrapper
from typing import BinaryIO

from PIL import Image

from ciede2000 import CIEDE2000_rgb
from sys import maxsize

ansi_colours = [(0,0,0),
                (128,0,0),
                (0,128,0),
                (128,128,0),
                (0,0,128),
                (128,0,128),
                (0,128,128),
                (192,192,192),
                (128,128,128),
                (255,0,0),
                (0,255,0),
                (255,255,0),
                (0,0,255),
                (255,0,255),
                (0,255,255),
                (255,255,255)]

for col in range(16, 232):
    index_R = ((col - 16) // 36)
    red = 55 + index_R * 40 if index_R > 0 else 0
    index_G = (((col - 16) % 36) // 6)
    green = 55 + index_G * 40 if index_G > 0 else 0
    index_B = ((col - 16) % 6)
    blue = 55 + index_B * 40 if index_B > 0 else 0
    ansi_colours.append((red, green, blue))

for col in range(232, 256):
    gray = (col - 232) * 10 + 8
    ansi_colours.append((gray, gray, gray))

def rgb_foreground(r, g, b):
    return f"\033[38;2;{int(r / 1.1)};{int(g / 1.1)};{int(b / 1.1)}m"
def rgb_background(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"
def ansi_foreground(col):
    return f"\033[38;5;{col}m"
def ansi_background(col):
    return f"\033[48;5;{col}m"

def ansi_convert_color(rgb: list) -> int:
    min_distance = maxsize
    index = 0

    for i in range(len(ansi_colours)):
        distance = CIEDE2000_rgb(ansi_colours[i], rgb)

        if distance < min_distance:
            index = i
            min_distance = distance

    return index

def clear_screen(output: TextIOWrapper = sys.stdout):
    output.write("\033[2J")
def cursor_home(output: TextIOWrapper = sys.stdout):
    output.write(f"\033[H")
def cursor_xy(x: int, y: int, output: TextIOWrapper = sys.stdout):
    output.write(f"\033[{y};{x}f")
def cursor_left(columns: int = 1, output: TextIOWrapper = sys.stdout):
    output.write(f"\033[{columns}D")  # Cursor left [width] and down one line
def cursor_down(rows: int = 1, output: TextIOWrapper = sys.stdout):
    output.write(f"\033[{rows}B")  # Cursor left [width] and down one line


def enable_cursor(enable, output: TextIOWrapper = sys.stdout):
    if enable:
        output.write("\033[?25h")
    else:
        output.write("\033[?25l")


class AsciiBuffer:
    def __init__(self, width: int, height: int, ansi: bool):
        self.width = width
        self.height = height
        self.ansi = ansi
        self.buffer = bytearray(self.width * self.height * (2 if ansi else 4))
        self.current_fg = -1
        self.current_bg = -1

    @staticmethod
    def from_image(
        filename: str,
        width: int = 0,
        width_ratio: float = 1.0,
        grayscale: bool = False,
        ansi256: bool = False,
    ) -> "AsciiBuffer":
        image: Image.Image = Image.open(filename)

        img_w, img_h = image.size
        scalar = img_w * width_ratio / (width if width > 0 else img_w)
        img_w = int(img_w * width_ratio / scalar)
        img_h = int(img_h / scalar)
        if img_h % 2 == 1:
            img_h = img_h + 1
        image = image.resize((img_w, img_h))

        if grayscale:
            image = image.convert("L")

        buffer = AsciiBuffer(img_w, img_h, ansi256)
        pixels = image.tobytes()
        index = 0
        stride = len(pixels) // (img_w * img_h)
        previousColor = -1 if ansi256 else [-1, -1, -1]
        for y in range(img_h):
            for x in range(img_w):
                pixel = pixels[index * stride : (index + 1) * stride]

                if ansi256:
                    ansi = ansi_convert_color([(v / 255.0) ** 2.2 for v in pixel])
                    buffer.buffer[index * 2] = ansi
                    buffer.buffer[index * 2 + 1] = 1 if previousColor == ansi else 0
                    previousColor = ansi
                else:
                    buffer.buffer[index * 4 : index * 4 + 3] = pixel[0 : 3]
                    buffer.buffer[index * 4 + 3] = 1 if previousColor[0] == pixel[0] and previousColor[1] == pixel[1] and previousColor[2] == pixel[2] else 0
                    previousColor = pixel

                index += 1

        return buffer

    def output(self, output: TextIOWrapper, left, top):
        if left is not None and top is not None:
            cursor_xy(left, top, output)

        index = 0
        index2 = self.width
        for y in range(self.height // 2):
            for x in range(self.width):
                if self.ansi:
                    if self.buffer[index * 2 + 1] == 0:
                        output.write(ansi_foreground(ansi_colours[self.buffer[index * 2]]))
                else:
                    if self.buffer[index * 4 + 3] == 0:
                        output.write(rgb_background(self.buffer[index * 4], self.buffer[index * 4 + 1], self.buffer[index * 4 + 2]))
                    if x == 0 or self.buffer[index2 * 4 + 3] == 0:
                        output.write(rgb_foreground(self.buffer[index2 * 4], self.buffer[index2 * 4 + 1], self.buffer[index2 * 4 + 2]))
                output.write("▄")

                index += 1
                index2 += 1

            cursor_left(self.width, output)
            cursor_down(1, output)

            index += self.width
            index2 += self.width

    #  ▁	LOWER ONE EIGHTH BLOCK
    #  ▂	LOWER ONE QUARTER BLOCK
    #  ▃	LOWER THREE EIGHTHS BLOCK
    #  ▄	LOWER HALF BLOCK
    #  ▅ 	LOWER FIVE EIGHTHS BLOCK
    #  ▆ 	LOWER THREE QUARTERS BLOCK
    #  ▇	LOWER SEVEN EIGHTHS BLOCK
    #  █	FULL BLOCK
    #  ▉	LEFT SEVEN EIGHTHS BLOCK
    #  ▊	LEFT THREE QUARTERS BLOCK
    #  ▋	LEFT FIVE EIGHTHS BLOCK
    #  ▌	LEFT HALF BLOCK
    #  ▍	LEFT THREE EIGHTHS BLOCK
    #  ▎	LEFT ONE QUARTER BLOCK
    #  ▏	LEFT ONE EIGHTH BLOCK
    #  ▖	QUADRANT LOWER LEFT
    #  ▗	QUADRANT LOWER RIGHT
    #  ▘	QUADRANT UPPER LEFT
    #  ▙	QUADRANT UPPER LEFT AND LOWER LEFT AND LOWER RIGHT
    #  ▚	QUADRANT UPPER LEFT AND LOWER RIGHT
    #  ▛	QUADRANT UPPER LEFT AND UPPER RIGHT AND LOWER LEFT
    #  ▜	QUADRANT UPPER LEFT AND UPPER RIGHT AND LOWER RIGHT
    #  ▝	QUADRANT UPPER RIGHT
    #  ▞	QUADRANT UPPER RIGHT AND LOWER LEFT
    #  ▟	QUADRANT UPPER RIGHT AND LOWER LEFT AND LOWER RIGHT
    #  ◼	BLACK MEDIUM SQUARE
    #  ◾	BLACK MEDIUM SMALL SQUARE
