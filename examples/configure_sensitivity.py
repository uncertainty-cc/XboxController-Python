import time
import sys

from cc.xboxcontroller import XboxController, Hand

def main():
    """
    """
    stick = XboxController(0, deadzone=0.0, dampen=0.0)

    while True:
        stick.update()
        print("X:", stick.getX(Hand.LEFT), end="")
        print("\tY:", stick.getY(Hand.LEFT))
        time.sleep(.01)

if __name__ == "__main__":
    main()
