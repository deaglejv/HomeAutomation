from getpass import getpass
from argparse import ArgumentParser
import logging

def GetCmdLineArguments():
    parser = ArgumentParser()

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

    # RabbitMQ items
    parser.add_argument("--rabbitURL", dest="rabbitURL",
                        help="Rabbit URL to use")
    parser.add_argument("--rabbitUser", dest="rabbitUser",
                        help="Rabbit User to use")
    parser.add_argument("--rabbitPassword", dest="rabbitPassword",
                        help="Rabbit Password to use")


    args = parser.parse_args()

    if args.jid is None:
        args.jid = input("JID: ")
    if args.password is None:
        args.password = getpass("Password: ")

    if args.rabbitURL is None:
        args.rabbitURL = input("Rabbit URL: ")
    if args.rabbitUser is None:
        args.rabbitUser = input("Rabbit User: ")
    if args.rabbitPassword is None:
        args.rabbitPassword = getpass("Rabbit Password: ")

    return args