# -*- coding: utf8 -*-
import time
from threading import Lock, RLock

from singlethread import CounterContext, EWMA


class Counter(dict):
    def __init__(self, *args, **kwargs):
        super(Counter, self).__init__(*args, **kwargs)
        self._lock = Lock()

    def inc(self, value=1):
        with self._lock:
            self['counter'] = self.get('counter', 0) + value

    def dec(self, value=1):
        with self._lock:
            self['counter'] = self.get('counter', 0) - value

    def context(self, value=1):
        return CounterContext(self, value)

    def __enter__(self):
        self.inc()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dec()


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
