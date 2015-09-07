import pickle
import datetime

from Utils.AutomationMessage import AutomationMessage


# fill this with the action words and the queues they will use
actionWords = dict(status='SendMessage'
                    ,open='GarageActionNeeded')

def ParseJabberMessage(msg):
    msgRouting = dict()
    msgAction = msg['body']

    if(msgAction.find(' ') > 0):
        msgAction = msgAction[0:msgAction.find(' ')]

    if msgAction in actionWords:
        msgBody = pickle.dumps(AutomationMessage(msg['from'].bare
                                                 , msg['To']
                                                 , msgAction
                                                 , msg['body']
                                                 , datetime.datetime.now()))
        msgRouting.update({'routing_key':actionWords[msgAction]})
        msgRouting.update({'body':msgBody})

        return msgRouting
    else:
        return None