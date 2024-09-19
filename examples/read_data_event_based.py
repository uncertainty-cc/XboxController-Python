import time
import sys

from cc.xboxcontroller import XboxController

def main():
    """
    """
    stick = XboxController(0)

    @stick.event
    def on_button(button, state):
        print("button", button, state)
        pass
    
    @stick.event
    def on_axis(axis, value):
        print("axis", axis, value)
        if axis == "LTrigger":
            stick.set_left_rumble(value)
        if axis == "RTrigger":
            stick.set_right_rumble(value)

    while True:
        stick.update()
        time.sleep(.01)


if __name__ == "__main__":
    main()

