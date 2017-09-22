'''
    A Hodgepodge server

    A 'hodge' connects to a 'podge' (source) which provides a registry of components
    which may be queried or interacted with via a network.

    A 'podge' can accept numerous incoming connections.  The 'podge' will then synch
    it's local component registry with connecting apps.
'''
__all__ = ["IPodge", "Podge", "background_server"]

# from zope.component.interfaces import IRegistrationEvent
#
# from zope.component.interfaces import IAdapterRegistration
# from zope.component.interfaces import IHandlerRegistration
# from zope.component.interfaces import ISubscriptionAdapterRegistration
# from zope.component.interfaces import IUtilityRegistration


import zmq, dill
import logging, sys
from hodgepodge.common import Hodgepodge, IHodgepodge
from zope import interface, component

log = logging.getLogger('podge')
log.addHandler(logging.StreamHandler())
log.level = logging.DEBUG


class IPodge(IHodgepodge):
    ''' A client- side transparent registry '''

    def __init__(name, serve="tcp://*:3030"):
        ''' A Podge registry has a name and may listen for connections '''

    def run(poll = None, can_stop = None, setup = None):
        ''' Run the server.  If poll is not None, we call poll(self)
            with each iteration.
        '''

    def stop():
        ''' Stops the Podge and closes socket connections '''


class Podge(Hodgepodge):
    ''' A Podge server synchronises it's component registry with all
        incoming connections from Hodge clients.
    '''

    interface.implements(IPodge)
    _can_terminate = False

    def __init__(self, name, serve="tcp://*:3030"):
        ''' A registry has a name '''
        super(Podge, self).__init__(name)
        self.serve(serve)

    def _process_req(self, who, cmd, payload):
        """ Protocol:
            request = <sync|call|adapt>:<payload>
            response = <err|sync|data>:<payload>

            For sync, the payload is a dump of the registry
            For call, the payload contains marshaled interface, method and arguments
            For adapt, the payload contains marshaled adapter arguments
            For err, the payload is a string: "<errno>:description"
            For data, the payload is a dumped data object
            For stop, the payload is text: 'stopped' or 'denied'.
        """
        if cmd == 'sync':
            log.debug("'%s': read sync:" % self.__name__)
            sm = self.getSiteManager()
            synch = dict(adapters=sm.adapters._adapters, utilities=sm.utilities._adapters)
            result = dill.dumps(synch)
            self.send('sync', result, how=zmq.REP)
            log.debug("'%s': sent repo" % self.__name__)
        elif cmd == 'adapt':
            [Iface, aname, args, kwargs] = dill.loads(payload)
            log.debug("'%s': read adapt: %s(%s)[name=%s]" % (self.__name__, Iface, args, aname))
            sm = self.getSiteManager()
            try:
                if len(args) > 1:
                    ob = sm.queryMultiAdapter(args, Iface, name=aname)
                elif len(args) > 0:
                    args = args[0]
                    ob = sm.queryAdapter(args, Iface, name=aname)
                payload = dill.dumps(ob)
                self.send('adapt', payload, how=zmq.REP)
                log.debug("'%s': sent adapted item %s(%s)[name=%s]" % (self.__name__, Iface, args, aname))
            except Exception, e:
                self.send('err', ': Adapter call failed %s[%s] not found' % (Iface, aname), how=zmq.REP)
        elif cmd == 'call':
            [Iface, utname, meth, args, kwargs] = dill.loads(payload)
            log.debug("'%s': read call: [%s]" % (self.__name__, args))
            sm = self.getSiteManager()
            ut = sm.queryUtility(Iface, utname, None)
            if ut is None:
                self.send('err', ': Utility %s[%s] not found' % (Iface, utname), how=zmq.REP)
            else:
                m = getattr(ut, meth, None)
                if m is None:
                    self.send('err', ': %s[%s].%s: Method not found' % (Iface, utname, meth), how=zmq.REP)
                else:
                    try:
                        ret = m(*args, **kwargs)
                        payload = dill.dumps([ret, ut])
                        log.debug("'%s': returning from call" % (self.__name__))
                        self.send('call', payload, how=zmq.REP)
                    except Exception, e:
                        log.debug("'%s': error in call: %s" % (self.__name__, str(e)))
                        self.send('err', ': %s[%s].%s: Error in call %s' % (Iface, utname, meth, str(e)), how=zmq.REP)
        elif cmd == 'stop':
            if self._can_terminate:
                log.info("'%s': received stop signal" % self.__name__)
                self.send('stop', 'stopped', how=zmq.REP)
                self.active(False)
            else:
                self.send('err', ': Cannot stop this server', how=zmq.REP)
        else:
            log.error("'%s': Unknown command" % self.__name__)
            self.send('err', '1:Unknown command', how=zmq.REP)

    def run(self, poll = None, can_stop = None, setup = None):
        ''' Run the server.  If poll is not None, we call poll(self)
            with each iteration.
        '''
        if can_stop is not None:  # is remote allowed to terminate?
            self._can_terminate = can_stop
        if setup is not None:
            setup(self)
        self.bind(zmq.REP)
        self.active(True)
        poller = self.getPoller()
        while self.active():
            for socket in self.poll_socket(poller):
                who, cmd, data = self.recv(socket)
                self._process_req(who, cmd, data)
            if poll is not None:
                poll(self)

    def stop(self):
        log.debug("'%s': calling close()" % self.__name__)
        self.close()


