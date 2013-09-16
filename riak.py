from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
import json


class Object(dict):
    @property
    def key(self):
        return self.location.rsplit('/', 1)[-1]

    @classmethod
    def from_response(cls, response):
        if response.body:
            data = json.loads(response.body.decode('utf-8'))
        else:
            data = {}

        obj = cls(data)
        if 'location' in response.headers:
            obj.location = response.headers['location']

        return obj

class MapReduce(dict):
    def __init__(self):
        self['inputs'] = []
        self['query'] = []

    def add(self, *inputs):
        self['inputs'].extend(inputs)

    def link(self, q):
        self['query'].append({'link': q})

    def map(self, q):
        self['query'].append({'map': q})

    def reduce(self, q):
        self['query'].append({'reduce': q})


def format_link(l):
    return '</buckets/%s/keys/%s>; riaktag="%s"' % l


class Client(object):
    
    def __init__(self, server):
        self.http = AsyncHTTPClient()
        self.server = server

    @coroutine
    def mapred(self, query):
        request = HTTPRequest(
            self.server + '/mapred',
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(query))

        response = yield self.http.fetch(request)
        return json.loads(response.body.decode('utf-8'))

    @coroutine
    def save(self, bucket, key, value, links=None):
        headers = {
            'Content-Type': 'application/json'
        }

        if links:
            headers['Link'] = ', '.join([format_link(l) for l in links])

        request = HTTPRequest(
            self.server + '/buckets/%s/keys/%s' % (bucket, key or ''),
            method='POST' if key is None else 'PUT',
            headers=headers,
            body=json.dumps(value))
        response = yield self.http.fetch(request)
        return Object.from_response(response)

    @coroutine
    def get(self, bucket, key):
        request = HTTPRequest(
            self.server + '/buckets/%s/keys/%s' % (bucket, key))
        try:
            response = yield self.http.fetch(request)
        except HTTPError:
            raise KeyError(key)

        return Object.from_response(response)
