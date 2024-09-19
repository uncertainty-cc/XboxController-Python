# cc.XboxController

Getting input from Microsoft XBox 360 controllers via the XInput library on Windows.

## Installation

```bash
pip install cc-xboxcontroller
```

## Usage

```python
import time

from cc.xboxcontroller import XboxController, Axis

def main():
    """
    """
    stick = XboxController(0)

    while True:
        stick.update()
        stick.set_rumble(abs(stick.get_left_trigger()))
        stick.set_rumble(abs(stick.axes[Axis.RTrigger]))
        print("A Btn:", stick.get_a_button(), end="")
        print("\tD-pad:", stick.get_dpad(), end="")
        print("\tX Axis:", stick.get_left_x())
        time.sleep(.01)


if __name__ == "__main__":
    main()

```
