# usbtemp-python3
Python 3 `Thermometer` class for the [usbtemp.com USB thermometer](https://usbtemp.com/) and DS9097E compatible 1-wire adapters with one DS18B20 digital probe attached. Source code is in `usbtemp.py`.

### Requirements
Python 3 and [pyserial](https://pyserial.readthedocs.io/) 3.3 or newer, on Debian/Ubuntu:
```
sudo apt install python3-serial
```
On Linux the user needs read/write access to the serial port, usually by being a member of the `dialout` group.

### Installation
Copy `usbtemp.py` next to your script, or install it with pip, which also installs pyserial:
```
pip install git+https://github.com/usbtemp/usbtemp-python3.git
```

### Usage
```
from usbtemp import Thermometer, ThermometerException

thermometer = Thermometer('/dev/ttyUSB0')
try:
    thermometer.Open()
    print('ROM: %s' % thermometer.Rom())
    print('Temperature: %0.2f' % thermometer.Temperature())
except ThermometerException as e:
    print(e)
finally:
    thermometer.Close()
```
Running `python3 usbtemp.py` does the same with `/dev/ttyUSB0`.

### Thermometer class
| Member | Description |
|---|---|
| `Thermometer(port)` | serial port, e.g. `'/dev/ttyUSB0'` or `'COM3'` |
| `Open()` | open the serial port |
| `Close()` | close the serial port |
| `Rom()` | probe serial number, 8 bytes as `RomCode`, a `bytes` subclass whose `str()` is hexadecimal, e.g. `'28ff6a2b711603e0'` |
| `Measure()` | start temperature conversion |
| `Acquire()` | result of the last conversion, in degrees Celsius |
| `Temperature()` | `Measure()`, wait 800 ms, `Acquire()` |
| `SetPrecision(bits)` | set resolution 9..12 bits, saved to probe EEPROM |
| `GetPrecision()` | current resolution, 9..12 bits |
| `Thermometer.MinPrecision` | lowest resolution, 9 bits |
| `Thermometer.MaxPrecision` | highest resolution, 12 bits |

Use `Measure()` and `Acquire()` instead of `Temperature()` to wait less at lower resolution:

| Resolution | Step | Conversion time |
|---|---|---|
| 9 bits | 0.5 °C | 94 ms |
| 10 bits | 0.25 °C | 188 ms |
| 11 bits | 0.125 °C | 375 ms |
| 12 bits | 0.0625 °C | 750 ms |

### Errors
Probe and bus errors raise `ThermometerException`:

| Message | Cause |
|---|---|
| `Device is not connected` | `Open()` was not called or the port is closed |
| `Read timeout` | the adapter does not answer within 500 ms |
| `No device present` | no probe is connected |
| `Short circuit` | the 1-wire bus is shorted |
| `Presence error: 0x..` | unexpected response to the bus reset |
| `Invalid response` | a byte sent to the probe was not echoed back correctly |
| `CRC error` | the data read from the probe is corrupted |
| `Invalid device` | the probe is not a DS18B20 |

`SetPrecision()` raises `ValueError` when the resolution is not an integer between 9 and 12.
Serial port errors, e.g. a missing port, no permission, a port in use by another program or an unplugged adapter, raise pyserial's `serial.SerialException`.

### Reference
*Maxim Application Note 214* and *DS18B20 datasheet*.

This software is in alpha stage, contributions are welcome.
