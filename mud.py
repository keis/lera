from tornado.gen import coroutine, Task
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
