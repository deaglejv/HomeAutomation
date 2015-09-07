#!/usr/bin/env python

import ssl
import pickle

from sleekxmpp import ClientXMPP

from sleekxmpp.xmlstream import resolver, cert
import pika

from Utils.CmdLineArguments import GetCmdLineArguments
from Utils.ParseJabberMessage import ParseJabberMessage

# This is going to get used a lot throughout the scripts I suspect.
args = GetCmdLineArguments()

credentials = pika.PlainCredentials(args.rabbitUser, args.rabbitPassword)
connection = pika.BlockingConnection(pika.ConnectionParameters(host=args.rabbitURL, credentials=credentials))
channel = connection.channel()

channel.exchange_declare(exchange='topic_logging', type='direct')
channel.exchange_declare(exchange='topic_send_message', type='direct')
channel.exchange_declare(exchange='topic_garage_action', type='direct')

loggingQueue = channel.queue_declare(exclusive=True)
logging_queue_name = loggingQueue.method.queue

sendMessageQueue = channel.queue_declare(exclusive=True)
send_message_queue_name = sendMessageQueue.method.queue

garageActionQueue = channel.queue_declare(exclusive=True)
garage_Action_queue_name = garageActionQueue.method.queue

channel.queue_bind(exchange='topic_logging', queue=logging_queue_name, routing_key='Logging')
channel.queue_bind(exchange='topic_send_message', queue=send_message_queue_name, routing_key='SendMessage')
channel.queue_bind(exchange='topic_garage_action', queue=garage_Action_queue_name, routing_key='GarageAction')

class JabberClient(ClientXMPP):
    """
        This is where any inbound messages are handled.
    """
    def __init__(self, jid, password, google_server, google_port):
        ClientXMPP.__init__(self, jid, password)

        self.google_server = google_server
        self.google_port = google_port

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

        channel.basic_publish(exchange='topic_logging',
                                  routing_key='Logging',
                                  body="Server Connected Successfully")

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
                    channel.basic_publish(exchange='topic_logging',
                                          routing_key='Logging',
                                          body='Google certificate found for %s' % self.boundjid.server)
                    return
            except cert.CertificateError:
                pass
        channel.basic_publish(exchange='topic_logging',
                                  routing_key='Logging',
                                  body="Invalid certificate received for %s" % self.boundjid.server)
        self.disconnect()

    def start(self, event):
        """
            Process the session_start event.
        """
        self.send_presence()
        self.get_roster()

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

        msgRouting = ParseJabberMessage(msg)
        amsg = pickle.loads(msgRouting['body'])

        if msg['type'] in ('chat', 'normal'):
            if msgRouting != None:
                channel.basic_publish(exchange='topic_send_message',
                      routing_key='SendMessage',
                      body=msgRouting['body'])

                channel.basic_publish(exchange='topic_logging',
                      routing_key='Logging',
                      body="Message Received From: %s, To: %s, Action: %s, Body: %s" % (amsg.msgFrom
                                                                                          , amsg.msgTo
                                                                                          , amsg.msgAction
                                                                                          , amsg.msgBody))
def main():
    xmppClient = JabberClient(args.jid, args.password, args.server, args.port)

    def ReplyToMessageSender(ch, method, properties, body):
        msg = pickle.loads(body)
        xmppClient.send_message(mto=msg.msgFrom
                                     , mbody="Thanks for sending: %s on %s" % (msg.msgBody, msg.msgDateTime)
                                     , mtype='chat')

        channel.basic_publish(exchange='topic_logging',
                      routing_key='Logging',
                      body="Message Sent To: %s, From: %s, Action: %s, Body: %s" % (msg.msgFrom
                                                                                          , msg.msgTo
                                                                                          , msg.msgAction
                                                                                          , msg.msgBody))

    channel.basic_consume(ReplyToMessageSender,
                          queue=send_message_queue_name,
                          no_ack=True)

    channel.start_consuming()


if __name__ == "__main__":
    main()