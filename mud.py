from tornado import ioloop, web, websocket
from tornado.gen import coroutine, Task
import json
import time

class User(object):
    def __init__(self, name, quest):
        self.name = name
        self.quest = quest

    @coroutine
    def look(self, what=None):
        yield Task(lambda callback: callback(time.sleep(0.2)))
        return "You are in a pitch black room, you are here to %s" % self.quest

    @classmethod
    @coroutine
    def get(cls, name, quest):
        yield Task(lambda callback: callback(time.sleep(0.2)))
        return cls(name.lower(), quest.lower())


class WebSocket(websocket.WebSocketHandler):
    def open(self):
        self.user = None
        self.name = None
        self.quest = None
        self.start()

    def write_json(self, data):
        self.write_message(json.dumps(data))

    def start(self):
        self.write_json({
            'message': 'WHAT.. is your name?',
            'prompt': 'Enter your name'
        })

    @coroutine
    def handle_greeting(self, message):
        if self.name is None:
            self.name = message
            self.write_json({
                'message': 'And what is your quest?',
                'prompt': 'Enter your quest'
            })

        elif self.quest is None:
            self.quest = message
            self.user = yield User.get(self.name, self.quest)

            desc = yield self.user.look()
            self.write_json({
                'message': desc
            })
        else:
            print('extra message to handle_greeting', message)


    @coroutine
    def handle_command(self, message):
        # TODO: do something sane with message
        parts = message.split()

        if parts[0] == 'look':
            desc = yield self.user.look()

            self.write_json({
                'message': desc
            })

        else:
            self.write_json({
                'message': '.. what?'
            })

    @coroutine
    def on_message(self, message):
        print('on message', message)
        try:
            if not self.user:
                yield self.handle_greeting(message)

            else:
                yield self.handle_command(message)
        except Exception as e:
            print(e)


application = web.Application([
    ('/socket', WebSocket)
])

if __name__ == "__main__":
    application.listen(8888)
    ioloop.IOLoop.instance().start()
