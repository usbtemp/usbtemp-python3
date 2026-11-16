import struct
import time

import serial


class ThermometerException(Exception):
    pass


class RomCode(bytes):
    """Probe serial number: the 8 ROM bytes, shown as hex by str() and print()."""
    def __str__(self):
        return self.hex()

    def __repr__(self):
        return "RomCode('%s')" % self.hex()


ROM_SIZE = 8
SP_SIZE = 9
SP_TH = 2
SP_TL = 3
SP_CONFIG = 4

# DS18B20 commands.
CMD_READ_ROM = 0x33
CMD_SKIP_ROM = 0xcc
CMD_CONVERT_T = 0x44
CMD_READ_SCRATCHPAD = 0xbe
CMD_WRITE_SCRATCHPAD = 0x4e
CMD_COPY_SCRATCHPAD = 0x48

# Configuration register: bits 6:5 hold the resolution, the other bits are fixed.
CONFIG_MASK = 0x9f
CONFIG_FIXED = 0x1f

# Seconds to wait for the adapter's reply.
READ_TIMEOUT = 0.5


class Thermometer:
    """
    USB Thermometer Middleware
    """
    MinPrecision = 9
    MaxPrecision = 12

    def __init__(self, port):
        self.port = port
        self.uart = None

    def Open(self):
        if not self.uart or not self.uart.is_open:
            # Lock the port so no other program can use it during a measurement
            # (Windows always opens serial ports exclusively).
            self.uart = serial.Serial(self.port, timeout = READ_TIMEOUT, exclusive = True)

    def Close(self):
        if self.uart and self.uart.is_open:
            self.uart.close()
            self.uart = None

    def Rom(self):
        self._command(CMD_READ_ROM)
        return RomCode(self._readBlock(ROM_SIZE))

    def Measure(self):
        """Start a temperature conversion."""
        self._command(CMD_SKIP_ROM, CMD_CONVERT_T)

    def Acquire(self):
        """Read the result of the last conversion, in degrees Celsius."""
        scratchpad = self._readScratchpad()
        temp = struct.unpack('<h', scratchpad[0:2])[0]
        return float(temp) / 16.0

    def Temperature(self):
        """Measure, wait for the conversion (750 ms at 12 bits) and acquire."""
        self.Measure()
        time.sleep(0.8)
        return self.Acquire()

    def _readScratchpad(self):
        """Read the scratchpad and check that it comes from a DS18B20."""
        self._command(CMD_SKIP_ROM, CMD_READ_SCRATCHPAD)
        scratchpad = self._readBlock(SP_SIZE)
        if (scratchpad[SP_CONFIG] & CONFIG_MASK) != CONFIG_FIXED:
            raise ThermometerException('Invalid device')
        return scratchpad

    def SetPrecision(self, precision):
        """Set the resolution (9..12 bits) and save it to the probe's EEPROM."""
        if (not isinstance(precision, int) or isinstance(precision, bool)
                or not self.MinPrecision <= precision <= self.MaxPrecision):
            raise ValueError('Precision must be between %d and %d bits' % (self.MinPrecision, self.MaxPrecision))
        config = CONFIG_FIXED | ((precision - self.MinPrecision) << 5)
        scratchpad = self._readScratchpad()
        if scratchpad[SP_CONFIG] == config:
            return
        # Write Scratchpad: TH, TL and config (TH/TL kept as they are).
        self._command(CMD_SKIP_ROM, CMD_WRITE_SCRATCHPAD, scratchpad[SP_TH], scratchpad[SP_TL], config)
        # Copy Scratchpad to EEPROM so the setting survives power loss.
        self._command(CMD_SKIP_ROM, CMD_COPY_SCRATCHPAD)

    def GetPrecision(self):
        """Current resolution, 9..12 bits."""
        scratchpad = self._readScratchpad()
        return ((scratchpad[SP_CONFIG] >> 5) & 0x03) + self.MinPrecision

    def _clear(self):
        """Check that the port is open and discard any stale data."""
        if not self.uart or not self.uart.is_open:
            raise ThermometerException('Device is not connected')
        self.uart.reset_input_buffer()
        self.uart.reset_output_buffer()

    def _owReset(self):
        self._clear()
        self.uart.baudrate = 9600
        try:
            self.uart.write(b'\xf0')
            r = self.uart.read(1)
        finally:
            # Always return to data speed, even if the write or read failed.
            self.uart.baudrate = 115200
        if len(r) != 1:
            raise ThermometerException('Read timeout')
        d = r[0]
        if d == 0xf0:
            raise ThermometerException('No device present')
        if d == 0x00:
            raise ThermometerException('Short circuit')
        if 0x10 <= d <= 0xe0:
            return
        raise ThermometerException('Presence error: 0x%02x' % d)

    def _owWriteByte(self, byte):
        w = []
        for _ in range(8):
            w.append(0xff if byte & 0x01 else 0x00)
            byte >>= 1
        self._clear()
        self.uart.write(bytes(w))
        r = self.uart.read(8)
        if len(r) != 8:
            raise ThermometerException('Read timeout')
        value = 0
        for b in r:
            value >>= 1
            if b == 0xff:
                value |= 0x80
        return value

    def _owWrite(self, byte):
        b = self._owWriteByte(byte)
        if b != byte:
            raise ThermometerException('Invalid response')

    def _owRead(self):
        return self._owWriteByte(0xff)

    def _command(self, *commands):
        """Reset the bus and send the command bytes."""
        self._owReset()
        for byte in commands:
            self._owWrite(byte)

    def _readBlock(self, n):
        """Read n bytes; the last one is the CRC of the bytes before it."""
        data = bytes([self._owRead() for _ in range(n)])
        if self._crc8(data[:-1]) != data[-1]:
            raise ThermometerException('CRC error')
        return data

    @staticmethod
    def _crc8(data):
        crc = 0
        for byte in data:
            for _ in range(8):
                mix = (crc ^ byte) & 0x01
                crc >>= 1
                if mix:
                    crc ^= 0x8c
                byte >>= 1
        return crc

if __name__ == '__main__':
    thermometer = Thermometer('/dev/ttyUSB0')
    try:
        thermometer.Open()
        print("Device ROM is %s" % thermometer.Rom())
        print("Temperature is %0.2f °C" % thermometer.Temperature())
    except Exception as e:
        print(e)
    finally:
        thermometer.Close()
