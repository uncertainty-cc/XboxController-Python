# dotXboxController

Getting input from Microsoft XBox 360 controllers via the XInput library on Windows.

## Installation

```bash
pip install dotxboxcontroller
```

## Usage

```python
import time
import sys

from dotxboxcontroller import XboxController, Hand

def main():
    """
    """
    stick = XboxController(0)

    while True:
        stick.update()
        stick.setRumble(Hand.LEFT, abs(stick.axes["LTrigger"]))
        stick.setRumble(Hand.RIGHT, abs(stick.axes["RTrigger"]))
        print("A Btn:", stick.getAButton(), end="")
        print("\tPOV:", stick.getPOV(), end="")
        print("\tX Axis:", stick.getX(Hand.LEFT))
        time.sleep(.01)


if __name__ == "__main__":
    main()

```
