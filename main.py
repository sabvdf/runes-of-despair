import io
import os
import termios
import time

from pynput import keyboard
from pynput.keyboard import Key

from block_ascii_art import *


def on_press(key):
    keypresses.append(key)

def enable_echo(enable):
    fd = sys.stdin.fileno()
    global old_settings
    old_settings = termios.tcgetattr(fd)

    if enable:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)
    else:
        new_settings = termios.tcgetattr(fd)
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)

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

stdout.write("\033[8;50;162t")
time.sleep(0.5)

### Find the center of the screen
(screen_width, screen_height) = os.get_terminal_size()
window_left, window_top = 38, 6

if screen_width < 162 or screen_height < 50:
    print(f"Please scale down your terminal so you can make it 162x50 characters.\nRight now, it's {screen_width}x{screen_height}.")
    exit()

### Send keypresses to the array
keypresses = []
termios.tcflush(sys.stdin, termios.TCIOFLUSH)
listener = keyboard.Listener(on_press=on_press)
listener.start()
time.sleep(0.2)

### Clear screen, hide cursor, print welcome message
clear_screen(stdout)
enable_cursor(False, stdout)
enable_echo(False)

AsciiBuffer.from_image("RoD.png").output(stdout, 0, 0)

cursor_xy(69, 45, stdout)
text_colours = f"{ansi_background(0)}{ansi_foreground(15)}"
stdout.write(f"{text_colours}Press any key to enter...")

# Wait for key press
while keypresses == []:
    time.sleep(0.01)

keypresses.pop(0)
clear_screen(stdout)

background = AsciiBuffer.from_image("Game.png")
background.output(stdout, 0, 0)

### Game loop
while True:
    ### Draw the world
    # Go back to the top left of the screen, to print over the previous output
    cursor_xy(window_left, window_top, stdout)

    # Print 4x2 characters for each x,y location in the world
    current_fg = -1
    current_bg = -1
    for y in range(height * 2):
        iy = y % 2
        for x in range(width * 4):
            ix = x % 4
            stdout.write(render(player_cell[iy][ix] if x // 4 == player_x and y // 2 == player_y else empty_cell[iy][ix]))
        cursor_left(width * 4, stdout)
        cursor_down(1, stdout)

    status_line = f"{text_colours}{player_x},{player_y} - Nothing here..."
    status_line += "".join([" "] * (77 - len(status_line)))

    cursor_xy(70, 43, stdout)
    stdout.write(status_line)

    ### Wait for and read a keyboard press
    while True:
        while keypresses == []:
            time.sleep(0.01)

        input = keypresses.pop(0)
        ### Take action based on input
        if hasattr(input, "char"):
            input = input.char
        match input:
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
