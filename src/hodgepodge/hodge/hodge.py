'''
    Client side library for transparently passing Python objects through
    a network, subscribing to server side events, or calling virtual
    utilities provided by servers.

    A 'hodge' connects to one or more 'podge' (sources) which provides a
    registry of components which may be queried or interacted with via a network.

    A 'podge' can accept numerous incoming connections.  The 'podge' will then synch
    it's local component registry with connecting apps.

'''
#__all__ = ["IHodge", "Hodge"]

# from zope.component.interfaces import IRegistrationEvent
#
# from zope.component.interfaces import IAdapterRegistration
# from zope.component.interfaces import IHandlerRegistration
# from zope.component.interfaces import ISubscriptionAdapterRegistration
# from zope.component.interfaces import IUtilityRegistration


import zmq, dill, types
import logging
from copy import copy
from hodgepodge.common import Hodgepodge, IHodgepodge
from zope import interface, component

log = logging.getLogger('hodge')
log.addHandler(logging.StreamHandler())
log.level = logging.DEBUG

class IHodge(IHodgepodge):
    ''' A client- side transparent registry '''

def proxymethod(hodgename, uname='', atype=None):
    def methwrapper(meth):
        def funcwrapper(*args, **kwargs):
            hodge = component.queryUtility(IHodge, name=hodgename)
            if atype=='utility':
                return hodge.call_util(meth, uname, *args, **kwargs)
            elif atype=='adapter':
                return hodge.call_adapter(meth, uname, *args, **kwargs)
            elif atype=='method':
                return hodge.call_method(meth, uname, *args, **kwargs)
        return funcwrapper
    return methwrapper


class Hodge(Hodgepodge):
    '''  Our client side [local] registry lives in an instance of this
    '''
    interface.implements(IHodge)

    def __init__(self, name, source='tcp://localhost:3030'):
        ''' A registry has a name '''
        super(Hodge, self).__init__(name)
        sm = self.getSiteManager()
        sm.registerUtility(self, IHodge, name)  # register local utility
        self.connect(source, zmq.REQ)


    def reg_adapter(self, sm, adapts, spec):
        for i, v in spec.items():
            if type(i) is interface.interface.InterfaceClass:
                adapts.append(i)
                self.reg_adapter(sm, adapts, v)
            else:
                provides = adapts.pop()
                v = copy(v)
                setattr(v, '__savenew__', getattr(v, '__new__', None))
                setattr(v, '__new__', self.proxy(v, '__new__', uname=i, atype='adapter'))
                sm.registerAdapter(v, tuple(adapts), provides, name=i)
#                 from hodgepodge.tests import TestUtility
#                 from hodgepodge.interfaces import ITestIf2
#                 q = sm.queryAdapter(TestUtility(), ITestIf2, name=u'a')
#                 q

    def start(self):
        log.debug("'%s': sending sync" % self.__name__)
        self.send('sync', '', how=zmq.REQ)
        who, cmd, payload = self.recv()
        log.debug("'%s': got initial repo from %s" % (self.__name__, who))
        if cmd=='err':
            raise ValueError(payload)
        elif cmd=='sync':
            sm = self.getSiteManager()
            registry = dill.loads(payload)
            for a in registry['adapters']:
                self.reg_adapter(sm, [], a)
            for u in registry['utilities']:
                for i, v in u.items():
                    for name, ob in v.items():
                        old = sm.queryUtility(i, name=name)
                        sources = None
                        if old:
                            sources = getattr(old, '_p_sources', set())
                            setattr(ob, '_p_sources', sources)
                            sm.unregisterUtility(old)

                        self.proxy_object_methods(who, ob, i, name, 'utility')
                        sm.registerUtility(ob, i, name=name)


    def proxy_object_methods(self, who, ob, iface, uname, atype='utility'):
        sources = getattr(ob, '_p_sources', set())
        if who not in sources: sources.add(who)  # sources of this utility
        setattr(ob, '_p_sources', sources)

        for method in iface.names():
            if type(iface[method]) is interface.interface.Method:
                setattr(ob, method, self.proxy(iface, method, uname=uname))

    def proxy(self, ob, method, uname='', atype='utility'):
        return types.MethodType(proxymethod(self.__name__, uname, atype)(method), ob)

    def call_adapter(self, meth, name, adapter, *args, **kwargs):
        IFace = list(adapter.__implemented__)
        if len(IFace):
            IFace = IFace[0]
            log.debug("'%s': calling adapter %s[%s](%s; %s)" % (self.__name__, IFace, name, args, kwargs))
            payload = dill.dumps([IFace, name, args[1:], kwargs])
            self.send('adapt', payload, how=zmq.REQ)
            who, cmd, payload = self.recv()
            log.debug("'%s': received a response from %s" % (self.__name__, who))
            if cmd == 'adapt':
                oldnew = getattr(adapter, '__new__', None)
                savenew = getattr(adapter, '__savenew__', None)
                if savenew is None:
                    delattr(adapter, '__new__')
                else:
                    setattr(adapter, '__new__', savenew)
                ob = dill.loads(payload)
                if oldnew is not None:
                    setattr(adapter, '__new__', oldnew)
                return ob  # an ordinary client-side object
            elif cmd == 'err':
                log.debug("'%s': adapter call failed: %s" % (self.__name__, payload))
                raise ValueError(payload)

    def call_method(self, meth, name, IFace, *args, **kwargs):
        return self.call_util(meth, name, IFace, *args, **kwargs)

    def call_util(self, meth, name, IFace, *args, **kwargs):
        log.debug("'%s': calling utility %s[%s].%s(%s; %s)" % (self.__name__, IFace, name, meth, args, kwargs))

        payload = dill.dumps([IFace, name, meth, args, kwargs])
        self.send('call', payload, how=zmq.REQ)
        who, cmd, payload = self.recv()
        log.debug("'%s': received a response from %s" % (self.__name__, who))
        if cmd=='err':
            log.debug("'%s': %s" % (self.__name__, payload))
            raise ValueError(payload)
        elif cmd=='call':
            retvalue, ob = dill.loads(payload)

            # update object in place.  Only look at attributes defined in the interface
            sm = self.getSiteManager()
            ut = sm.getUtility(IFace, name=name)
            for attr in IFace.names():
                if type(IFace[attr]) is interface.interface.Method:
                    setattr(ut, attr, self.proxy(IFace, attr, uname=name, atype='utility'))
                else:
                    setattr(ut, attr, getattr(ob, attr, None))
            return retvalue

    def stop_server(self):
        self.send('stop', '', how=zmq.REQ)
        return self.recv()


if __name__ == '__main__':
    """
        :doctest:

        >>> from zope import component, interface
        >>> import hodgepodge.hodge as hodge
        >>> h = hodge.Hodge('bob')
        >>> component.queryUtility(hodge.IHodge, name='bob')
        <hodgepodge.hodge.hodge.Hodge object at ...>

    """

