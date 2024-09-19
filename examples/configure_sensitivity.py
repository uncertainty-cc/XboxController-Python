import time

from cc.xboxcontroller import XboxController

def main():
    """
    """
    stick = XboxController(0, deadzone=0.0, dampen=0.0)

    while True:
        stick.update()
        print("X:", stick.get_left_x(), end="")
        print("\tY:", stick.get_left_y())
        time.sleep(.01)

if __name__ == "__main__":
    main()
