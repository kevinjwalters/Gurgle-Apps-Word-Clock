import machine
import neopixel

from background import MatrixBackground

_MP_CLASSIC_TIMING = (400-100, 850+100, 800, 450)
_CUSTOM_TIMING = [sum(x) for x in zip(_MP_CLASSIC_TIMING,
                                     (-50, +50 , 0, 0))]
_CP_2022_TIMIMG =  (300, 900, 700, 500)

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colors are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

class ws2812b_matrix:

    def __init__(self, pin, width, height, background=None):
        self.width = width
        self.height = height
        self.background = background

        self.np = neopixel.NeoPixel(machine.Pin(pin), width * height,
                                    timing=_CP_2022_TIMIMG)
        self.gamma = 2.2
        self.gamma_table = bytearray([int(pow(x / 255.0, self.gamma) * 254.99 + 1.0) for x in range(256)])
        self.gamma_table[0] = 0
        self.lut = bytearray(list(range(256)))
        self.char = [0x3c,0x56,0x93,0xdb,0xff,0xff,0xdd,0x89]
        self.brightness = 7
        self.max_brightness = 15
        self.gamma_correction = True
        count = self.width * self.height
        self._rainbow = [ wheel(int(x * 256 / count)) for x in range(count)]

        self.set_brightness(self.brightness)


    def show_char(self, char, color=(255, 255, 255)):
        return self._show(char, color)

    def show_char_with_color_array(self, char, color_array):
        return self._show(char, color_array)

    def _show(self, char, color_any):
        self.char = char
        fixed_adjusted_color = self.adjust_for_brightness(color_any) if len(color_any) == 3 else None
        # set_time() must be called on background beforehand for render to work
        bg_image = None if self.background is None else self.background.renderBackground(self.lut)
        fg_image = None if self.background is None else self.background.renderForeground(self.lut)
        for i in range(self.height):
            for j in range(self.width):
                np_idx = i * self.width + j
                im_idx = 3 * np_idx
                # (255, 255, 255) is used for transparency in foreground image
                if (fg_image is not None and
                    not (fg_image[im_idx] == MatrixBackground.TRANSPARENT_LEVEL
                         and fg_image[im_idx+1] == MatrixBackground.TRANSPARENT_LEVEL
                         and fg_image[im_idx+2] == MatrixBackground.TRANSPARENT_LEVEL)):
                    self.np[np_idx] = (fg_image[im_idx], fg_image[im_idx+1], fg_image[im_idx+2])
                else:
                    if char[i] & (1 << self.width - 1 - j):
                        if fixed_adjusted_color is None:
                            adjusted_color = self.adjust_for_brightness(color_any[i*8+j])
                            self.np[np_idx] = adjusted_color
                        else:
                            self.np[np_idx] = fixed_adjusted_color
                    else:
                        self.np[np_idx] = (0, 0, 0) if bg_image is None else (bg_image[im_idx], bg_image[im_idx+1], bg_image[im_idx+2])
        self.np.write()
        return True

    def set_brightness(self, brightness):
        if 0 <= brightness <= self.max_brightness:
            if self.brightness == brightness:
                return
            self.brightness = brightness
            if self.gamma_correction:
                brightness_scale = (self.brightness+1)/(self.max_brightness+1)
                for x in range(256):
                    self.lut[x] = self.gamma_table[int(x * brightness_scale)]
        else:
            raise ValueError(f"Brightness must be between 0 and {self.max_brightness}")

    def set_pixel(self, x, y, color):
        self.np[x*8+y] = color
        self.np.write()

    def adjust_for_brightness(self, color):
        return (self.lut[color[0]], self.lut[color[1]], self.lut[color[2]])

    def show(self):
        self.np.write()

    def clear(self):
        for i in range(self.width*self.height):
            self.np[i] = (0, 0, 0)
        self.np.write()

    def fill(self, color):
        for i in range(self.width*self.height):
            self.np[i] = color
        self.np.write()

    def set_char(self, char):
        self.char = char

    def get_char(self):
        return self.char

    def get_rainbow_array(self):
        return self._rainbow

    def set_background(self, background):
        self.background = background
