'''  
    Required hooks and general housework to make a local registry which extends the 
    global component registry
    
    Liberally swiped from grok and zope code
'''

import zmq, pickle, threading
from zope import component, interface

__all__ = ["setSite", "getSite","getSiteManager", "setHooks", "resetHooks"]


def adapter_hook(interface, object, name='', default=None):
    try:
        return siteinfo.adapter_hook(interface, object, name, default)
    except component.interfaces.ComponentLookupError:
        return default


class read_property(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, inst, cls):
        if inst is None:
            return self

        return self.func(inst)

class SiteInfo(threading.local):
    site = None
    sm = component.getGlobalSiteManager()

    def adapter_hook(self):
        adapter_hook = self.sm.adapters.adapter_hook
        self.adapter_hook = adapter_hook
        return adapter_hook

    adapter_hook = read_property(adapter_hook)

siteinfo = SiteInfo()


def setSite(site):
    sm = site.getSiteManager()
    siteinfo.site = site
    siteinfo.sm = sm
    try:
        del siteinfo.adapter_hook
    except AttributeError:
        pass
        
def getSite():
    return siteinfo.site


def getSiteManager(context=None):
    """ A special hook for getting the site manager.

        Here we take the currently set site into account to find the appropriate
        site manager.
    """
    if context is None:
        return siteinfo.sm

    sm = component.interfaces.IComponentLookup(
        context, component.getGlobalSiteManager())
    return sm

def setHooks():
    component.adapter_hook.sethook(adapter_hook)
    component.getSiteManager.sethook(getSiteManager)

def resetHooks():
    # Reset hookable functions to original implementation.
    component.adapter_hook.reset()
    component.getSiteManager.reset()

