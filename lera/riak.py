from asyncio import Future, coroutine
from collections import namedtuple
import aiohttp
import logging
import json
import re

logger = logging.getLogger(__name__)


class Conflict(Exception):
    def __init__(self, vclock, location, siblings):
        self.vclock = vclock
        self.location = location
        self.siblings = siblings


class Object(dict):
    vclock = None
    links = ()

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
            headers = dict(r.split(': ') for r in headers.split('\r\n'))
            data = json.loads(body.rstrip(nl))

            obj = cls(data)
            obj.vclock = vclock

            if 'Link' in headers:
                obj.links = list(parse_links(headers['Link']))

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
        self.server = server

    @coroutine
    def mapred(self, query):
        req = aiohttp.request('POST',
                              self.server + '/mapred',
                              headers={'Content-Type': 'application/json'},
                              data=json.dumps(query))

        res = yield from req
        res.body = yield from res.read()

        return json.loads(res.body.decode('utf-8'))

    @coroutine
    def save(self, bucket, key, value, links=None, vclock=None):
        headers = {
            'Content-Type': 'application/json'
        }

        if vclock is not None:
            headers['X-Riak-VClock'] = vclock

        if links:
            headers['Link'] = format_links(links)

        req = aiohttp.request('POST' if key is None else 'PUT',
                              self.server + '/buckets/%s/keys/%s' % (bucket, key or ''),
                              headers=headers,
                              data=json.dumps(value))

        res = yield from req
        try:
            res.body = yield from res.read()
        except aiohttp.IncompleteRead:  # no data from put
            res.body = None

        return Object.from_response(res)

    @coroutine
    def get(self, bucket, key):
        url = self.server + '/buckets/%s/keys/%s' % (bucket, key)
        req = aiohttp.request('GET', url,
                                headers={'accept': 'application/json,multipart/mixed'})

        res = yield from req
        res.body = yield from res.read()


        if res.status >= 300:
            if res.status == 300:
                vclock = res.headers['X-Riak-VClock']
                siblings = Object.from_multipart_response(res)

                raise Conflict(vclock, url, siblings)

            raise KeyError(key)

        obj = Object.from_response(res)
        if not hasattr(obj, 'location'):
            obj.location = url
        return obj
