# -*- coding: utf-8 -*-

import os.path


class Led(object):
    led_sys_path = '/sys/devices/platform/leds/leds'

    def __init__(self, led_folder, function=None):
        self.full_path = os.path.join(Led.led_sys_path, led_folder)
        self.trigger = os.path.join(self.full_path, 'trigger')
        self.delay_on = os.path.join(self.full_path, 'delay_on')
        self.delay_off = os.path.join(self.full_path, 'delay_off')
        self.brightness = os.path.join(self.full_path, 'brightness')

        self._function = function

        with open(self.trigger, mode='r') as f:
            self._mode = f.readline()

    def set_trigger(self, new_trigger):
        with open(self.trigger, mode='w') as f:
            f.write(str(new_trigger))
            self._mode = new_trigger

    def set_brightness(self, new_brightness):
        with open(self.brightness, mode='w') as f:
            f.write(str(new_brightness))

    def set_blink(self, new_delay):
        for delay_file in (self.delay_off, self.delay_on):
            with open(delay_file, mode='w') as f:
                f.write(str(new_delay))

    @property
    def function(self):
        return self._function

    def on(self):
        self.set_trigger('default-on')

    def off(self):
        self.set_trigger('default-off')

    def toggle(self):
        if self.mode == 'default-on':
            self.off()
        else:
            self.on()

if __name__ == '__main__':
    import time

    l2 = Led('beaglebone:green:usr2')

    l2.set_trigger('default-on')

    time.sleep(5)

    l2.set_trigger('delay-on')
    l2.set_blink(50)

    time.sleep(5)

    l2.set_trigger('heartbeat')
