# -*- coding: utf8 -*-
from __future__ import absolute_import

import threading
from itertools import starmap

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SocketServer import ThreadingMixIn
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from socketserver import ThreadingMixIn


from ..manager import manager as global_manager


def infinity(value):
    # use Go's format for the infinity value
    if value == float('inf'):
        return '+Inf'

    if value == float('-inf'):
        return '-Inf'

    return value


def to_prometheus(metric):
    name = metric.pop('name')

    if len(metric.value) == 1:
        key = metric.value.keys()[0]
        value = infinity(metric.pop(key))

    tags = ''
    if len(metric):
        tags = starmap('{}="{}"'.format, sorted(metric.items()))
        tags = '{}{{{}}}'.format(name, ','.join(tags))

    # name{tag=value} value
    return '{}{} {}'.format(name, tags, value).encode('string-escape')


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class PrometheusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
        self.end_headers()

        response = []
        for metric in self.server.manager.metrics:
            metric = type(metric)(metric)
            response.append(to_prometheus(metric))

        response = '\n'.join(response) + '\n'
        print(response)
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
