import sys
from io import TextIOWrapper
from typing import BinaryIO, Dict, Tuple

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

block_characters = "█▄▌▘▝▖▗▚"
block_coverage = [(1,1,1,1),(0,0,1,1),(1,0,1,0),(1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1),(1,0,0,1)]
block_mapping = [(list(i for i, n in enumerate(coverage) if n == 0), list(i for i, n in enumerate(coverage) if n == 1)) for coverage in block_coverage]
hi_res_characters = "▁▂▃▅▆▇▉▊▋▍▎▏◼◾━┃┏┓┗┛┣┫┳┻╋╸╹╺╻"

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
    output.write(f"\033[{y+1};{x+1}f")
def cursor_left(columns: int = 1, output: TextIOWrapper = sys.stdout):
    output.write(f"\033[{columns}D")  # Cursor left [width] and down one line
def cursor_down(rows: int = 1, output: TextIOWrapper = sys.stdout):
    output.write(f"\033[{rows}B")  # Cursor left [width] and down one line

def enable_cursor(enable, output: TextIOWrapper = sys.stdout):
    if enable:
        output.write("\033[?25h")
    else:
        output.write("\033[?25l")

def calc_distance(colours):
    distance = [[maxsize for _ in range(len(colours))] for _ in range(len(colours))]
    for a in range(len(colours)):
        for b in range(a+1, len(colours)):
            if len(colours[a]) == 3:
                distance[b][a] = distance[a][b] = CIEDE2000_rgb(colours[a], colours[b])
            else:
                distance[b][a] = distance[a][b] = abs((colours[a] / 255.0) - (colours[b] / 255.0))
    return distance

def average_colour(colours):
    if len(colours) == 0:
        return [0, 0, 0]
    return [int(sum(vals) / len(vals)) for vals in zip(*colours)]

def lists_max(lst):
    return max([i for n in lst for i in n])

def lists_average(lists):
    return [sum(lst) / len(lst) if len(lst) > 0 else 0.0 for lst in lists]

def map_block_character(colours, distance):
    if colours[0] == colours[1] == colours[2] == colours[3]:
        return block_characters[0], [colours[0], colours[0]]
    distances = [[[distance[a][b] for ia, a in enumerate(indices) for b in indices[ia+1:]] for indices in mapping] for mapping in block_mapping]
    best_match = min(enumerate(zip([lists_max(d) for d in distances], [sum(lists_average(d)) for d in distances])), key=lambda x: x[1])
    out_colours = [average_colour([colours[i] for i in indices]) for indices in block_mapping[best_match[0]]]
    return (block_characters[best_match[0]], out_colours)


