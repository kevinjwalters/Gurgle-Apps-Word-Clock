"""
    Project Name: board.py
    File Name: board.py
    Author: GurgleApps.com
    Date: 2021-04-01
    Description: Detects the board type
"""
import os

class Board:
    class BoardType:
        PICO_W = 'Raspberry Pi Pico W'
        PICO = 'Raspberry Pi Pico'
        PICO_2_W = 'Raspberry Pi Pico 2 W'
        PICO_2 = 'Raspberry Pi Pico 2'
        ESP8266 = 'ESP8266'
        ESP32_C3 = 'ESP32-C3'
        ESP32 = 'ESP32'
        UNKNOWN = 'Unknown'

        FAMILY_PICO = (PICO, PICO_W, PICO_2, PICO_2_W)

    def __init__(self):
        self.type = self.detect_board_type()

    def detect_board_type(self):
        sysname = os.uname().sysname.lower()
        machine = os.uname().machine.lower()

        if sysname == 'rp2':
            if 'pico 2 w' in machine:
                return self.BoardType.PICO_2_W
            elif 'pico 2' in machine:
                return self.BoardType.PICO_2
            elif 'pico w' in machine:
                return self.BoardType.PICO_W
            elif 'pico' in machine:
                return self.BoardType.PICO
            else:
                return self.BoardType.UNKNOWN
        elif sysname == 'esp8266':
            return self.BoardType.ESP8266
        elif sysname == 'esp32':
            if 'esp32c3' in machine:
                return self.BoardType.ESP32_C3
            else:
                return self.BoardType.ESP32
        # Add more conditions for other boards here
        else:
            return self.BoardType.UNKNOWN
