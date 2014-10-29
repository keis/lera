import logging
from functools import partial
from .server import app
from asyncio import get_event_loop
from aiohttp.wsgi import WSGIServerHttpProtocol

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('asyncio').setLevel(logging.INFO)

loop = get_event_loop()
f = loop.create_server(
    partial(WSGIServerHttpProtocol, app, debug=True, keep_alive=75),
    '0.0.0.0', '8060')
srv = loop.run_until_complete(f)

print('serving on %s' % (srv.sockets[0].getsockname(),))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
