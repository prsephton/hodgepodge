from zope import interface

class ITestIf(interface.Interface):
    f1 = interface.Attribute(u'F1 attribute')

    def a(self, b):
        ''' A method '''

    def b(self, c):
        ''' Another method '''

class ITestIf2(interface.Interface):
    g1 = interface.Attribute(u'G1 attribute')

    def r(self, v):
        ''' A method that takes a v '''

class ITestIf3(interface.Interface):
    q1 = interface.Attribute(u'Q1 attribute')
    q2 = interface.Attribute(u'Q2 attribute')

    def s(self):
        ''' A method '''

    def t(self):
        ''' Another method '''
