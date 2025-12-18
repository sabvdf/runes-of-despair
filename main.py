import io
import os
import termios
import time

from pynput import keyboard
from pynput.keyboard import Key

from block_ascii_art import *

old_settings = []

def on_press(key):
    keypresses.append(key)

def enable_echo(enable):
    try:
        fd = sys.stdin.fileno()
        global old_settings
        old_settings = termios.tcgetattr(fd)

        if enable:
            termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)
        else:
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
    except IOError:
        pass

def flush_stdin():
    try:
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)
    except IOError:
        pass


def render(cell):
    output = []
    (char, bg, fg) = cell
    global current_bg, current_fg
    if current_bg != bg:
        output.append(bg_colours[bg])
        current_bg = bg
    if current_fg != fg:
        output.append(fg_colours[fg])
        current_fg = fg
    output.append(char)
    return "".join(output)


### Write directly to stdout without buffering
stdout = io.TextIOWrapper(open(sys.stdout.fileno(), 'wb', 0), write_through=True)

### Main variables definition
player_x = 14
player_y = 8
width = 30
height = 18

### Create color code character sequences
fg_colours = [f"{ansi_foreground(i)}" for i in range(256)]
bg_colours = [f"{ansi_background(i)}" for i in range(256)]

empty_cell = [[("█", 0, 234),("▀", 0, 234),("▀", 0, 234),("█", 0, 234)],
              [("█", 0, 234),("▄", 0, 234),("▄", 0, 234),("█", 0, 234)]]
player_cell = [[("▄", 0, 245),("▛", 180, 160),("▜", 180, 160),("▄", 0, 245)],
               [("▗", 0, 130),("▛", 0, 32),("▜", 0, 32),("▖", 0, 130)]]

if not "--force" in sys.argv:
    stdout.write("\033[8;50;162t")
    time.sleep(0.5)

### Find the center of the screen
try:
    screen_width, screen_height = os.get_terminal_size()
except OSError:
    screen_width, screen_height = 162, 50
window_left, window_top = 37, 5

if screen_width < 162 or screen_height < 50:
    if not "--force" in sys.argv:
        print(f"Sorry, Runes of Despair's semigraphics runs only on a terminal of 162x50 characters.\nPlease scale down your terminal font so you can make it display at least 162x50 characters.\nRight now, it's {screen_width}x{screen_height}.")
        exit()

### Send keypresses to the array
keypresses = []
flush_stdin()
listener = keyboard.Listener(on_press=on_press)
listener.start()
time.sleep(0.2)

### Clear screen, hide cursor, print welcome message
clear_screen(stdout)
enable_cursor(False, stdout)
enable_echo(False)

cursor_xy(screen_width // 2 - 5, screen_height // 2, stdout)
stdout.write(f"Loading...")

sprites = AsciiBuffer.from_image("Sprites.png", pre_scaled=True, sprite_size=(8,4))
fire_index = 8
tick = 0

logo = AsciiBuffer.from_image("RoD.png", pre_scaled=True)
background = AsciiBuffer.from_image("Game.png", pre_scaled=True)

logo.output(stdout, 0, 0)

cursor_xy(68, 44, stdout)
text_colours = f"{ansi_background(0)}{ansi_foreground(15)}"
stdout.write(f"{text_colours}Press any key to enter...")

# Wait for key press
while not keypresses:
    time.sleep(0.01)

keypresses.pop(0)
clear_screen(stdout)

background.output(stdout, 0, 0)

### Game loop
while True:
    ### Draw the world

    # Print 4x2 characters for each x,y location in the world
    current_fg = -1
    current_bg = -1
    for y in range(height):
        for x in range(width):
            if x != 10 or y != 5:
                sprites.output_sprite(stdout, window_left + x * 4, window_top + y * 2, 1 if x == player_x and y == player_y else 0)

    status_line = f"{text_colours}{player_x},{player_y} - Nothing here..."
    status_line += "".join([" "] * (77 - len(status_line)))

    cursor_xy(68, 42, stdout)
    stdout.write(status_line)

    ### Wait for and read a keyboard press
    while True:
        while not keypresses:
            time.sleep(0.01)
            tick += 1
            if tick == 3:
                tick = 0
                fire_index += 1
                if fire_index > 57:
                    fire_index = 8
                sprites.output_sprite(stdout, 77, 15, fire_index)

        input_key = keypresses.pop(0)
        ### Take action based on input
        if hasattr(input_key, "char"):
            input_key = input_key.char
        match input_key:
            case Key.left:
                if player_x > 0:
                    player_x -= 1
            case Key.right:
                if player_x + 1 < width:
                    player_x += 1
            case Key.up:
                if player_y > 0:
                    player_y -= 1
            case Key.down:
                if player_y + 1 < height:
                    player_y += 1
            case Key.esc | "q":
                enable_echo(True)
                enable_cursor(True)
                termios.tcflush(sys.stdin, termios.TCIOFLUSH)
                time.sleep(0.2)
                clear_screen(stdout)
                cursor_home(stdout)
                exit()
            case _:
                continue
        break
