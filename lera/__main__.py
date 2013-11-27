from tornado import ioloop
import logging

logging.basicConfig(level=logging.DEBUG)

from .server import application

application.listen(8888)
ioloop.IOLoop.instance().start()
