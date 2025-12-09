# SPDX-FileCopyrightText: 2025 Kevin J. Walters
#
# SPDX-License-Identifier: MIT

import array
import math
import random

import matrix_fonts


class Layout:
    _layouts = {}
    STD_SPACING=8.125  # in mm

    def __init__(self, width, height, spacing_mm):
        self.width = width
        self.height = height
        self.width_mm = width * spacing_mm
        self.height_mm = height * spacing_mm
        self.spacing_mm = spacing_mm
        self.led_count = width * height
        self.pixel_diamater = 5

        # These are centre positions
        self.led_pos = array.array("f", [0.0] * (self.led_count * 2))
        self.right_x = self.spacing_mm * (self.width - 1) / 2.0
        self.left_x = 0.0 - self.right_x
        self.bottom_y = self.spacing_mm * (self.height - 1) / 2.0
        self.top_y = 0.0 - self.bottom_y
        idx = 0
        for y_idx in range(self.height):
            for x_idx in range(self.width):
                self.led_pos[idx] = self.left_x + x_idx * self.spacing_mm
                self.led_pos[idx + 1] = self.top_y + y_idx * self.spacing_mm
                idx += 2

    @classmethod
    def getLayout(cls, width, height, spacing_mm):
        spc = cls.STD_SPACING if spacing_mm is None else spacing_mm
        layout = cls._layouts.get((width, height, spc))
        if layout is None:
            layout = Layout(width, height, spc)
            cls._layouts[(width, height, spc)] = layout
        return layout

    @classmethod
    def vertical_line_near_pixel(cls, near_distance, x1, y1b, y1t, x2, y2):
        """If line runs within near_distance from (x2, y2) then
           (distance, y_relint, beyond) is returned otherwise None"""
        x_distance = abs(x2 - x1)
        if y1t <= y2 <= y1b:  # point is next to line
            return (x_distance, (y2 - y1t) / (y1b - y1t), False)

        distance = float("Inf")
        if y2 > y1b and y2 < y1b + near_distance:
            distance = math.sqrt(x_distance * x_distance + (y2 - y1b) * (y2 - y1b))
            return (distance, 1, True)
        elif y2 < y1t and y2 > y1t - near_distance:
            distance = math.sqrt(x_distance * x_distance + (y2 - y1t) * (y2 - y1t))
            return (distance, 0, True)

        return None

    def get_pixels_through_x(self, l_x, near_distance):
        near_idxs = []
        # Scan the top row for nearby pixels
        for idx in range(self.width):
            if abs(self.led_pos[idx * 2] - l_x) < near_distance:
                near_idxs.append(idx)
        row_near_count = len(near_idxs)
        if row_near_count == 0:
            return near_idxs

        # Duplicate first row to cover all the rows
        near_idxs = near_idxs * self.height
        for idx in range(row_near_count, len(near_idxs)):
            near_idxs[idx] += idx // row_near_count * self.width
        return near_idxs


LOCAL_T = 0
EPOCH_T_S = 1
EPOCH_T_NS = 2

