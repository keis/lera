from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Request
#from asyncio import coroutine, Future, Task, sleep
from trollius import coroutine, Future, Task, sleep


class Response(Future):
    '''connect/express inspired response object'''

    def __init__(self, start_response):
        super(Response, self).__init__()
        self.start_response = start_response
        self.headers = {}

    def status(self, status):
        headers = list(self.headers.items())
        self.start_response(status, headers)
        return self

    def send(self, result):
        if isinstance(result, bytes):
            result = [result]

        self.set_result(result)
        return self


@coroutine
def index(req, res):
    res.headers['Content-Type'] = 'text/plain'
    res.status('200 OK').send(b'index')


@coroutine
def lazy(req, res):
    res.headers['Content-Type'] = 'text/plain'
    yield from sleep(1)
    res.status('200 Ok').send([b'lazy page'])


urls = Map([
    Rule('/', endpoint=index),
    Rule('/lazy', endpoint=lazy)
])


def dispatch_request(req, res):
    adapter = urls.bind_to_environ(req.environ)
    try:
        endpoint, values = adapter.match()
        return endpoint(req, res, **values)
    except HTTPException as e:
        return e


def app(environ, start_response):
    request = Request(environ)
    response = Response(start_response)
    Task(dispatch_request(request, response))
    return response


if __name__ == '__main__':
    from pulsar.apps.wsgi import WSGIServer
    WSGIServer(app, debug=True, reload=True).start()
