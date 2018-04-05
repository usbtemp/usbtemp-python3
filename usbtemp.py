import serial
import struct
import time

class Thermometer:

    def __init__(self, port, timeout = 1):
        self.port = port;
        self.timeout = timeout;
        self.uart = None

    def Open(self):
       if not self.uart or not self.uart.isOpen():
            self.uart = serial.Serial(self.port, timeout = self.timeout);

    def Close(self):
       if self.uart and self.uart.isOpen():
            self.uart.close()
            self.uart = None

    def Rom(self):
        self._owReset();
        self._owWrite(0x33)
        data = self._readBytes(8)
        if (self._crc8(data[0:7]) != data[7]):
            raise Exception('CRC error')
        return data.hex()

    def Temperature(self):
        self._owReset();
        self._owWrite(0xcc)
        self._owWrite(0x44)
        time.sleep(1)
        self._owReset();
        self._owWrite(0xcc)
        self._owWrite(0xbe)
        scratchpad = self._readBytes(9)
        if (self._crc8(scratchpad[0:8]) != scratchpad[8]):
            raise Exception('CRC error')
        temp = struct.unpack('<h', scratchpad[0:2])[0]
        return float(temp) / 16.0

    def _clear(self):
        self.uart.reset_input_buffer()
        self.uart.reset_output_buffer()

    def _owReset(self):
        if not self.uart or not self.uart.isOpen():
            raise Exception('Device is not connected')
        self._clear()
        self.uart.baudrate = 9600
        self.uart.write(b'\xf0')
        r = self.uart.read(1)
        self.uart.baudrate = 115200
        if len(r) != 1:
            raise Exception('Read/Write error')
        d = r[0]
        if d == 0xf0:
            raise Exception('No device present')
        elif d == 0x00:
            raise Exception('Short circuit');
        elif 0x10 <= d <= 0xe0:
            return
        else:
            raise Exception('Presence error: 0x%02x' % d)

    def _owWriteByte(self, byte):
        if not self.uart or not self.uart.isOpen():
            raise Exception('Device is not connected')
        w = []
        for i in range(8):
            w.append(0xff if byte & 0x01 else 0x00)
            byte >>= 1
        self._clear()
        self.uart.write(bytes(w))
        r = self.uart.read(8)
        if len(r) != 8:
            raise Exception('Write error')
        value = 0
        for b in iter(r):
            value >>= 1
            if b == 0xff:
                value |= 0x80
        return value

    def _owWrite(self, byte):
        b = self._owWriteByte(byte)
        if b != byte:
            raise Exception('Invalid response')

    def _owRead(self):
        return self._owWriteByte(0xff)

    def _readBytes(self, n):
        return bytes([self._owRead() for i in range(n)])

    def _crc8(self, data):
        crc = 0
        for byte in iter(data):
            for i in range(8):
                mix = (crc ^ byte) & 0x01
                crc >>= 1
                if mix:
                    crc ^= 0x8c
                byte >>= 1
        return crc

if __name__ == '__main__':
    thermometer = Thermometer('/dev/ttyUSB0')
    thermometer.Open()
    try:
        print("Device ROM is %s" % thermometer.Rom())
        print("Temperature is %0.2f °C" % thermometer.Temperature())
    except Exception as e:
        print(e)
    thermometer.Close()
