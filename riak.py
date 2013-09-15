from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
import json


class Client(object):

    def __init__(self, server):
        self.http = AsyncHTTPClient()
        self.server = server

    @coroutine
    def save(self, bucket, key, value):
        request = HTTPRequest(
            self.server + '/buckets/%s/keys/%s' % (bucket, key),
            method='PUT',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(value))
        response = yield self.http.fetch(request)
        return

    @coroutine
    def get(self, bucket, key):
        request = HTTPRequest(
            self.server + '/buckets/%s/keys/%s' % (bucket, key))
        try:
            response = yield self.http.fetch(request)
        except HTTPError:
            raise KeyError(key)

        return json.loads(response.body.decode('utf-8'))
