# -*- coding: utf8 -*-
import copy
import time
from math import exp


class MonotonicCounter(dict):
    def __init__(self, *args, **kwargs):
        self['counter'] = 0
        super(MonotonicCounter, self).__init__(*args, **kwargs)

    def inc(self, value=1):
        self['counter'] = self.get('counter', 0) + value

    def __enter__(self):
        self.inc()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def context(self, value=1):
        return MonotonicCounterContext(self, value)

    @property
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
    def __init__(self, *args, **kwargs):
        self['exceptions'] = 0
        super(ExceptionCounter, self).__init__(*args, **kwargs)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self['exceptions'] = self.get('exceptions', 0) + 1

    @property
    def value(self):
        return {'exceptions': self['counter']}


class Gauge(dict):
    def __init__(self, *args, **kwargs):
        self['gauge'] = 0
        super(Gauge, self).__init__(*args, **kwargs)

    def inc(self, value=1):
        self['gauge'] = self.get('gauge', 0) + value

    def dec(self, value=1):
        self['gauge'] = self.get('gauge', 0) - value

    def set(self, value):
        self['gauge'] = value

    @property
    def value(self):
        return {'gauge': self['gauge']}


class SimpleHistogram(dict):
    '''A static histogram, you need to define the buckets a priori'''
    def __init__(self, buckets, *args, **kwargs):
        self.buckets = {
            float(bucket): 0
            for bucket in buckets
        }
        self.buckets.setdefault(float('inf'), 0)

        super(SimpleHistogram, self).__init__(*args, **kwargs)

    def mark(self, value):
        for bucket in self.buckets.keys():
            if value <= bucket:
                self.buckets[bucket] = self.buckets.get(bucket, 0) + 1

    @property
    def value(self):
        return copy.deepcopy(self.buckets)


class Meter(dict):
    def __init__(self, interval, windows, *args, **kwargs):
        self.start_timestamp = time.time()
        self.last_timestamp = self.start_timestamp
        self.interval = interval
        self.count = 0.0

        self.windows = [
            EWMA(interval, seconds)
            for seconds in windows
        ]

        super(Meter, self).__init__(*args, **kwargs)

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

    @property
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
