from tornado import ioloop, web, websocket
import json

class User(object):
    def __init__(self, name, quest):
        self.name = name
        self.quest = quest

    @classmethod
    def get(cls, name, quest):
        return cls(name.lower(), quest.lower())


class WebSocket(websocket.WebSocketHandler):
    def open(self):
        self.proc = self.greeting()
        next(self.proc)

    def write_json(self, data):
        self.write_message(json.dumps(data))

    def greeting(self):
        name, quest = None, None
        self.write_json({
            'message': 'WHAT.. is your name?',
            'prompt': 'Enter your name'
        })

        while not name:
            name = yield

        self.write_json({
            'message': 'And what is your quest?',
            'prompt': 'Enter your quest'
        })

        while not quest:
            quest = yield

        self.user = User.get(name, quest)
        self.proc = self.commands()
        yield next(self.proc)

    def commands(self):
        while True:
            self.write_json({
                'message': 'hurr durr'
            })
            message = yield
            # do something with message

    def on_message(self, message):
        self.proc.send(message)


application = web.Application([
    ('/socket', WebSocket)
])

if __name__ == "__main__":
    application.listen(8888)
    ioloop.IOLoop.instance().start()