class MatrixBackground:
    TRANSPARENT_LEVEL = 255
    TRANSPARENT = (TRANSPARENT_LEVEL, TRANSPARENT_LEVEL, TRANSPARENT_LEVEL)
    BLACK = (0, 0, 0)

    _images = {}
    _UNDEF_TIME = ((1970, 1, 1, 0, 0, 0, 3, 1),
                   0,
                   0)

    def __init__(self, width, height, spacing_mm=None, *, layers=("bg",)):
        self.layout = Layout.getLayout(width, height, spacing_mm)
        self.layers = layers
        self.images = [self.getImage(width, height, layer) for layer in layers]
        self.image = self.images[0]  # the image for first layer
        self.update_rate = 0
        self.running = False
        self._start_time = [0] * 3
        self._time = list(self._UNDEF_TIME)

    @classmethod
    def getImage(cls, width, height, layer):
        image = cls._images.get((width, height, layer))
        if image is None:
            image = bytearray(width * height * 3)
            cls._images[(width, height, layer)] = image
        return image

    def renderBackground(self, lut):
        return None

    def renderForeground(self, lut):
        return None

    def clearScreen(self, color=None):
        for idx, layer in enumerate(self.layers):
            color = (self.TRANSPARENT if layer == "fg" else self.BLACK) if color is None else color
            image = self.images[idx]
            for im_idx in range(0, len(self.image), 3):
                image[im_idx] = color[0]
                image[im_idx + 1] = color[1]
                image[im_idx + 2] = color[2]

    def start(self, local_time, epoch_time, epoch_time_ns):
        self._start_time[LOCAL_T] = local_time
        self._start_time[EPOCH_T_S] = epoch_time
        self._start_time[EPOCH_T_NS] = epoch_time_ns
        self.clearScreen()
        self.running = True

    def stop(self):
        self._start_time = list(self._UNDEF_TIME)
        self.running = False

    def setTime(self, local_time, epoch_time, epoch_time_ns):
        self._time[LOCAL_T] = local_time
        self._time[EPOCH_T_S] = epoch_time
        self._time[EPOCH_T_NS] = epoch_time_ns

    def _write(self,  text, color, image, lut, *,
               shift_x=0, shift_y=0):
        char_list = matrix_fonts.textFont1.get(text)
        if char_list is None:
            return

        # move down/up
        if shift_y > 0:
            char_list = [0 if idx < shift_y else char_list[idx - shift_y] for idx in range(self.layout.height)]
        elif shift_y < 0:
            char_list = [0 if idx >= self.layout.height - shift_y else char_list[idx + shift_y] for idx in range(self.layout.height)]

        idx = 0
        width = self.layout.width
        for row in char_list:
            # move left/right
            row_val = row >> shift_x if shift_x > 0 else (row << (0 - shift_x) if shift_x < 0 else row)
            for j in range(width):
                pixel = row_val & (1 << width - 1 - j)
                image[idx] = lut[color[0]] if pixel else 0
                image[idx + 1] = lut[color[1]] if pixel else 0
                image[idx + 2] = lut[color[2]] if pixel else 0
                idx += 3

    def _write_sprite(self, sprite, palette, image, lut, *,
                      intensity=1,
                      width=8, height=8, shift_x=0, shift_y=0):
        s_idx = -1
        d_width = self.layout.width
        d_height = self.layout.height
        for y in range(height):
            for x in range(width):
                pos_x = x + shift_x
                pos_y = y + shift_y
                s_idx += 1
                if not 0 <= pos_x < d_width or not 0 <= pos_y < d_height:
                    continue  # not on the display
                color_idx = sprite[s_idx]
                color = palette[color_idx]
                if color is MatrixBackground.TRANSPARENT:
                    r = g = b = MatrixBackground.TRANSPARENT_LEVEL
                else:
                    r = lut[round(color[0] * intensity)]
                    g = lut[round(color[1] * intensity)]
                    b = lut[round(color[2] * intensity)]
                idx = 3 * (pos_y * d_width + pos_x)
                image[idx] = r
                image[idx + 1] = g
                image[idx + 2] = b


# Field offsets in compact, efficient, slightly ugly _rain_drops
_DP_X = 0
_DP_Y = 1
_DP_SPEED = 2
_DP_TRAIL_LENGTH = 3
_DP_HEAD_BRI = 4

