# -*- coding: utf-8 -*-

"""
# trigger_xmlrpc.py - Twisted twistd server plugin for Trigger
"""

__author__ = 'Jathan McCollum'
__maintainer__ = 'Jathan McCollum'
__email__ = 'jathan.mccollum@teamaol.com'
__copyright__ = 'Copyright 2012-2013, AOL Inc.'

from zope.interface import implements
from twisted.application.internet import TCPServer, SSLServer
from twisted.application.service import IServiceMaker, MultiService
from twisted.conch.manhole_tap import makeService as makeConsoleService
from twisted.plugin import IPlugin
from twisted.python.rebuild import rebuild
from twisted.python import usage, log
from twisted.web import server, xmlrpc
import warnings

try:
    from twisted.internet import ssl
except ImportError:
    # If no ssl, complain loudly.
    warnings.warn('SSL support disabled for Trigger XMLRPC Server: PyOpenSSL required.',
                  RuntimeWarning)
    ssl = None

from trigger.contrib.xmlrpc.server import TriggerXMLRPCServer


# Defaults
XML_PORT = 8000
SSH_PORT = 8001
SSH_USERS = 'users.txt'
SSL_KEYFILE = 'server.key'
SSL_CERTFILE = 'cacert.pem'


class Options(usage.Options):
    optParameters = [
        ['port', 'p', XML_PORT, 'Listening port for XMLRPC'],
        ['ssh-port', 's', SSH_PORT, 'Listening port for SSH manhole'],
        ['ssh-users', 'u', SSH_USERS,
         'Path to a passwd(5)-format username/password file'],
        ['ssl-keyfile', 'k', SSL_KEYFILE,
         'Path to a file containing a private key'],
        ['ssl-certfile', 'c', SSL_CERTFILE,
         'Path to a file containing a CA certificate'],
    ]

class TriggerXMLRPCServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = 'trigger-xmlrpc'
    description = 'Trigger XMLRPC Server'
    options = Options

    def makeService(self, options):
        rpc = TriggerXMLRPCServer(allowNone=True, useDateTime=True)
        xmlrpc.addIntrospection(rpc)
        site_factory = server.Site(rpc)

        # Try to setup SSL 
        if ssl is not None:
            ctx = ssl.DefaultOpenSSLContextFactory(options['ssl-keyfile'],
                                                   options['ssl-certfile'])
            xmlrpc_service = SSLServer(int(options['port']), site_factory, ctx)
        # Or fallback to clear-text =(
        else:
            xmlrpc_service = TCPServer(int(options['port']), site_factory)

        # SSH Manhole service
        console_service = makeConsoleService(
            {
                'sshPort': 'tcp:%s' % options['ssh-port'],
                'telnetPort': None,
                'passwd': options['ssh-users'],
                'namespace': {
                    'service': rpc,
                    'rebuild': rebuild,
                    'factory': site_factory,
                }
            }
        )

        svc = MultiService()
        xmlrpc_service.setServiceParent(svc)
        console_service.setServiceParent(svc)
        return svc

serviceMaker = TriggerXMLRPCServiceMaker()