class AsciiBuffer:
    def __init__(self, width: int, height: int, ansi: bool, blocks: bool, sprite_size: Tuple[int, int] = (0, 0)):
        self.width = width
        self.height = height
        self.ansi = ansi
        self.blocks = blocks
        if blocks:
            self.chars = ["�"] * (self.width * self.height // 2)
            self.charbg = bytearray(self.width * self.height * (1 if ansi else 2))
            self.charfg = bytearray(self.width * self.height * (1 if ansi else 2))
        else:
            self.pixels = bytearray(self.width * self.height * (2 if ansi else 4))
        self.sprite_size = sprite_size if sprite_size != (0, 0) else (self.width, self.height)
        self.sprite_cells = (self.width // self.sprite_size[0], self.height // self.sprite_size[1])
        self.current_fg = -1
        self.current_bg = -1


    @staticmethod
    def from_image(
        filename: str,
        width: int = 0,
        width_ratio: float = 1.0,
        grayscale: bool = False,
        ansi256: bool = False,
        blocks: bool = True,
        pre_scaled: bool = False,
        sprite_size: Tuple[int, int] = (0, 0)
    ) -> "AsciiBuffer":
        image: Image.Image = Image.open(filename)

        img_w, img_h = image.size
        orig_w, orig_h = img_w, img_h
        if width > 0 or width_ratio != 1.0:
            scalar = img_w * width_ratio / (width if width > 0 else img_w)
            img_w = int(img_w * width_ratio / scalar)
            img_h = int(img_h / scalar)
            if img_h % 2 == 1:
                img_h = img_h + 1
        if blocks and not pre_scaled:
            img_h //= 2
            if img_h % 2 == 1:
                img_h = img_h + 1
        if img_h != orig_h or img_w != orig_w:
            image = image.resize((img_w, img_h))

        if grayscale:
            image = image.convert("L")

        buffer = AsciiBuffer(img_w, img_h, ansi256, blocks, sprite_size)
        pixels = image.tobytes()
        if blocks:
            index = 0
            stride = len(pixels) // (img_w * img_h)
            previous_bg = previous_fg = -1 if ansi256 else [-1, -1, -1]
            for y in range(img_h // 2):
                for x in range(img_w // 2):
                    pixel = [[int(c) for c in p] for p in [pixels[i * stride : (i + 1) * stride] for i in [index, index + 1, index + img_w, index + img_w + 1]]]

                    distance = calc_distance(pixel)
                    block_char, colours = map_block_character(pixel, distance)

                    if ansi256:
                        ansi = [ansi_convert_color([(v / 255.0) ** 2.2 for v in colour]) for colour in colours]
                        buffer.charbg[index] = ansi[0]
                        buffer.charbg[index + 1] = 1 if previous_bg == ansi[0] else 0
                        previous_bg = ansi[0]
                        buffer.charfg[index] = ansi[1]
                        buffer.charfg[index + 1] = 1 if previous_fg == ansi[1] else 0
                        previous_fg = ansi[1]
                        buffer.chars[index // 2] = block_char
                    else:
                        buffer.charbg[index * 2 : index * 2 + 3] = colours[0][0 : 3]
                        buffer.charbg[index * 2 + 3] = 1 if previous_bg == colours[0] else 0
                        previous_bg = colours[0]
                        buffer.charfg[index * 2 : index * 2 + 3] = colours[1][0 : 3]
                        buffer.charfg[index * 2 + 3] = 1 if previous_fg == colours[1] else 0
                        previous_fg = colours[1]
                        buffer.chars[index // 2] = block_char

                    index += 2
                index += img_w
        else:
            index = 0
            stride = len(pixels) // (img_w * img_h)
            previous_color = -1 if ansi256 else [-1, -1, -1]
            for y in range(img_h):
                for x in range(img_w):
                    pixel = pixels[index * stride : (index + 1) * stride]

                    if ansi256:
                        ansi = ansi_convert_color([(v / 255.0) ** 2.2 for v in pixel])
                        buffer.pixels[index * 2] = ansi
                        buffer.pixels[index * 2 + 1] = 1 if previous_color == ansi else 0
                        previous_color = ansi
                    else:
                        buffer.pixels[index * 4 : index * 4 + 3] = pixel[0 : 3]
                        buffer.pixels[index * 4 + 3] = 1 if previous_color == pixel else 0
                        previous_color = pixel

                    index += 1

        return buffer


    def output(self, output: TextIOWrapper, left: int, top: int, source_rect = None):
        if self.blocks:
            self.output_blocks(output, left, top, source_rect)
        else:
            self.output_simple(output, left, top, source_rect)


    def output_sprite(self, output: TextIOWrapper, left: int, top: int, sprite_index: int):
        sprite_cell = (sprite_index % self.sprite_cells[0], sprite_index // self.sprite_cells[0])
        self.output(output, left, top, (sprite_cell[0] * self.sprite_size[0], sprite_cell[1] * self.sprite_size[1], self.sprite_size[0], self.sprite_size[1]))


    def output_simple(self, output: TextIOWrapper, left: int, top: int, source_rect = None):
        if left is None:
            left = 0
        if top is None:
            top = 0

        offset_x, offset_y, width, height = source_rect if source_rect is not None else (0, 0, self.width, self.height)

        index = offset_x + offset_y * self.width
        index2 = index + self.width
        for y in range(height // 2):
            cursor_xy(left, top + y, output)
            for x in range(width):
                if self.ansi:
                    if self.pixels[index * 2 + 1] == 0:
                        output.write(ansi_foreground(ansi_colours[self.pixels[index * 2]]))
                else:
                    if self.pixels[index * 4 + 3] == 0:
                        output.write(rgb_background(self.pixels[index * 4], self.pixels[index * 4 + 1], self.pixels[index * 4 + 2]))
                    if x == 0 or self.pixels[index2 * 4 + 3] == 0:
                        output.write(rgb_foreground(self.pixels[index2 * 4], self.pixels[index2 * 4 + 1], self.pixels[index2 * 4 + 2]))
                output.write("▄")

                index += 1
                index2 += 1

            index += self.width + self.width - width
            index2 = index + self.width


    def output_blocks(self, output: TextIOWrapper, left: int, top: int, source_rect = None):
        if left is None:
            left = 0
        if top is None:
            top = 0

        offset_x, offset_y, width, height = source_rect if source_rect is not None else (0, 0, self.width, self.height)

        index = offset_x // 2 + offset_y * self.width // 2
        for y in range(height // 2):
            cursor_xy(left, top + y, output)
            for x in range(width // 2):
                if self.ansi:
                    if x == 0 or self.charbg[index * 2 + 1] == 0 or self.charfg[index * 2 + 1] == 0:
                        output.write(ansi_background(ansi_colours[self.charbg[index * 2]]))
                        output.write(ansi_foreground(ansi_colours[self.charfg[index * 2]]))
                else:
                    if x == 0 or self.charbg[index * 4 + 3] == 0 or self.charfg[index * 4 + 3] == 0:
                        output.write(rgb_background(self.charbg[index * 4], self.charbg[index * 4 + 1], self.charbg[index * 4 + 2]))
                        output.write(rgb_foreground(self.charfg[index * 4], self.charfg[index * 4 + 1], self.charfg[index * 4 + 2]))
                output.write(self.chars[index])

                index += 1
            index += (self.width + self.width - width) // 2