class PrecipitationBackground(MatrixBackground):
    """Parent class for rain and snow."""
    def __init__(self, width, height, spacing_mm=None, *,
                 max_drops=None,
                 drop_color=None):
        super().__init__(width, height, spacing_mm)

        self.update_rate = 15
        self._near_distance = 0.55 * self.layout.spacing_mm
        self._gone_y = self.layout.bottom_y + self.layout.spacing_mm
        self._max_drops = max_drops
        self._last_time = [0] * 3
        # This is a flattened list of [x, y, speed, trail_length, head_bri]
        self._rain_drops = array.array('f', [0.0] * (5 * self._max_drops))
        self._drop_color = drop_color
        self._color_channel = None
        if drop_color[1] == 0 and drop_color[2] == 0:
            self._color_channel = 0
        elif drop_color[0] == 0 and drop_color[2] == 0:
            self._color_channel = 1
        elif drop_color[0] == 0 and drop_color[1] == 0:
            self._color_channel = 2

    @classmethod
    def _raindrops_prob(cls, duration_s):
        selecta = random.random()
        count_per_s = ((4 + 3 * random.random()) if selecta < 0.7
                       else (8 * 8 * random.random()) if selecta < 0.900
                             else (17 * 8 * random.random() if selecta < 0.975
                                   else (50 * 8 * random.random())))
        return round(count_per_s * duration_s)

    def _trailLength(self):
        raise NotImplementedError

    def _removeadddrops(self, dur_s):
        for drop_no in range(self._max_drops):
            base_idx = drop_no * 5
            if self._rain_drops[base_idx + _DP_HEAD_BRI] == 0.0:
                continue
            self._rain_drops[base_idx + _DP_Y] += self._rain_drops[base_idx + _DP_SPEED] * dur_s
            if self._rain_drops[base_idx + _DP_Y] - self._rain_drops[base_idx + _DP_TRAIL_LENGTH] > self._gone_y:
                self._rain_drops[base_idx + _DP_HEAD_BRI] = 0.0

        # Add new drops based on probability and time elasped since last addition
        new_drop_count = self._raindrops_prob(dur_s)
        drops_added = 0
        for drop_no in range(self._max_drops):
            base_idx = drop_no * 5
            if self._rain_drops[base_idx + _DP_HEAD_BRI] != 0.0:
                continue

            self._rain_drops[base_idx + _DP_X] = random.uniform(0 - self.layout.width_mm * 0.52,
                                                                self.layout.width_mm * 0.52)
            self._rain_drops[base_idx + _DP_Y] = random.uniform(0 - self.layout.height_mm * 0.6,
                                                                0 - self.layout.height_mm * 0.5)
            self._rain_drops[base_idx + _DP_SPEED] = self._speed()
            self._rain_drops[base_idx + _DP_TRAIL_LENGTH] = self._trailLength()
            self._rain_drops[base_idx + _DP_HEAD_BRI] = random.uniform(0.3, 1.0)
            drops_added += 1
            if drops_added >= new_drop_count:
                break

    def renderBackground(self, lut):
        # move existing drops and remove any drops that have fallen
        # off the display by setting brightness to zero
        if self._last_time[EPOCH_T_S] == 0:
            self._last_time[:] = self._time
        delta_s = (self._time[EPOCH_T_NS] - self._last_time[EPOCH_T_NS]) * 1e-9
        self._removeadddrops(delta_s)

        # Clear green values
        target = self.image
        if self._color_channel is None:
            self.clearScreen()
        else:
            for e_idx in range(self._color_channel, len(target), 3):
                target[e_idx] = 0
        # Render rain drops in green
        il_radius_outer = (self.layout.pixel_diamater + 1) / 2.0
        il_radius_inner = il_radius_outer / 3.0
        drop_r, drop_g, drop_b = self._drop_color
        for drop_no in range(self._max_drops):
            x, y, speed, trail_length, head_bri = self._rain_drops[drop_no * 5:(drop_no * 5 + 5)]
            if head_bri == 0.0:
                continue  # not a rain drop

            for idx in self.layout.get_pixels_through_x(x, self._near_distance):
                distances = self.layout.vertical_line_near_pixel(self.layout.spacing_mm,
                                                                 x, y, y - trail_length,
                                                                 self.layout.led_pos[idx * 2],
                                                                 self.layout.led_pos[idx * 2 + 1])
                if distances:
                    trail_bri = distances[1] * distances[1] * 0.75 + 0.25
                    dist_bri =  1.0 if distances[0] < il_radius_inner else max(0, (il_radius_outer - distances[0])) / il_radius_outer
                    brightness = trail_bri * head_bri * dist_bri
                    if brightness > 0.0:
                        # Use a max() strategy to combine "droplets" on LEDs
                        im_idx = idx * 3
                        if drop_r:
                            level = min(drop_r, round(brightness * drop_r))
                            target[im_idx] = max(lut[level], target[im_idx])
                        if drop_g:
                            level = min(drop_g, round(brightness * drop_g))
                            target[im_idx + 1] = max(lut[level], target[im_idx + 1])
                        if drop_b:
                            level = min(drop_b, round(brightness * drop_b))
                            target[im_idx + 2] = max(lut[level], target[im_idx + 2])

        self._last_time[:] = self._time
        return self.image

    def stop(self):
        super().stop()
        # "Remove" all the rain drops by setting brightness to zero
        for drop_no in range(self._max_drops):
            self._rain_drops[drop_no * 5 + _DP_HEAD_BRI] = 0.0


