# -*- coding: utf8 -*-
from __future__ import absolute_import

import threading
import time
import socket
from itertools import starmap

try:
    import httplib
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SocketServer import ThreadingMixIn
except ImportError:
    from http import client as httplib
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from socketserver import ThreadingMixIn


from metrics.manager import manager as global_manager
from metrics import concurrent
from metrics import singlethread


try:
    SEPARATOR = '\n'

    def escape(value):
        return value.encode('string-escape')

    # this will fail if it is python3, because there is not string-escape codec
    escape('')
except LookupError:
    SEPARATOR = b'\n'

    def escape(value):
        return value.encode('unicode_escape')


def infinity(value):
    # use Go's format for the infinity value
    if value == float('inf'):
        return '+Inf'

    if value == float('-inf'):
        return '-Inf'

    return value


METRIC_TYPE = {
    concurrent.MonotonicCounter: 'counter',
    concurrent.ExceptionCounter: 'counter',
    concurrent.Meter: 'summary',

    singlethread.ExceptionCounter: 'counter',
    singlethread.MonotonicCounter: 'counter',
    singlethread.MonotonicCounterContext: 'counter',
    singlethread.Gauge: 'gauge',
    singlethread.SimpleHistogram: 'histogram',
    singlethread.Meter: 'summary',
}


def to_prometheus(metric):
    name = metric.pop('name')

    if len(metric.value) == 1:
        key = list(metric.value.keys())[0]
        value = infinity(metric.pop(key))

    tags = ''
    if len(metric):
        tags = starmap('{}="{}"'.format, sorted(metric.items()))
        tags = '{}{{{}}}'.format(name, ','.join(tags))

    comment_type = ''
    if type(metric) in METRIC_TYPE:
        type_ = METRIC_TYPE[type(metric)]
        comment_type = escape('# TYPE {} {}'.format(name, type_)) + SEPARATOR

    # name{tag=value} value
    return comment_type + escape('{}{} {}'.format(name, tags, value))


def serialize_metrics(metrics):
    response = []
    for metric in metrics:
        metric = type(metric)(metric)
        response.append(to_prometheus(metric))

    return SEPARATOR.join(response) + SEPARATOR


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class PrometheusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
        self.end_headers()

        response = serialize_metrics(self.server.manager.metrics)
        self.wfile.write(response.encode('utf8'))


class Prometheus(object):
    def __init__(self, manager=None):
        self.manager = manager or global_manager

    def background_serve(self, host, port):
        server = ThreadedHTTPServer((host, port), PrometheusHandler)
        server.manager = self.manager

        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()


class PrometheusPushThread(threading.Thread):
    def __init__(self, hosturl, jobname, push_interval=60, manager=None):
        super(PrometheusPushThread, self).__init__()

        self.manager = manager or global_manager
        self.jobname = jobname
        self.hosturl = hosturl
        self.push_interval = float(push_interval)
        self.daemon = True
        self.url = '/metrics/jobs/{}'.format(jobname)

    def run(self):
        conn = httplib.HTTPConnection(self.hosturl)

        while True:
            time.sleep(self.push_interval)
            data = serialize_metrics(self.manager.metrics)

            try:
                conn.request('PUT', self.url, data)
                response = conn.getresponse()
                response.read()
            except socket.error:
                # assume an intermittent
                conn.close()
                conn = httplib.HTTPConnection(self.hosturl)
            except httplib.InvalidURL:
                # cannot recover from a wrong url
                break

    background_serve = run
