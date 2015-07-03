# -*- coding: utf8 -*-
from metrics import MonotonicCounter, Gauge, ExceptionCounter, Meter


def _factory(type_, klass):
    def method(self, name, **kwargs):
        # instantiate a new metric with manager's tags
        metric = klass(self)
        metric.update(kwargs)
        metric['name'] = name

        # allow the user to overwrite an older metric
        self.metrics[name] = metric

        return metric

    method.func_name = type_
    return method


class Manager(dict):
    counter = _factory('counter', MonotonicCounter)
    gauge = _factory('gauge', Gauge)
    exception = _factory('exception', ExceptionCounter)
    meter = _factory('meter', Meter)

    def __init__(self, *args, **kwargs):
        super(Manager, self).__init__(*args, **kwargs)
        self.metrics = {}


manager = Manager()
