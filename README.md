# cc.XboxController

Getting input from Microsoft XBox 360 controllers via the XInput library on Windows.

## Installation

```bash
pip install cc-xboxcontroller
```

## Usage

```python
import time

from cc.xboxcontroller import XboxController, Hand

def main():
    """
    """
    stick = XboxController(0)

    while True:
        stick.update()
        stick.setRumble(Hand.LEFT, abs(stick.axes["LTrigger"]))
        stick.setRumble(Hand.RIGHT, abs(stick.axes["RTrigger"]))
        print("A Btn:", stick.getAButton(), end="")
        print("\tD-pad:", stick.getDPad(), end="")
        print("\tX Axis:", stick.getX(Hand.LEFT))
        time.sleep(.01)


if __name__ == "__main__":
    main()

```
