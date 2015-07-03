# -*- coding: utf8 -*-
import time
from math import exp


class MonotonicCounter(dict):
    def inc(self, value=1):
        self['counter'] = self.get('counter', 0) + value

    def __enter__(self):
        self.inc()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def context(self, value=1):
        return MonotonicCounterContext(self, value)

    def value(self):
        return {'counter': self['counter']}


class MonotonicCounterContext(object):
    def __init__(self, counter, value):
        self.counter = counter
        self.value = value

    def __enter__(self):
        self.counter.inc(self.value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class ExceptionCounter(dict):
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self['exceptions'] = self.get('exceptions', 0) + 1

    def value(self):
        return {'exceptions': self['exceptions']}


class Gauge(dict):
    def inc(self, value=1):
        self['gauge'] = self.get('gauge', 0) + value

    def dec(self, value=1):
        self['gauge'] = self.get('gauge', 0) - value

    def set(self, value):
        self['gauge'] = value

    def value(self):
        return {'gauge': self['gauge']}


class Meter(dict):
    def __init__(self, interval, windows, *args, **kwargs):
        super(Meter, self).__init__(*args, **kwargs)

        self.start_timestamp = time.time()
        self.last_timestamp = self.start_timestamp
        self.interval = interval
        self.count = 0.0

        self.windows = [
            EWMA(interval, seconds)
            for seconds in windows
        ]

    def mean(self):
        elapsed = time.time() - self.start_timestamp
        return self.count / elapsed

    def mark(self, value=1):
        self.update()

        self.count += value
        for average in self.windows:
            average.add(value)

    def update(self):
        now = time.time()
        if now - self.last_timestamp > self.interval:
            for average in self.windows:
                average.update()
                self[str(average.window)] = average.rate

            self['mean'] = self.mean()
            self.last_timestamp = now

    def value(self):
        result = {
            str(average.window): self[str(average.window)]
            for average in self.windows
        }
        result.extend({'mean': self['mean']})
        return result


class EWMA(object):
    def __init__(self, interval, window):
        self._alpha = EWMA.alpha(interval, window)
        self.interval = interval
        self.window = window
        self.rate = None
        self.count = 0

    def add(self, value=1):
        self.count += value

    def update(self):
        instant_rate = self.count / self.interval

        if self.rate:
            self.rate += self._alpha * (instant_rate - self.rate)
        else:
            self.rate = instant_rate

    @staticmethod
    def alpha(interval, window):
        '''The interval and the window in seconds'''
        interval = float(interval)
        window = float(window)
        return 1.0 - exp(-interval / window)
