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

>>> 'buttons' in struct_dict(XINPUT_GAMEPAD)
True
>>> struct_dict(XINPUT_GAMEPAD)['buttons'].__class__.__name__
'CField'
"""
def struct_dict(struct):
    def get_pair(field, ftype): return (
        field, getattr(struct, field))
    return dict(list(map(get_pair, struct._fields_)))


"""
Get bit values as a list for a given number

>>> get_bit_values(1) == [0]*31 + [1]
True

>>> get_bit_values(0xDEADBEEF)
[1L, 1L, 0L, 1L, 1L, 1L, 1L, 0L, 1L, 0L, 1L, 0L, 1L, 1L, 0L, 1L, 1L, 0L, 1L, 1L, 1L, 1L, 1L, 0L, 1L, 1L, 1L, 0L, 1L, 1L, 1L, 1L]

You may override the default word size of 32-bits to match your actual
application.
>>> get_bit_values(0x3, 2)
[1L, 1L]

>>> get_bit_values(0x3, 4)
[0L, 0L, 1L, 1L]
"""
def get_bit_values(number, size=32):
    res = list(gen_bit_values(number))
    res.reverse()
    # 0-pad the most significant bit
    res = [0] * (size - len(res)) + res
    return res


"""
Return a zero or one for each bit of a numeric value up to the most
significant 1 bit, beginning with the least significant bit.
"""
def gen_bit_values(number):
    number = int(number)
    while number:
        yield number & 0x1
        number >>= 1


class Axis:
    LX = "LX"
    LY = "LY"
    RX = "RX"
    RY = "RY"
    LTrigger = "LTrigger"
    RTrigger = "RTrigger"

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

class Hand:
    LEFT = "LEFT"
    RIGHT = "RIGHT"


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
    def enumerate_devices() -> tuple[list[int], list["XboxController"]]:
        devices = list(map(XboxController, list(
            range(XboxController.max_devices))))
        sticks = [d for d in devices if d.is_connected()]
        return list(map(attrgetter("device_number"), sticks)), sticks

    def __init__(self, 
        device_number: int = 0, 
        deadzone: float = DEADZONE, 
        dampen: float = DAMPEN, 
        normalize_axes: int = 1
    ):
        values = vars()
        del values["self"]
        self.__dict__.update(values)

        super().__init__()

        self.device_number = device_number
        self._last_state = self.get_state()
        self.received_packets = 0
        self.missed_packets = 0

        self.deadzone = deadzone
        self.dampen = dampen

        self.axes = {
            Axis.LX: 0,
            Axis.LY: 0,
            Axis.RX: 0,
            Axis.RY: 0,
            Axis.LTrigger: 0,
            Axis.RTrigger: 0,
        }
        self.buttons = [0] * 17
        self.rumble = [0] * 2

        # Set the method that will be called to normalize
        # the values for analog axis.
        choices = [self.translate_identity, self.translate_using_data_size]
        self.translate = choices[normalize_axes]

    def translate_using_data_size(self, value: int, data_size: int) -> float:

        # normalizes analog data to [0, 1] for unsigned data
        # and [-0.5, 0.5] for signed data
        data_bits = 8 * data_size
        return float(value) / (2**data_bits - 1)

    def translate_identity(self, value: int, data_size: int = None) -> float:

        return value

    """
    Get the state of the controller represented by this object.

    Returns:
        XINPUT_STATE | None: The state of the controller, or None if the controller is not connected.
    """
    def get_state(self) -> XINPUT_STATE | None:
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

    def is_connected(self) -> bool:
        return self._last_state is not None

    """
    Get battery type & charge level.

    Returns:
        tuple[str, str]: The battery type and charge level.
    """
    def get_battery_information(self) -> tuple[str, str]:
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
    def update(self) -> None:
        state = self.get_state()
        if not state:
            raise RuntimeError("Joystick %d is not connected" %
                               self.device_number)
        if state.packet_number != self._last_state.packet_number:
            # state has changed, handle the change
            self.update_packet_count(state)
            self.handle_changed_state(state)
        self._last_state = state

    """
    Keep track of received and missed packets for performance tuning.

    Args:
        state (XINPUT_STATE): The state of the controller.
    """
    def update_packet_count(self, state: XINPUT_STATE) -> None:
        self.received_packets += 1
        missed_packets = state.packet_number - self._last_state.packet_number - 1
        if missed_packets:
            self.dispatch_event("on_missed_packet", missed_packets)
        self.missed_packets += missed_packets

    """
    Dispatch various events as a result of the state changing.

    Args:
        state (XINPUT_STATE): The state of the controller.
    """
    def handle_changed_state(self, state: XINPUT_STATE) -> None:
        self.dispatch_event("on_state_changed", state)
        self.dispatch_axis_events(state)
        self.dispatch_button_events(state)

    """
    Dispatch axis events as a result of the state changing.

    Args:
        state (XINPUT_STATE): The state of the controller.
    """
    def dispatch_axis_events(self, state: XINPUT_STATE) -> None:
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
                    if axis not in [Axis.LTrigger, Axis.RTrigger]:
                        val *= 2
                    val = max(-1.0, min(val, 1))
                    self.axes[axis] = val
                    self.dispatch_event("on_axis", axis, val)

    """
    Dispatch button events as a result of the state changing.

    Args:
        state (XINPUT_STATE): The state of the controller.
    """
    def dispatch_button_events(self, state: XINPUT_STATE) -> None:
        changed = state.gamepad.buttons ^ self._last_state.gamepad.buttons
        changed = get_bit_values(changed, 16)
        buttons_state = get_bit_values(state.gamepad.buttons, 16)
        button_numbers = count(1)
        changed_buttons = list(filter(itemgetter(0), list(
            zip(changed, button_numbers, buttons_state))))
        tuple(starmap(self.dispatch_button_event, changed_buttons))

    """
    Dispatch a button event.

    Args:
        changed (bool): Whether the button state has changed.
        number (int): The button number.
        pressed (bool): Whether the button is pressed.
    """
    def dispatch_button_event(self, changed, number, pressed) -> None:
        self.buttons[number] = pressed
        self.dispatch_event("on_button", number, pressed)

    """
    Get the state of a button.

    Args:
        button (int): The button to get the state of.

    Returns:
        bool: The state of the button.
    """
    def get_button(self, button: int) -> bool:
        return self.buttons[button]

    """
    Get the value of an axis.

    Args:
        axis (str): The axis to get the value of.

    Returns:
        float: The value of the axis in range [-1.0, 1.0].
    """
    def get_axis(self, axis: str) -> float:
        return self.axes[axis]

    """
    Set the rumble output for the HID. Currently supports 2 rumble values, left rumble and
    right rumble.

    Args:
        side (str): Which side to set.
        value (float): The normalized value in range [0.0, 1.0] to set the rumble to.
    """
    def set_rumble(self, side: str, value: float) -> None:
        # Set up function argument types and return type
        if side.upper() == Hand.LEFT:
            self.rumble[0] = max(0.0, min(1.0, value))
        elif side.upper() == Hand.RIGHT:
            self.rumble[1] = max(0.0, min(1.0, value))
        XInputSetState = xinput.XInputSetState
        XInputSetState.argtypes = [ctypes.c_uint,
                                   ctypes.POINTER(XINPUT_VIBRATION)]
        XInputSetState.restype = ctypes.c_uint
        vibration = XINPUT_VIBRATION(
            int(self.rumble[0] * 65535), int(self.rumble[1] * 65535))
        XInputSetState(self.device_number, ctypes.byref(vibration))

    """
    Get the left analog stick's X position.

    Returns:
        float: The X position in range [-1.0, 1.0].
    """
    def get_left_x(self) -> float:
        return self.get_axis(Axis.LX)

    """
    Get the left analog stick's Y position.

    Returns:
        float: The Y position in range [-1.0, 1.0].
    """
    def get_left_y(self) -> float:
        return self.get_axis(Axis.LY)

    """
    Get the right analog stick's X position.

    Returns:
        float: The X position in range [-1.0, 1.0].
    """
    def get_right_x(self) -> float:
        return self.get_axis(Axis.RX)

    """
    Get the right analog stick's Y position.

    Returns:
        float: The Y position in range [-1.0, 1.0].
    """
    def get_right_y(self) -> float:
        return self.get_axis(Axis.RY)

    """
    Get the left trigger axis value.

    Returns:
        float: The trigger axis value in range [0.0, 1.0].
    """
    def get_left_trigger(self) -> float:
        return self.get_axis(Axis.LTrigger)

    """
    Get the right trigger axis value.

    Returns:
        float: The trigger axis value in range [0.0, 1.0].
    """
    def get_right_trigger(self) -> float:
        return self.get_axis(Axis.RTrigger)

    """
    Get the Y button state of the controller.

    Returns:
        bool: The state of the Y button.
    """
    def get_y_button(self) -> bool:
        return self.get_button(Button.Y)

    """
    Get the X button state of the controller.

    Returns:
        bool: The state of the X button.
    """
    def get_x_button(self) -> bool:
        return self.get_button(Button.X)

    """
    Get the B button state of the controller.

    Returns:
        bool: The state of the B button.
    """
    def get_b_button(self) -> bool:
        return self.get_button(Button.B)

    """
    Get the A button state of the controller.

    Returns:
        bool: The state of the A button.
    """
    def get_a_button(self) -> bool:
        return self.get_button(Button.A)

    """
    Get the bumper state of the controller.

    Args:
        side (str): Which hand, left or right.

    Returns:
        bool: The state of the bumper.
    """
    def get_bumper(self, side: str) -> bool:
        if side.upper() == Hand.LEFT:
            return self.get_button(Button.BUMPER_L)
        if side.upper() == Hand.RIGHT:
            return self.get_button(Button.BUMPER_R)
    
    """
    Get the left stick button state of the controller.
    
    Returns:
        bool: The state of the left stick button.
    """
    def get_left_bumper(self) -> bool:
        return self.get_button(Button.BUMPER_L)
    
    """
    Get the right stick button state of the controller.

    Returns:
        bool: The state of the right stick button.
    """
    def get_right_bumper(self) -> bool:
        return self.get_button(Button.BUMPER_R)

    """
    Get the start button state of the controller.

    Returns:
        bool: The state of the start button.
    """
    def get_start_button(self) -> bool:
        return self.get_button(Button.START)

    """
    Get the back button state of the controller.

    Returns:
        bool: The state of the back button.
    """
    def get_back_button(self) -> bool:
        return self.get_button(Button.BACK)

    """
    Get the dpad state of the controller.

    Returns:
        int: The state of the dpad.
    """
    def get_dpad(self) -> int:
        if not self.get_button(Button.DPAD_L) and not self.get_button(Button.DPAD_R) and self.get_button(Button.DPAD_U) and not self.get_button(Button.DPAD_D):
            return 0
        elif not self.get_button(Button.DPAD_L) and self.get_button(Button.DPAD_R) and self.get_button(Button.DPAD_U) and not self.get_button(Button.DPAD_D):
            return 45
        elif not self.get_button(Button.DPAD_L) and self.get_button(Button.DPAD_R) and not self.get_button(Button.DPAD_U) and not self.get_button(Button.DPAD_D):
            return 90
        elif not self.get_button(Button.DPAD_L) and self.get_button(Button.DPAD_R) and not self.get_button(Button.DPAD_U) and self.get_button(Button.DPAD_D):
            return 135
        elif not self.get_button(Button.DPAD_L) and not self.get_button(Button.DPAD_R) and not self.get_button(Button.DPAD_U) and self.get_button(Button.DPAD_D):
            return 180
        elif self.get_button(Button.DPAD_L) and not self.get_button(Button.DPAD_R) and not self.get_button(Button.DPAD_U) and self.get_button(Button.DPAD_D):
            return 225
        elif self.get_button(Button.DPAD_L) and not self.get_button(Button.DPAD_R) and not self.get_button(Button.DPAD_U) and not self.get_button(Button.DPAD_D):
            return 270
        elif self.get_button(Button.DPAD_L) and not self.get_button(Button.DPAD_R) and self.get_button(Button.DPAD_U) and not self.get_button(Button.DPAD_D):
            return 315
        return -1

    """
    Set the left rumble output for the HID.

    Args:
        value (float): The normalized value in range [0.0, 1.0] to set the rumble to.
    """
    def set_left_rumble(self, value: float) -> None:
        self.set_rumble(Hand.LEFT, value)

    """
    Set the right rumble output for the HID.

    Args:
        value (float): The normalized value in range [0.0, 1.0] to set the rumble to.
    """
    def set_right_rumble(self, value: float) -> None:
        self.set_rumble(Hand.RIGHT, value)

    """
    Handle the state changed event.

    Args:
        state (XINPUT_STATE): The state of the controller.
    """
    def on_state_changed(self, state):
        pass

    """
    Handle the axis event.

    Args:
        axis (str): The axis that changed.
        value (float): The value of the axis.
    """
    def on_axis(self, axis, value):
        pass

    """
    Handle the button event.

    Args:
        button (int): The button that changed.
        state (bool): The state of the button.
    """
    def on_button(self, button, state):
        pass

    """
    Handle the missed packet event.

    Args:
        number (int): The number of missed packets.
    """

    def on_missed_packet(self, number):
        pass


XboxController.register_event_type("on_state_changed")
XboxController.register_event_type("on_axis")
XboxController.register_event_type("on_button")
XboxController.register_event_type("on_missed_packet")
