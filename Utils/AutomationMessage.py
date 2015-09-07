class AutomationMessage(object):
    def __init__(self, msgFrom, msgTo, msgAction, msgBody, msgDateTime):
        self.msgFrom = msgFrom
        self.msgTo = msgTo
        self.msgAction = msgAction
        self.msgBody = msgBody
        self.msgDateTime = msgDateTime