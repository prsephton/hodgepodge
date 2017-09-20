Hodgepodge is a distributed component system based upon zope.interface and ZeroMQ.

Hodge provides a client side library for accessing remote utilities and data, while Podge provides a server based library for publishing interfaces which can be accessed via Hodge.

Some use cases:
	1. Python RPC
	2. Scaling Python apps through distributed processing
	3. Implementing data caches
	4. Event driven publish/subscribe

From the doctests:

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
        ...    print ("stopping")
        ...    ob.stop()
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
