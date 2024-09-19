import time

from cc.xboxcontroller import XboxController

def main():
    """
    """
    stick = XboxController(0)

    while True:
        stick.update()
        stick.set_left_rumble(abs(stick.get_left_trigger()))
        stick.set_right_rumble(abs(stick.get_right_trigger()))
        print("A Btn:", stick.get_a_button(), end="")
        print("\tD-pad:", stick.get_dpad(), end="")
        print("\tX Axis:", stick.get_left_x())
        time.sleep(.01)


if __name__ == "__main__":
    main()