class DigitalRainMB(PrecipitationBackground):
    """A falling digital rain effect in green remniscent of a certain science fiction/action film."""

    def __init__(self, width, height, spacing_mm=None):
        super().__init__(width, height, spacing_mm,
                         max_drops=12,
                         drop_color=(0, 255, 0))

    def _trailLength(self):
        return random.uniform(10.0, 55.0) * 0.5 + random.uniform(25.0, 35.0) * 0.5

    def _speed(self):
        return random.uniform(10, 25) if random.random() < 0.95 else random.uniform(3, 90)


class SnowMB(PrecipitationBackground):
    """A snow effect for the Juggalos & Juggalettes dreaming of a white Christmas."""
    def __init__(self, width, height, spacing_mm=None):
        super().__init__(width, height, spacing_mm,
                         max_drops=5,
                         drop_color=(140, 140, 140))

    def _trailLength(self):
        return 3

    def _speed(self):
        return random.uniform(15, 20)


class MinutesOffsetMB(MatrixBackground):
    """Shows the offset between displayed time and actual time with a vertical blue bar
       from left side for -2 minutes to right side for +2 minutes. The bar disappears
       when the displayed time is accurate."""

    def __init__(self, width, height, spacing_mm=None):
        super().__init__(width, height, spacing_mm)

        self.color = (0, 0, 32)
        self.update_rate = 1
        half_width = width // 2
        self._cols = {-2: [half_width - half_width],
                      -1: [half_width - half_width // 2],
                      0: [],
                      1: [half_width + half_width // 2 - 1],
                      2: [half_width + half_width - 1]}

    def renderBackground(self, lut):
        minute = self._time[LOCAL_T][4]
        rounded_minute = round(minute / 5) * 5
        error = minute - rounded_minute
        self.clearScreen()
        r = lut[self.color[0]]
        g = lut[self.color[1]]
        b = lut[self.color[2]]
        for col in self._cols[error]:
            for idx in range(col * 3, len(self.image), self.layout.width * 3):
                self.image[idx] = r
                self.image[idx + 1] = g
                self.image[idx + 2] = b

        return self.image


class MinutesDigitMB(MatrixBackground):
    """Shows the final digit of the minutes as a background.
       This scrolls off and on when the minute value changes."""
    def __init__(self, width, height, spacing_mm=None):
        super().__init__(width, height, spacing_mm)

        self.color = (16, 8, 0)
        self.update_rate = 1
        self._last_digit = None
        self._pos_y = 1

    def renderBackground(self, lut):
        digit = self._time[LOCAL_T][4] % 10  # last digit of minutes
        offset_y = 0
        if self._last_digit != digit:
            seconds = self._time[LOCAL_T][5]
            if seconds >= 17:
                self._last_digit = digit
            else:
                if seconds >= 8:
                    offset_y = 16 - seconds
                else:
                    # move old digit off screen
                    offset_y = seconds + 1
                    digit = self._last_digit

        self._write(chr(ord('0') + digit), self.color,
                    self.image, lut,
                    shift_y=self._pos_y + offset_y)
        return self.image
