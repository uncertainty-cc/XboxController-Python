import sys

from dotxboxcontroller import XboxController


if __name__ == "__main__":
    numbers, sticks = XboxController.enumerateDevices()
    print("found {0} devices: {1}".format(len(numbers), numbers))
    
    if not sticks:
        sys.exit(0)

    for stick in sticks:        
        print("stick num {0}".format(stick.device_number))
        print(stick.getBatteryInformation())

