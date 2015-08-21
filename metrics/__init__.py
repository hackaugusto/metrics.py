# -*- coding: utf8 -*-
'''
The metrics extends the dict classe to store the metric data and extra tags.
'''

from .concurrent import ExceptionCounter, MonotonicCounter, Meter  # NOQA
from .singlethread import Gauge  # NOQA
