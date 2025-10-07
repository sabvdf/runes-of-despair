import sys
import keyboard

def clear_screen():
    print("\033[2J", end="")
def enable_cursor(enable):
    if enable:
        print("\033[?25H", end="")
    else:

        print("\033[?25l", end="")


### Clear screen, hide cursor, print welcome message
clear_screen()
enable_cursor(False)
print("*** Runes of Despair ***\n"
      "*** The Black Sigil ***\n\n"
      "Press any key to enter...")

# Wait for key press
keyboard.read_key()

### Main variables definition
player_x = 25
player_y = 7
width = 51
height = 15

### Game loop
while True:
    ### Draw the world
    # Go back to the start of the line (\r) and up {height} lines,
    # to print over the previous output
    print(f"\r\033[{height}A", end="")

    # Print one character for each x,y location in the world
    for y in range(height):
        for x in range(width):
            print("@" if x == player_x and y == player_y else ".", end="")
        print()

    ### Wait for and read a keyboard press
    while True:
        input = keyboard.read_key()
        if keyboard.is_pressed(input):
            ### Take action based on input
            match input:
                case "left":
                    if player_x > 0:
                        player_x -= 1
                case "right":
                    if player_x + 1 < width:
                        player_x += 1
                case "up":
                    if player_y > 0:
                        player_y -= 1
                case "down":
                    if player_y + 1 < height:
                        player_y += 1
                case "esc":
                    exit()
                case _:
                    continue
            break
