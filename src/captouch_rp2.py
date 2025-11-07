# SPDX-FileCopyrightText: 2021,2025 James Brown, Kevin J. Walters
#
# SPDX-License-Identifier: MIT

# This is https://github.com/AncientJames/jtouch/blob/main/jtouch.py
# with a few tweaks and asyncio Pushbutton compatibility
# See https://github.com/gurgleapps/Gurgle-Apps-Word-Clock/issues/11

import rp2
import machine


_CAP_LOOP_MANTISSA = const(19)
_CAP_LOOP_EXPONENT = const(15)

_U32MAX = const((1 << 32) - 1)


@rp2.asm_pio(set_init=[rp2.PIO.OUT_LOW], fifo_join=rp2.PIO.JOIN_RX)
def capsense():
    # set y to the sample period count
    # 1048576 8.4ns at 125MHz (and 7.0ns at 150MHz)
    # 19 * 2^15 = 622592 repeats at about 2 cycles at 125MHz = 9.96ms
    mov(isr, null)
    set(y, _CAP_LOOP_MANTISSA)
    in_(y, 5)
    in_(null, _CAP_LOOP_EXPONENT)
    mov(y, isr)

    # clear the counter
    mov(x, invert(null))

    label('resample')
    # set pin to input...
    set(pindirs, 0)

    label('busy')
    # ...and wait for it to pull high
    jmp(pin, 'high')
    jmp(y_dec, 'busy')
    jmp('done')

    label('high')
    # set pin to output and pull low
    set(pindirs, 1)
    set(pins, 0)

    # while that's going on, count the time spent outside of the busy loop
    jmp(y_dec, 'dec1')
    jmp('done')
    label('dec1')
    jmp(y_dec, 'dec2')
    jmp('done')
    label('dec2')
    jmp(y_dec, 'dec3')
    jmp('done')
    label('dec3')
    jmp(y_dec, 'dec4')
    jmp('done')
    label('dec4')
    jmp(y_dec, 'dec5')
    jmp('done')
    label('dec5')

    # count this cycle and repeat
    jmp(x_dec, 'resample')

    label('done')
    # time's up - push the count
    mov(isr,x)
    push(noblock)


class TouchPad:
    """A PIO-based capacitive touch object with boolean and continuous values.

    :param int pin: The GPIO pin number.
    :param int sm_num: Optional PIO state machine number.
    :param bool calibrate_now: Perform an immediate pad calibration. Touch pad must not be used during calibration. Default True.
    :param int noise_threshold: The minimum noise threshold. Default 100.
    :param int press_threshold: The count value which indicates a touch or None for 3% of untouched value. Default None.
    :param int press_range: A fixed count range for the continuous scale or None for auto-ranging. Default None.
    :param int warmup: the number of update calls to use to calibrate the touch pad before it's ready for use. Default 20.
    """

    FIFO_LEN = 4 * 2  # RX FIFO is jopined with TX FIFO to enlarge it
    NOISE_MULTIPLIER = 4
    next_sm = 0

    def __init__(self, pin, sm_num=None, calibrate_now=True,
                 *,
                 noise_threshold=100,
                 press_threshold=None,
                 press_range=None,
                 warmup=20):
        self.warmup = warmup
        self.noise_threshold = noise_threshold
        self.frequency = 125_000_000  # Does not have to divide into cpu clock
        self.cap_loop_count = _CAP_LOOP_MANTISSA * 2**_CAP_LOOP_EXPONENT
        self.est_s = self.cap_loop_count * 2 / self.frequency
        # Bare Pi Pico ratio is 22.9:1, Pi Pico 2 W with 6cm wire 26.5
        self.est_hi = round(self.cap_loop_count) // 24
        # 3% of 24000 count is 800
        self.press_threshold = round(0.03 * self.est_hi) if press_threshold is None else press_threshold
        self.press_range = press_range

        self.level = 0
        self.last_value = 0
        self.level_lo = _U32MAX
        self.level_hi = 0

        self.warmup_level_lo = _U32MAX
        self.warmup_level_hi = 0

        self.sm_num = sm_num
        if self.sm_num is None:
            self.sm_num = self.next_sm
            self.next_sm += 1

        machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.state_machine = rp2.StateMachine(self.sm_num,
                                              capsense,
                                              freq=self.frequency,
                                              set_base=machine.Pin(pin),
                                              jmp_pin=machine.Pin(pin))
        self.state_machine.active(1)
        if calibrate_now:
            while self.warmup > 0:
                self.update(True)


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.state_machine.active(0)

    def active(self, active):
        self.state_machine.active(active)

    def update(self, wait=False):
        fifo_cnt = self.state_machine.rx_fifo()
        if fifo_cnt > 0 or wait:
            # Discard any stale buffered values and
            # read a new one if FIFO was full
            for _ in range(fifo_cnt):
                raw_value = _U32MAX - self.state_machine.get()
            if fifo_cnt == 0 or fifo_cnt == self.FIFO_LEN:
                raw_value = _U32MAX - self.state_machine.get()

            press_range = self.press_range
            if self.warmup > 0:
                self.warmup -= 1
                self.warmup_level_lo = min(raw_value, self.warmup_level_lo)
                self.warmup_level_hi = max(raw_value, self.warmup_level_hi)
                if self.warmup == 0:
                    self.noise_threshold = max(self.noise_threshold,
                                               self.NOISE_MULTIPLIER * (self.warmup_level_hi - self.warmup_level_lo))
                    self.level_hi = self.warmup_level_hi
                    if press_range is None:
                        self.level_lo = min(self.warmup_level_lo, self.warmup_level_hi - self.press_threshold)
                    else:
                        self.level_lo = self.warmup_level_hi - press_range
            else:
                decrease = self.level_hi - raw_value
                level_range = self.level_hi - self.level_lo
                if decrease > self.press_threshold:
                    # If range tracking is enabled then slowly follow any outliers
                    if press_range is None and raw_value < self.level_hi - level_range * 0.80:
                        self.level_lo = (7 * self.level_lo + raw_value) / 8.0
                else:
                    # Very slowly follow any drift in untouched
                    # or lightly touched values hoping the latter is rare
                    self.level_hi = (511 * self.level_hi + raw_value) / 512.0
                    if press_range is not None:
                        self.level_lo = self.level_hi - press_range

                self.level = min(1.0,
                                 max(0.0,
                                     decrease / level_range)) if decrease > self.noise_threshold else 0.0

            self.last_value = raw_value

    def is_pressed(self):
        self.update()
        return self.last_value < self.level_hi - self.press_threshold

    def __call__(self):
        """This is intended for use with the asyncio primitive Pushbutton."""
        self.update(True)
        return self.last_value < self.level_hi - self.press_threshold
