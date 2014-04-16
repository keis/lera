from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from collections import namedtuple
import logging
import json
import re


logger = logging.getLogger('riak')


class Conflict(Exception):
    def __init__(self, vclock, siblings):
        self.vclock = vclock
        self.siblings = siblings


class Object(dict):
    @property
    def key(self):
        return self.location.rsplit('/', 1)[-1]

    @classmethod
    def from_multipart_response(cls, response):
        # A very naive parser that ignores headers and mostly
        # rely on luck to parse any response

        nl = '\r\n'

        vclock = response.headers['X-Riak-VClock']
        siblings = []
        ctype = response.headers['content-type']
        boundary = re.search('boundary=([^ ]*)', ctype).group(1)
        body = response.body.decode('utf-8')

        for part in body.split('--' + boundary):
            part = part.lstrip(nl)

            if (nl * 2) not in part:
                continue

            headers, body = part.split(nl * 2)
            data = json.loads(body.rstrip(nl))
            obj = cls(data)
            obj.vclock = vclock

            siblings.append(obj)

        return siblings

    @classmethod
    def from_response(cls, response):
        if response.body:
            data = json.loads(response.body.decode('utf-8'))
        else:
            data = {}

        obj = cls(data)
        obj.vclock = response.headers.get('X-Riak-VClock', None)

        if 'location' in response.headers:
            obj.location = response.headers['location']

        if 'link' in response.headers:
            obj.links = list(parse_links(response.headers['link']))

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


link = namedtuple('link', ('bucket', 'key', 'tag'))

def format_links(links):
    frmt = '</buckets/%s/keys/%s>; riaktag="%s"'
    return ', '.join([frmt % l for l in links])


def parse_links(links):
    for l in links.split(', '):
        data = re.match('</buckets/([^/]*)/keys/([^>]*)>; riaktag="([^"]*)"', l)
        if data is not None:
            yield link(data.group(1), data.group(2), data.group(3))


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
    def save(self, bucket, key, value, links=None, vclock=None):
        headers = {
            'Content-Type': 'application/json'
        }

        if vclock is not None:
            headers['X-Riak-VClock'] = vclock

        if links:
            headers['Link'] = format_links(links)

        request = HTTPRequest(
            self.server + '/buckets/%s/keys/%s' % (bucket, key or ''),
            method='POST' if key is None else 'PUT',
            headers=headers,
            body=json.dumps(value))
        response = yield self.http.fetch(request)
        return Object.from_response(response)

    @coroutine
    def get(self, bucket, key):
        url = self.server + '/buckets/%s/keys/%s' % (bucket, key)
        request = HTTPRequest(url,
                              headers={'accept': 'application/json,multipart/mixed'})
        try:
            response = yield self.http.fetch(request)
        except HTTPError as e:
            response = e.response

            if e.code == 300:
                vclock = response.headers['X-Riak-VClock']
                siblings = Object.from_multipart_response(response)
                raise Conflict(vclock, siblings)

            raise KeyError(key)

        return Object.from_response(response)