def background_server(name, serve="tcp://*:3030", entry_point='run',  *args, **kwargs):
    '''  Runs a podge in the background
    '''
    def podge_server():
        p = Podge(name, serve)
        from time import sleep
        ep = getattr(p, entry_point, None)
        if not ep: raise(ValueError(u'Unknown entry point'))
        ep(*args, **kwargs)

    from multiprocessing import Process
    proc = Process(target=podge_server, args=tuple())
    proc.start()
    log.info("'%s': server started" % name)
    return proc


if __name__ == '__main__':
    """
        :doctest:

    Set up imports and capture logging for the doctest

        >>> from hodgepodge.hodge import Hodge
        >>> from hodgepodge.podge import Podge
        >>> from hodgepodge.utils import setCapturableLogging
        >>> from zope import component, interface
        >>> from time import sleep
        >>> import logging, sys
        >>> plog = logging.getLogger('podge')
        >>> setCapturableLogging(plog)
        >>> hlog = logging.getLogger('hodge')
        >>> setCapturableLogging(hlog)

    Test if we can run and stop the server in the foreground

        >>> def poll(ob):
        ...    if ob.active() and not ob.stopping():
        ...       print ("stopping")
        ...       ob.active(False)
        >>> p = Podge('joe')
        >>> p.run(poll=poll)
        stopping

    A "podge" server is meant to be run as a stand alone process.  It registers
    a set of utilities or adapters, and advertises these to connecting client
    hodges.

    A "hodge" is a site which contains a set of adapters or utilities
    which are defined by podges to which it connects.  It does not actually
    implement these adapters/utilities, but instead queries the appropriate
    podges whenever its adapters/utilities are accessed.

    This time we will create and register a global utility with the podge, and
    use the hodge interface to call methods in it remotely.

    >>> from hodgepodge.podge import background_server
    >>> from hodgepodge.interfaces import ITestIf, ITestIf2, ITestIf3
    >>> from hodgepodge.tests import TestUtility, TestAdapter, TestMultiAdapter

    A process is a 'sealed unit'.  One cannot change stuff like registry's from the
    outside. To allow for initialization, the entry point routine will call a setup
    function if we define one.

    We will use this to register a utility and some adapters with the podge site manager.

        >>> def setup(podge):
        ...    sm = podge.getSiteManager()
        ...    sm.registerUtility(TestUtility(), ITestIf, u'test')
        ...    sm.registerAdapter(TestAdapter, (ITestIf,), ITestIf2, name=u'a')
        ...    sm.registerAdapter(TestMultiAdapter, (ITestIf, ITestIf2),
        ...                       ITestIf3, name=u'b')

    Instances of the above utility and adapters will reside in the local podge
    component registry.  When a hodge connects, the podge synchronises the hodge
    component registry with it's own.

    The version of a utility in a hodge replaces all methods with shims, so that
    a call to a method results in the podge actually doing the work.  This provides
    the equivalent of a network shared component- ideal for global configuration,
    global data access, global data processing etc.

    An adapter stored in the hodge calls the podge to adapt any objects and return
    a new object, so the hodge adapter is again just a shim.  This can be used for
    implementing adaptive data (object) retrieval interfaces.

    First start up a podge server:

        >>> pid = background_server('joe', can_stop=True, setup=setup)
        'joe': server started

    Lets start up a hodge called 'bob'.  Bob should be able to see the
    utility advertised from the podge.

        >>> h = Hodge('bob')
        >>> h.start()
        'bob': sending sync
        'bob': got initial repo from joe

    Make sure we have selected the hodge registry, and locate the
    published utility. The hodge version of an object contains only
    shims to the real utility object stored back at the podge.

    This allows remote use of centralised utilities (or the equivalent
    of RPC calls).

    We can select a hodge site with setSite().

        >>> h.setSite()
        <hodgepodge.hodge.hodge.Hodge object at ...>

    A site has a site manager that we can use to register or query components.

        >>> sm = h.getSiteManager()
        >>> sm
        <LocalSiteManager ++etc++site>

        >>> sm.queryUtility(ITestIf, name='test')
        <...TestUtility object at ...>

    Hooks installed by the hodge should also allow zope.component.queryUtility() to work

        >>> ob = component.queryUtility(ITestIf, name='test')
        >>> ob
        <...TestUtility object at ...>

    Lets call some global utility methods, and inspect object attributes.  The call happens
    inside the podge process, even though we are calling methods in a utility located
    in the hodge registry.

        >>> ob.a(1)
        'bob': calling utility <InterfaceClass hodgepodge.interfaces.ITestIf>[test].a((1,); {})
        'bob': received a response from joe
        'arg B was: 1'

    Non-method attributes values are also available
        >>> ob.f1
        123

    Calling some methods can update attributes
        >>> ob.b(4)
        'bob': calling utility <InterfaceClass hodgepodge.interfaces.ITestIf>[test].b((4,); {})
        'bob': received a response from joe
        127

    Updated attributes are synchronized back from the podge to the hodge.
        >>> ob.f1
        127

    Lets adapt our object and return an instance of an ITestIf2:
        >>> ob2 = component.queryAdapter(ob, ITestIf2, name=u'a')
        'bob': calling adapter <InterfaceClass hodgepodge.interfaces.ITestIf2>[a](...)
        'bob': received a response from joe
        >>> ob2
        <hodgepodge.tests.test_doctests.TestObject object at ...>

    We now have an ob2, and we can call its methods:
        >>> ob2.r(45)
        100

    ... and reference it's attributes:
        >>> ob2.f1
        127
        >>> ob2.g1
        55

    Our result, ob2 is just a regular object, and all method calls are local.
    We can use queryMultiAdapter() to pass more than one parameter to an adapter:

        >>> ob3 = component.queryMultiAdapter((ob, ob2), ITestIf3, name=u'b')
        'bob': calling adapter <InterfaceClass hodgepodge.interfaces.ITestIf3>[b](...)
        'bob': received a response from joe

        >>> ob3
        <hodgepodge.tests.test_doctests.TestMultiAdapter object at ...>

        >>> print ("q1=%s; q2=%s; s()=%s; t()=%s" % (ob3.q1, ob3.q2, ob3.s(), ob3.t()))
        q1=127; q2=55; s()=2; t()=6985

    Our hodge can stop the server because we said it could (with the 'can_stop' argument)
        >>> h.stop_server()
        ('joe', 'stop', 'stopped')
        >>> pid.join()

    """

    from hodgepodge.hodge import Hodge
    from hodgepodge.tests import TestUtility, TestAdapter, TestMultiAdapter
    from hodgepodge.interfaces import ITestIf, ITestIf2, ITestIf3

    def setup(podge):
        sm = podge.getSiteManager()
        sm.registerUtility(TestUtility(), ITestIf, u'test')
        sm.registerAdapter(TestAdapter, (ITestIf,), ITestIf2, name=u'a')
        sm.registerAdapter(TestMultiAdapter, (ITestIf, ITestIf2),
                           ITestIf3, name=u'b')
#         ob = TestUtility()
#         a = sm.queryAdapter(ob, ITestIf2, name=u'a')
#         a

    pid = background_server('joe', can_stop=True, setup = setup)
    h = Hodge('bob')
    h.start()
    h.setSite()
    ob = component.queryUtility(ITestIf, name='test')
    print "a(1)=<%s>"  % ob.a(1)
    print "a('jkl')=<%s>"  % ob.a('jkl')
    print "before v = ob.b(2): f1=%s" % ob.f1
    v = ob.b(2)
    print "after %s = ob.b(2): f1=%s" % (v, ob.f1)
    ob2 = component.queryAdapter(ob, ITestIf2, name=u'a')
    print "%s" % ob2
    ob3 = component.queryMultiAdapter((ob, ob2), ITestIf3, name=u'b')
    print "%s" % ob3

    print h.stop_server()
    pid.join()
    print("Done")

