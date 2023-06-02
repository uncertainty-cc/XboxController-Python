""" xboxcontroller.py
Getting input from Microsoft XBox 360 controllers via the XInput library on Windows.

Adapted from Jason R. Coombs' code:
http://pydoc.net/Python/jaraco.input/1.0.1/jaraco.input.win32.xinput
under MIT licence
"""

import ctypes
from operator import itemgetter, attrgetter
from itertools import count, starmap

from pyglet import event

# structs according to
# http://msdn.microsoft.com/en-gb/library/windows/desktop/ee417001%28v=vs.85%29.aspx


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("buttons", ctypes.c_ushort),       # wButtons
        ("LTrigger", ctypes.c_ubyte),   # bLeftTrigger
        ("RTrigger", ctypes.c_ubyte),  # bLeftTrigger
        ("LX", ctypes.c_short),      # sThumbLX
        ("LY", ctypes.c_short),      # sThumbLY
        ("RX", ctypes.c_short),      # sThumbRx
        ("RY", ctypes.c_short),      # sThumbRy
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("packet_number", ctypes.c_ulong),  # dwPacketNumber
        ("gamepad", XINPUT_GAMEPAD),        # Gamepad
    ]


class XINPUT_VIBRATION(ctypes.Structure):
    _fields_ = [("wLeftMotorSpeed", ctypes.c_ushort),
                ("wRightMotorSpeed", ctypes.c_ushort)]


class XINPUT_BATTERY_INFORMATION(ctypes.Structure):
    _fields_ = [("BatteryType", ctypes.c_ubyte),
                ("BatteryLevel", ctypes.c_ubyte)]


class ERRORCODE:
    DEVICE_NOT_CONNECTED = 1167
    SUCCESS = 0


# See here for various xinput versions https://docs.microsoft.com/en-us/windows/win32/xinput/xinput-versions
xinput = ctypes.windll.xinput1_4

"""
take a ctypes.Structure and return its field/value pairs
as a dict.

>>> 'buttons' in structDict(XINPUT_GAMEPAD)
True
>>> structDict(XINPUT_GAMEPAD)['buttons'].__class__.__name__
'CField'
"""
def structDict(struct):
    def get_pair(field, ftype): return (
        field, getattr(struct, field))
    return dict(list(map(get_pair, struct._fields_)))


"""
Get bit values as a list for a given number

>>> getBitValues(1) == [0]*31 + [1]
True

>>> getBitValues(0xDEADBEEF)
[1L, 1L, 0L, 1L, 1L, 1L, 1L, 0L, 1L, 0L, 1L, 0L, 1L, 1L, 0L, 1L, 1L, 0L, 1L, 1L, 1L, 1L, 1L, 0L, 1L, 1L, 1L, 0L, 1L, 1L, 1L, 1L]

You may override the default word size of 32-bits to match your actual
application.
>>> getBitValues(0x3, 2)
[1L, 1L]

>>> getBitValues(0x3, 4)
[0L, 0L, 1L, 1L]
"""
def getBitValues(number, size=32):
    res = list(genBitValues(number))
    res.reverse()
    # 0-pad the most significant bit
    res = [0] * (size - len(res)) + res
    return res


"""
Return a zero or one for each bit of a numeric value up to the most
significant 1 bit, beginning with the least significant bit.
"""
def genBitValues(number):
    number = int(number)
    while number:
        yield number & 0x1
        number >>= 1


class Hand:
    LEFT = 0
    RIGHT = 1


class Button:
    Y = 1
    X = 2
    B = 3
    A = 4
    L = 5
    BUMPER_R = 7
    BUMPER_L = 8
    STICK_R = 9
    STICK_L = 10
    BACK = 11
    START = 12
    DPAD_R = 13
    DPAD_L = 14
    DPAD_D = 15
    DPAD_U = 16


# add deadzones and dampen noise
# try appropriate values or simply follow 
# http://msdn.microsoft.com/en-gb/library/windows/desktop/ee417001%28v=vs.85%29.aspx#dead_zone

DEADZONE = 0.08000000000000000
DAMPEN = 0.00000000500000000
    
