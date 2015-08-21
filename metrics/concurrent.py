# -*- coding: utf8 -*-
import time
from threading import Lock, RLock

from .singlethread import MonotonicCounterContext, EWMA


class MonotonicCounter(dict):
    def __init__(self, *args, **kwargs):
        self['counter'] = 0
        self._lock = Lock()
        super(MonotonicCounter, self).__init__(*args, **kwargs)

    def inc(self, value=1):
        with self._lock:
            self['counter'] = self.get('counter', 0) + value

    def context(self, value=1):
        return MonotonicCounterContext(self, value)

    def __enter__(self):
        self.inc()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def value(self):
        return {'counter': self['counter']}


class ExceptionCounter(dict):
    def __init__(self, *args, **kwargs):
        self['exceptions'] = 0
        self._lock = RLock()
        super(MonotonicCounter, self).__init__(*args, **kwargs)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            with self._lock:
                self['exceptions'] = self.get('exceptions', 0) + 1

    @property
    def value(self):
        return {'exceptions': self['exceptions']}


class Meter(dict):
    def __init__(self, interval, windows, *args, **kwargs):
        super(Meter, self).__init__(*args, **kwargs)

        self.start_timestamp = time.time()
        self.last_timestamp = self.start_timestamp
        self.interval = interval
        self.count = 0.0
        self._lock = RLock()

        self.windows = [
            EWMA(interval, seconds)
            for seconds in windows
        ]

    def mean(self):
        with self._lock:
            elapsed = time.time() - self.start_timestamp
            return self.count / elapsed

    def mark(self, value=1):
        with self._lock:
            self.update()

            self.count += value
            for average in self.windows:
                average.add(value)

    def update(self):
        with self._lock:
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
