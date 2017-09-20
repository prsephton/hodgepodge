import unittest, doctest
import sys, logging
from zope import interface, component
from hodgepodge.interfaces import ITestIf, ITestIf2, ITestIf3


class TestUtility(object):
    interface.implements(ITestIf)

    f1 = 123

    def a(self, b):
        return "arg B was: %s" % b

    def b(self, c):
        self.f1 += c
        return self.f1


class TestObject(object):
    interface.implements(ITestIf2)

    g1 = 55
    def __init__(self, f1):
        self.f1 = f1

    def r(self, v):
        ''' A method in an object '''
        return v + self.g1


class TestAdapter(object):
    interface.implements(ITestIf2)
    component.adapts(ITestIf)

    def __new__(self, context):
        return TestObject(context.f1)


class TestMultiAdapter(object):
    interface.implements(ITestIf3)
    component.adapts(ITestIf, ITestIf2)

    def __init__(self, ob1, ob2):
        self.q1 = ob1.f1
        self.q2 = ob2.g1

    def s(self):
        return self.q1 / self.q2

    def t(self):
        return self.q1 * self.q2


class CapturableHandler(logging.StreamHandler):

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, value):
        pass

def setUp(test):
    logging.basicConfig(level=logging.DEBUG)
    if not logging.getLogger().handlers:
        logging.getLogger().addHandler(CapturableHandler())
        logging.getLogger().setLevel(logging.DEBUG)
#         hodge = logging.getLogger('hodge')
#         podge = logging.getLogger('podge')
#         hodge.addHandler(CapturableHandler())
#         podge.addHandler(CapturableHandler())
#         hodge.setLevel(logging.DEBUG)
#         podge.setLevel(logging.DEBUG)

def tearDown(test):
    pass

def test_suite():
    optionflags = doctest.ELLIPSIS+doctest.NORMALIZE_WHITESPACE
    return unittest.TestSuite([
#        doctest.DocTestSuite(optionflags=optionflags),
        doctest.DocFileSuite('../hodge/hodge.py', setUp=setUp,
                            tearDown=tearDown,
                            optionflags=optionflags),
        doctest.DocFileSuite('../podge/podge.py', setUp=setUp,
                            tearDown=tearDown,
                            optionflags=optionflags),
    ])

