import logging, sys

class CapturableHandler(logging.StreamHandler):

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, value):
        pass


def setCapturableLogging(log):
    log.setLevel(logging.DEBUG)
    log.addHandler(CapturableHandler())

