#!/usr/bin/env python

import ssl
import logging
import pickle
from getpass import getpass
from argparse import ArgumentParser
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream import resolver, cert
import pika
from AutomationMessage import AutomationMessage

credentials = pika.PlainCredentials('Someone', 'A Password')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='192.168.1.x', credentials=credentials))
channel = connection.channel()

channel.queue_declare(queue='SendMessage')
channel.queue_declare(queue='ActionNeeded')

class JabberClient(ClientXMPP):
    """
        This is where any inbound messages are handled.
    """
    def __init__(self, jid, password, google_server, google_port):
        ClientXMPP.__init__(self, jid, password)

        self.google_server = google_server
        self.google_port = google_port

        self.logger = logging.getLogger(__name__)
        log_fmt = '%(asctime)-15s %(levelname)-8s %(message)s'
        log_level = logging.INFO
        logging.basicConfig(format=log_fmt, level=log_level)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.receive_msg)

        self.add_event_handler("ssl_invalid_cert", self.ssl_invalid_cert)

        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0004') # Data Forms
        self.register_plugin('xep_0060') # PubSub
        self.register_plugin('xep_0199') # XMPP Ping

        self.connect((google_server, google_port))
        self.process(block=False)

    def ssl_invalid_cert(self, raw_cert):
        """
            Handle an invalid certificate from the Jabber server
            This may happen if the domain is using Google Apps
            for their XMPP server and the XMPP server.
        """
        hosts = resolver.get_SRV(self.google_server, self.google_port,
                                 'xmpp-client',
                                 resolver=resolver.default_resolver())

        domain_uses_google = False
        for host, _ in hosts:
            if host.lower()[-10:] == 'google.com':
                domain_uses_google = True

        if domain_uses_google:
            try:
                if cert.verify('talk.google.com', ssl.PEM_cert_to_DER_cert(raw_cert)):
                    logging.debug('Google certificate found for %s', self.boundjid.server)
                    return
            except cert.CertificateError:
                pass

        logging.error("Invalid certificate received for %s", self.boundjid.server)
        self.disconnect()

    def start(self, event):
        """
            Process the session_start event.
        """
        self.send_presence()
        try:
            self.get_roster()
        except IqError as err:
            logging.error('There was an error getting the roster')
            logging.error(err.iq['error']['condition'])
            self.disconnect()
        except IqTimeout:
            logging.error('Server is taking too long to respond')
            self.disconnect()

    def receive_msg(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """

        actionWords = ['open', 'close']

        if msg['type'] in ('chat', 'normal'):
            if  any(x in msg['body'].lower() for x in actionWords):
                channel.basic_publish(exchange='',
                      routing_key='ActionNeeded',
                      body=pickle.dumps(AutomationMessage(msg['from'].bare,msg['body'])))
            else:
                channel.basic_publish(exchange='',
                      routing_key='SendMessage',
                      body=pickle.dumps(AutomationMessage(msg['from'].bare,msg['body'])))


def main():
    parser = ArgumentParser(description=JabberClient.__doc__)

    # Output verbosity options.
    parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                        action="store_const", dest="loglevel",
                        const=logging.ERROR, default=logging.INFO)
    parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                        action="store_const", dest="loglevel",
                        const=logging.DEBUG, default=logging.INFO)

    # JID and password options.
    parser.add_argument("--jid", dest="jid",
                        help="JID to use")
    parser.add_argument("--password", dest="password",
                        help="password to use")
    parser.add_argument("--server", dest="server", default='talk.google.com',
                        help="server to connect to")
    parser.add_argument("--port", dest="port", default=5222,
                        help="port to connect to")


    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(level=args.loglevel, format='%(levelname)-8s %(message)s')

    if args.jid is None:
        args.jid = input("JID: ")
    if args.password is None:
        args.password = getpass("Password: ")

    xmppClient = JabberClient(args.jid, args.password, args.server, args.port)

    def SendMessage(ch, method, properties, body):
        msg = pickle.loads(body)

        xmppClient.send_message(mto=msg.msgTo
                                     , mbody="Thanks for sending: %s" % msg.msgBody
                                     , mtype='chat')

    channel.basic_consume(SendMessage,
                          queue='SendMessage',
                          no_ack=True)

    channel.start_consuming()


if __name__ == "__main__":
    main()