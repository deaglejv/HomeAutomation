#!/usr/bin/env python

import logging

import pika

from Utils.CmdLineArguments import GetCmdLineArguments


# This is going to get used a lot throughout the scripts I suspect.
args = GetCmdLineArguments()

credentials = pika.PlainCredentials(args.rabbitUser, args.rabbitPassword)
connection = pika.BlockingConnection(pika.ConnectionParameters(host=args.rabbitURL, credentials=credentials))
channel = connection.channel()

channel.exchange_declare(exchange='topic_logging', type='direct')

loggingQueue = channel.queue_declare(exclusive=True)
logging_queue_name = loggingQueue.method.queue

channel.queue_bind(exchange='topic_logging', queue=logging_queue_name, routing_key='Logging')

logger = logging.getLogger(__name__)
log_fmt = '%(asctime)-15s %(levelname)-8s %(message)s'
log_level = logging.INFO
logging.basicConfig(format=log_fmt, level=log_level)

def LogMessage(ch, method, properties, body):
        logger.info(body.decode("utf-8"))


def main():
    channel.basic_consume(LogMessage,
                          queue=logging_queue_name,
                          no_ack=True)

    channel.start_consuming()


if __name__ == "__main__":
    main()