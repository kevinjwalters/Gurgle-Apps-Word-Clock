# SPDX-FileCopyrightText: 2025 Kevin J. Walters
#
# SPDX-License-Identifier: MIT

from background import MatrixBackground, LOCAL_T, EPOCH_T_NS
#from ws2812b_matrix import wheel


class HalloweenMB(MatrixBackground):
    SPOOKY_GHOST = bytearray([0, 0, 2, 2, 2, 0, 0,
                              0, 2, 2, 2, 2, 2, 0,
                              2, 2, 1, 2, 1, 2, 0,
                              0, 2, 2, 2, 2, 2, 0,
                              0, 2, 2, 0, 2, 2, 0,
                              0, 2, 2, 2, 2, 2, 0,
                              0, 0, 2, 2, 2, 0, 0,
                              0, 0, 0, 2, 2, 2, 2])
    SPOOKY_GHOST_WIDTH = 7
    SPOOKY_GHOST_HEIGHT = len(SPOOKY_GHOST) // SPOOKY_GHOST_WIDTH
    SPOOKY_EYE_COLOR = [0, 0, 0]
    SPOOKY_GHOST_PALETTE = [MatrixBackground.TRANSPARENT,
                            MatrixBackground.TRANSPARENT,  # SPOOKY_EYE_COLOR,
                            (254, 254, 254)
                           ]

    PUMPKIN = bytearray([0, 0, 0, 0, 0, 0, 5, 5, 0, 0, 0, 0,
                         0, 0, 2, 1, 2, 5, 5, 1, 2, 1, 0, 0,
                         0, 2, 1, 1, 2, 1, 2, 1, 1, 2, 1, 0,
                         1, 2, 3, 2, 3, 1, 2, 3, 2, 3, 1, 2,
                         1, 2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 2,
                         1, 2, 1, 2, 1, 4, 4, 1, 1, 2, 1, 2,
                         0, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 0,
                         0, 0, 2, 1, 2, 0, 0, 1, 2, 1, 0, 0])
    PUMPKIN_WIDTH = 12
    PUMPKIN_HEIGHT = len(PUMPKIN) // PUMPKIN_WIDTH
    PUMPKIN_PALETTE = [MatrixBackground.TRANSPARENT,
                       (160, 80, 0),
                       (100, 45, 0),
                       MatrixBackground.TRANSPARENT,  # (10, 10, 10),  # eyes
                       (192, 192, 0),
                       (0, 80, 0)]

    HAT = [0, 0, 0, 0, 1, 1, 0, 0,
           0, 0, 0, 1, 1, 0, 0, 0,
           0, 0, 0, 1, 1, 0, 0, 0,
           0, 0, 1, 1, 1, 1, 0, 0,
           0, 0, 1, 1, 1, 1, 0, 0,
           0, 1, 1, 1, 1, 1, 1, 0,
           1, 1, 1, 1, 1, 1, 1, 1,
           1, 2, 1, 3, 3, 1, 2, 1,
           1, 1, 2, 3, 3, 2, 1, 1,
           0, 0, 1, 1, 1, 1, 0, 0
           ]
    HAT_WIDTH = 8
    HAT_HEIGHT = len(HAT) // HAT_WIDTH
    HAT_PALETTE = [MatrixBackground.TRANSPARENT,
                   (0, 0, 120),
                   (0, 130, 0),
                   (210, 210, 0)
                  ]

    def __init__(self, width, height, spacing_mm=None):
        super().__init__(width, height, spacing_mm)

        self.color = (16, 8, 0)
        self.update_rate = 4


    ### TODO - work out how to deal with foreground and background together vs single image!!
    def renderForeground(self, lut):
        mins = self._time[LOCAL_T][4]
        secs = self._time[LOCAL_T][5]
        millisecs = self._time[EPOCH_T_NS] // 1_000_000 % 1000
        hires_secs = secs + millisecs * 1e-3

        ### Show an image as the displayed time in words changes
        ### Cycling through the three images
        if mins % 15 == 3 and 0 <= secs < 8:
            self.clearScreen()
            # ramp the brightness up and then down
            sprite_bri = min(1.0, 0.05 + 0.3 * (4.0 - abs(4 - hires_secs)))
            x_wiggle = secs % 2

            # Fiddle with a class variable inside an instance method...
            #self.SPOOKY_EYE_COLOR[:] = wheel(int(hires_secs * 95) % 256)
            self._write_sprite(self.SPOOKY_GHOST,
                               self.SPOOKY_GHOST_PALETTE,
                               lut,
                               intensity=sprite_bri,
                               width=self.SPOOKY_GHOST_WIDTH,
                               height=self.SPOOKY_GHOST_HEIGHT,
                               shift_x=x_wiggle,
                               shift_y=0)
        elif mins % 15 == 8 and 0 <= secs < 10:
            self.clearScreen()
            self._write_sprite(self.PUMPKIN,
                               self.PUMPKIN_PALETTE,
                               lut,
                               intensity=1.0,
                               width=self.PUMPKIN_WIDTH,
                               height=self.PUMPKIN_HEIGHT,
                               shift_x=10 - round((11 - hires_secs) * 2),
                               shift_y=0)
        elif mins % 15 == 13 and 0 <= secs < 10:
            self.clearScreen()
            self._write_sprite(self.HAT,
                               self.HAT_PALETTE,
                               lut,
                               intensity=1.0,
                               width=self.HAT_WIDTH,
                               height=self.HAT_HEIGHT,
                               shift_x=0,
                               shift_y=10 - round((11 - hires_secs) * 2))
        else:
            return None

        return self.image
