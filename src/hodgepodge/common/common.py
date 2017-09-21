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

import logging
log = logging.getLogger('common')
log.addHandler(logging.StreamHandler())
log.level = logging.INFO

class IHodgepodge(interface.Interface):
    ''' A Hodgepodge general interface '''

    def __init__(self, name):
        ''' Initialise a new object with unique <name> '''

    def recv(how=None):
        ''' Receive (who, cmd, data) from socket[how] or the default socket '''

    def send(cmd, data, how=None):
        ''' Send (me, cmd, data) to sock[how] or the default socket '''

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
    _sockets = None

    def _default_socket(self):
        if zmq.REP in self._sockets:
            return self._sockets[zmq.REP]
        elif zmq.REQ in self._sockets:
            return self._sockets[zmq.REQ]
        else:
            raise ValueError('Recv: Cannot locate an open socket')

    def recv(self, how=None):
        sock = None
        if how in self._sockets:
            sock = self._sockets[how]
        if sock is None:
            sock = self._default_socket()
        for iter in range(3):
            try:
                rsp = sock.recv()
                if rsp is None:
                    raise ValueError(u"0MQ RECEIVE FAILED")
                i = rsp.find(":")
                who = rsp[:i]
                data = rsp[i+1:]
                i = data.find(":")
                if i<0: return (who, '', data)
                cmd = data[:i]
                data = data[i+1:]
                return (who, cmd, data)
            except Exception, e:
                log.error("{}: Cannot receive: {}".format(self.__name__, str(e)))


    def send(self, cmd, data, how=None):
        sock = None
        if how in self._sockets:
            sock = self._sockets[how]
        if sock is None:
            sock = self._default_socket()

        if sock is not None:
            if type(data) is unicode:
                sock.send_string("%s:%s:%s" % (self.__name__, cmd, data))
            else:
                sock.send("%s:%s:%s" % (self.__name__, cmd, data))

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
        self._sockets[how] = self._zcontext.socket(how)
        self._sockets[how].connect(source)

    def bind(self, how):
        self._sockets[how] = self._zcontext.socket(how)
        self._sockets[how].bind(self._serve)

    def getPoller(self):
        poller = zmq.Poller()
        for s in self._sockets.values():
            poller.register(s, zmq.POLLIN)
        return poller

    def poll_socket(self, poller, timeout=100):
        socks = dict(poller.poll(timeout))
        if self.stopping() or not self._running:
            return []
        return [s for s, i in socks.items() if i == zmq.POLLIN]

#         if self._socket in socks and socks[self._socket] == zmq.POLLIN:
#             return [self._socket]
#         return []

    def stopping(self, stop=None):
        if stop is not None and self._stopping==0:
            self._stopping = 5
        if self._stopping > 0:
            log.debug('Stopping: %s' % self._stopping)
            self._stopping -= 1
            if self._stopping==0:
                log.debug('{}: stopping delay complete'.format(self.__name__))
                self.close()
            return True
        return False

    def close(self):
        if self.active():
            log.debug('{}: Terminating sockets'.format(self.__name__))
            self._running = False
            self._stopping = 0
            for s in self._sockets.values():
                s.close()
            log.debug('{}: Terminating sockets complete'.format(self.__name__))

    def __init__(self, name):
        ''' A registry has a name '''
        assert name != 'base'   # The 'base' registry is the global registry
        super(Hodgepodge, self).__init__()
        self.__name__ = name
        self._zcontext = zmq.Context()
        self._sockets = {}
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

