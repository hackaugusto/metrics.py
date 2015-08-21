# -*- coding: utf8 -*-
import ctypes
from ctypes.util import find_library

try:
    from time import process_time
except ImportError:
    import resource

    # https://www.python.org/dev/peps/pep-0418/#time-process-time
    def process_time():
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage[0] + usage[1]

cint = ctypes.c_int
clong = ctypes.c_long
cchar = ctypes.c_char
cvoid = ctypes.c_void_p


def clib(function, arguments_types, return_type):
    clib = ctypes.CDLL(find_library('c'))

    func = getattr(clib, function)
    func.argtypes = arguments_types
    func.restype = return_type

    return func


class timeval(ctypes.Structure):
    # <bits/types.h>
    # typedef long int __time_t;
    # typedef long int __suseconds_t;
    #
    # <bits/time.h>
    # struct timeval
    # {
    #   __time_t tv_sec;
    #   __suseconds_t tv_usec;
    # };
    _fields_ = [
        ('tv_sec', clong),
        ('tv_usec', clong),
    ]


# int gettimeofday(struct timeval*, void *);
# If tzp is not a null pointer, the behavior is unspecified.
_gettimeofday = clib('gettimeofday', [ctypes.POINTER(timeval), cvoid], cint)
TZP_NULL = cvoid()


# python's time.time is the best option:
# clib.gettimeofday: 1000000 loops, best of 3: 1.61 µs per loop
# clib.time:         1000000 loops, best of 3: 341 ns per loop
# time.time:         10000000 loops, best of 3: 99.4 ns per loop
def gettimeofday():
    out = timeval()
    _gettimeofday(ctypes.byref(out), TZP_NULL)
    return out


class WallTimer(object):
    '''Fast timer on linux systems, this timer is sucetible to time drift due
    to updates to the clock (by a admin or NTPd)
    '''
    def __init__(self):
        self.elapsed = None

    def __enter__(self):
        self._start = time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time() - self._start


class ProcessTimer(object):
    '''Slower version that counts the time spent running and at the kernel
    (discarding sleeping).

    Care must be taken if you're using this timer with a event driven
    framework, so that you do not count the time from another green thread.
    '''
    def __init__(self):
        self.elapsed = None

    def __enter__(self):
        self._start = process_time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = process_time() - self._start
