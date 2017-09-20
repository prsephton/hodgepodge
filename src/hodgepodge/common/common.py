'''
'''
__all__ = ["Hodgepodge", "IHodgepodge"]

# from zope.component.interfaces import IRegistrationEvent
#
# from zope.component.interfaces import IAdapterRegistration
# from zope.component.interfaces import IHandlerRegistration
# from zope.component.interfaces import ISubscriptionAdapterRegistration
# from zope.component.interfaces import IUtilityRegistration


import zmq, pickle
from zope import component, interface
from zope.site import LocalSiteManager, SiteManagerContainer
from hodgepodge import site

class IHodgepodge(interface.Interface):
    ''' A Hodgepodge general interface '''

    def __init__(self, name):
        ''' Initialise a new object with unique <name> '''

    def recv(sock=None):
        ''' Receive (who, cmd, data) from sock or the default socket '''

    def send(cmd, data, socks=None):
        ''' Send (me, cmd, data) to socks list or the default socket '''

    def active(running=None):
        ''' Return active status.  If running is specified, set status. '''

    def serve(serve):
        ''' Set default socket to <serve>. '''

    def connect(source, how):
        ''' Connect to <source>. <how> is a 0MQ protocol. '''

    def bind(how):
        ''' Listen for requests on default socket.  <how> is a 0MQ protocol.  '''

    def getPoller(self):
        ''' Get a 0MQ poller configured for input on default socket '''

    def poll_socket(poller, timeout=100):
        ''' Poll for input, on <poller> delaying for up to <timeout> ms. '''

    def setSite(new=None):
        ''' Select this as current site and activate local site manager.
            Installs hooks if <new>, allowing local sm to extend global sm.
        '''

    def close():
        ''' Close the socket and set inactive status '''


class Hodgepodge(SiteManagerContainer):
    '''  A component which provides some common functions
    '''
    _zcontext = None
    _running = False
    _stopping = 0

    def recv(self, sock=None):
        if sock is None: sock = self._socket
        rsp = sock.recv()
        i = rsp.find(":")
        who = rsp[:i]
        data = rsp[i+1:]
        i = data.find(":")
        if i<0: return (who, '', data)
        cmd = data[:i]
        data = data[i+1:]
        return (who, cmd, data)

        if rsp: return rsp

    def send(self, cmd, data, socks=None):
        if socks is None: socks = [self._socket]
        for s in socks:
            if type(data) is unicode:
                s.send_string("%s:%s:%s" % (self.__name__, cmd, data))
            else:
                s.send("%s:%s:%s" % (self.__name__, cmd, data))

    def active(self, running=None):
        if running is not None:
            if not running:
                self.stopping(True)
            else:
                self._running = True
        return self._running

    def serve(self, serve):
        self._serve = serve

    def connect(self, source, how):
        self._socket = self._zcontext.socket(how)
        self._socket.connect(source)

    def bind(self, how):
        self._socket = self._zcontext.socket(how)
        self._socket.bind(self._serve)

    def getPoller(self):
        poller = zmq.Poller()
        poller.register(self._socket, zmq.POLLIN)
        return poller

    def poll_socket(self, poller, timeout=100):
        socks = dict(poller.poll(timeout))
        if self.stopping():
            return []
        if self._socket in socks and socks[self._socket] == zmq.POLLIN:
            return [self._socket]
        return []

    def stopping(self, stop=None):
        if stop: self._stopping = 5
        if self._stopping > 0:
            self._stopping -= 1
            if self._stopping==0:
                self._running = False
            return True
        return False

    def close(self):
        self._running = False
        self._socket.close()

    def __init__(self, name):
        ''' A registry has a name '''
        assert name != 'base'   # The 'base' registry is the global registry
        super(Hodgepodge, self).__init__()
        self.__name__ = name
        self._zcontext = zmq.Context()
        sm = LocalSiteManager(self)
        self.setSiteManager(sm)
        self.setSite()

    def setSite(self, new=None):
        ''' Used to switch between sites '''
        prev = site.getSite()
        if new is None:
            site.setSite(self)
            site.setHooks()
        else:
            site.setSite(new)
        return prev

if __name__ == '__main__':
    """
        :doctest:

    """