"""
A stateful wrapper to the XboxController, using pyglet event 
model, that binds to one XInput device and dispatches events 
when states change.

Example:
stick = XboxController(0)
"""
class XboxController(event.EventDispatcher):
    max_devices = 4

    """
    Returns a list of connected devices.
    """
    @staticmethod
    def enumerateDevices():
        devices = list(map(XboxController, list(
            range(XboxController.max_devices))))
        sticks = [d for d in devices if d.isConnected()]
        return list(map(attrgetter("device_number"), sticks)), sticks

    def __init__(self, device_number=0, deadzone=DEADZONE, dampen=DAMPEN, normalize_axes=1):
        values = vars()
        del values["self"]
        self.__dict__.update(values)

        super(XboxController, self).__init__()

        self._last_state = self.getState()
        self.received_packets = 0
        self.missed_packets = 0

        self.deadzone = deadzone
        self.dampen = dampen

        self.axes = {"LTrigger": 0, "RTrigger": 0,
                     "LX": 0, "LY": 0, "RX": 0, "RY": 0, }
        self.buttons = [0] * 17
        self.rumble = [0] * 2

        # Set the method that will be called to normalize
        # the values for analog axis.
        choices = [self.translateIdentity, self.translateUsingDataSize]
        self.translate = choices[normalize_axes]

    def translateUsingDataSize(self, value, data_size):
        # normalizes analog data to [0, 1] for unsigned data
        # and [-0.5, 0.5] for signed data
        data_bits = 8 * data_size
        return float(value) / (2**data_bits - 1)

    def translateIdentity(self, value, data_size=None):
        return value

    """
    Get the state of the controller represented by this object.
    """
    def getState(self):
        state = XINPUT_STATE()
        res = xinput.XInputGetState(self.device_number, ctypes.byref(state))
        if res == ERRORCODE.SUCCESS:
            return state
        if res != ERRORCODE.DEVICE_NOT_CONNECTED:
            raise RuntimeError(
                "Unknown error %d attempting to get state of device %d" % (res, self.device_number))
        else:
            # device is not connected
            return None

    def isConnected(self):
        return self._last_state is not None

    """
    Get battery type & charge level.
    """
    def getBatteryInformation(self):
        BATTERY_DEVTYPE_GAMEPAD = 0x00
        BATTERY_DEVTYPE_HEADSET = 0x01
        # Set up function argument types and return type
        XInputGetBatteryInformation = xinput.XInputGetBatteryInformation
        XInputGetBatteryInformation.argtypes = [
            ctypes.c_uint, ctypes.c_ubyte, ctypes.POINTER(XINPUT_BATTERY_INFORMATION)]
        XInputGetBatteryInformation.restype = ctypes.c_uint
        battery = XINPUT_BATTERY_INFORMATION(0, 0)
        XInputGetBatteryInformation(
            self.device_number, BATTERY_DEVTYPE_GAMEPAD, ctypes.byref(battery))
        battery_type = "Unknown" if battery.BatteryType == 0xFF else [
            "Disconnected", "Wired", "Alkaline", "Nimh"][battery.BatteryType]
        level = ["Empty", "Low", "Medium", "Full"][battery.BatteryLevel]
        return battery_type, level

    """
    Update the status of the joystick. Required before reading status data.
    """
    def update(self):
        state = self.getState()
        if not state:
            raise RuntimeError("Joystick %d is not connected" %
                               self.device_number)
        if state.packet_number != self._last_state.packet_number:
            # state has changed, handle the change
            self.updatePacketCount(state)
            self.handleChangedState(state)
        self._last_state = state

    """
    Keep track of received and missed packets for performance tuning.
    """
    def updatePacketCount(self, state):
        self.received_packets += 1
        missed_packets = state.packet_number - self._last_state.packet_number - 1
        if missed_packets:
            self.dispatch_event("onMissedPacket", missed_packets)
        self.missed_packets += missed_packets

    """
    Dispatch various events as a result of the state changing.
    """
    def handleChangedState(self, state):
        self.dispatch_event("onStateChanged", state)
        self.dispatchAxisEvents(state)
        self.dispatchButtonEvents(state)

    def dispatchAxisEvents(self, state):
        axis_fields = dict(XINPUT_GAMEPAD._fields_)
        axis_fields.pop("buttons")
        for axis, data_type in list(axis_fields.items()):
            last_val = getattr(self._last_state.gamepad, axis)
            val = getattr(state.gamepad, axis)
            data_size = ctypes.sizeof(data_type)
            last_val = self.translate(last_val, data_size)
            val = self.translate(val, data_size)
            if abs(last_val - val) > self.dampen:
                if abs(last_val) < self.deadzone:
                    last_val = 0
                if abs(val) < self.deadzone:
                    val = 0
                if last_val != val:
                    if axis not in ["LTrigger", "RTrigger"]:
                        val *= 2
                    val = max(-1.0, min(val, 1))
                    self.axes[axis] = val
                    self.dispatch_event("onAxis", axis, val)

    def dispatchButtonEvents(self, state):
        changed = state.gamepad.buttons ^ self._last_state.gamepad.buttons
        changed = getBitValues(changed, 16)
        buttons_state = getBitValues(state.gamepad.buttons, 16)
        button_numbers = count(1)
        changed_buttons = list(filter(itemgetter(0), list(
            zip(changed, button_numbers, buttons_state))))
        tuple(starmap(self.dispatchButtonEvent, changed_buttons))

    def dispatchButtonEvent(self, changed, number, pressed):
        self.buttons[number] = pressed
        self.dispatch_event("onButton", number, pressed)

    """
    Set the rumble output for the HID. Currently supports 2 rumble values, left rumble and
    right rumble.

    @type hand: Hand
    @param hand: which side to set
    @type value: float
    @param value: The normalized value in range [0.0, 1.0] to set the rumble to
    """
    def setRumble(self, hand, value):
        # Set up function argument types and return type
        if hand == Hand.LEFT:
            self.rumble[0] = max(0.0, min(1.0, value))
        elif hand == Hand.RIGHT:
            self.rumble[1] = max(0.0, min(1.0, value))
        XInputSetState = xinput.XInputSetState
        XInputSetState.argtypes = [ctypes.c_uint,
                                   ctypes.POINTER(XINPUT_VIBRATION)]
        XInputSetState.restype = ctypes.c_uint
        vibration = XINPUT_VIBRATION(
            int(self.rumble[0] * 65535), int(self.rumble[1] * 65535))
        XInputSetState(self.device_number, ctypes.byref(vibration))

    """
    Get the X position of the HID.

    @type hand: Hand
    @param hand: which hand, left or right
    @return: the X position in range [-1.0, 1.0]
    """
    def getX(self, hand):
        if hand == Hand.LEFT:
            return self.axes["LX"]
        if hand == Hand.RIGHT:
            return self.axes["RX"]

    """
    Get the Y position of the HID.

    @type hand: Hand
    @param hand: which hand, left or right
    @return: the Y position in range [-1.0, 1.0]
    """
    def getY(self, hand):
        if hand == Hand.LEFT:
            return self.axes["LY"]
        if hand == Hand.RIGHT:
            return self.axes["RY"]

    """
    Get the trigger axis value of the controller.

    @type hand: Hand
    @param hand: which hand, left or right
    @return: the trigger axis value in range [0.0, 1.0]
    """
    def getTrigger(self, hand):
        if hand == Hand.LEFT:
            return self.axes["LTrigger"]
        if hand == Hand.RIGHT:
            return self.axes["RTrigger"]

    def getYButton(self):
        return self.buttons[Button.Y]

    def getXButton(self):
        return self.buttons[Button.X]

    def getBButton(self):
        return self.buttons[Button.B]

    def getAButton(self):
        return self.buttons[Button.A]

    def getBumper(self, hand):
        if hand == Hand.LEFT:
            return self.buttons[Button.BUMPER_L]
        if hand == Hand.RIGHT:
            return self.buttons[Button.BUMPER_R]

    def getStartButton(self):
        return self.buttons[Button.START]
        
    def getBackButton(self):
        return self.buttons[Button.BACK]

    def getDPad(self):
        if not self.buttons[Button.DPAD_L] and not self.buttons[Button.DPAD_R] and self.buttons[Button.DPAD_U] and not self.buttons[Button.DPAD_D]:
            return 0
        elif not self.buttons[Button.DPAD_L] and self.buttons[Button.DPAD_R] and self.buttons[Button.DPAD_U] and not self.buttons[Button.DPAD_D]:
            return 45
        elif not self.buttons[Button.DPAD_L] and self.buttons[Button.DPAD_R] and not self.buttons[Button.DPAD_U] and not self.buttons[Button.DPAD_D]:
            return 90
        elif not self.buttons[Button.DPAD_L] and self.buttons[Button.DPAD_R] and not self.buttons[Button.DPAD_U] and self.buttons[Button.DPAD_D]:
            return 135
        elif not self.buttons[Button.DPAD_L] and not self.buttons[Button.DPAD_R] and not self.buttons[Button.DPAD_U] and self.buttons[Button.DPAD_D]:
            return 180
        elif self.buttons[Button.DPAD_L] and not self.buttons[Button.DPAD_R] and not self.buttons[Button.DPAD_U] and self.buttons[Button.DPAD_D]:
            return 225
        elif self.buttons[Button.DPAD_L] and not self.buttons[Button.DPAD_R] and not self.buttons[Button.DPAD_U] and not self.buttons[Button.DPAD_D]:
            return 270
        elif self.buttons[Button.DPAD_L] and not self.buttons[Button.DPAD_R] and self.buttons[Button.DPAD_U] and not self.buttons[Button.DPAD_D]:
            return 315
        return -1

    def onStateChanged(self, state):
        pass

    def onAxis(self, axis, value):
        pass

    def onButton(self, button, state):
        pass

    def onMissedPacket(self, number):
        pass


XboxController.register_event_type("onStateChanged")
XboxController.register_event_type("onAxis")
XboxController.register_event_type("onButton")
XboxController.register_event_type("onMissedPacket")
