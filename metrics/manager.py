# -*- coding: utf8 -*-
from contextlib import contextmanager

from . import MonotonicCounter, Gauge, ExceptionCounter, Meter


def tags_key(tags):
    return tuple(tags.items())


def _factory(type_, klass):
    def method(self, name, **kwargs):
        # instantiate a new metric with manager's tags
        metric = klass(self)
        metric.update(kwargs)
        metric['name'] = name

        # allow the user to overwrite an older metric
        metrics_tags = self.metrics_name.setdefault(name, {})
        metrics_tags[tags_key(kwargs)] = metric

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
        self.metrics_name = {}

    @contextmanager
    def with_tags(self, name, kind, tags):
        metrics_tags = self.metrics_name.setdefault(name, {})

        print(name, kind, tags)
        try:
            metric = metrics_tags[tags_key(tags)]
        except KeyError:
            metric = metrics_tags[tags_key(tags)] = getattr(self, kind)(name, **tags)

        print(self.metrics_name)
        print(id(manager))
        with metric:
            yield

    @property
    def metrics(self):
        print(id(manager))
        print(self.metrics_name)
        for metrics_tags in self.metrics_name.values():
            for metric in metrics_tags.values():
                yield metric


manager = Manager()
