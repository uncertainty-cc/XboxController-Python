import time
import sys

from cc.xboxcontroller import XboxController, Hand

def main():
    """
    """
    stick = XboxController(0)

    @stick.event
    def onButton(button, state):
        print("button", button, state)
        pass
    
    @stick.event
    def onAxis(axis, value):
        print("axis", axis, value)
        if axis == "LTrigger":
            stick.setRumble(Hand.LEFT, value)
        if axis == "RTrigger":
            stick.setRumble(Hand.RIGHT, value)

    while True:
        stick.update()
        time.sleep(.01)


if __name__ == "__main__":
    main()

