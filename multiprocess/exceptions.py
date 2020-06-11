

class SubscriberClosedException(Exception):
    def __init__(self, sub):
        self.message = "Subscriber is closed {}".format(sub)
        super().__init__(self.message)

    def __str__(self):
        return "SUBSCRIBER ERROR : {}".format(self.message)


class NotImplementedException(Exception):
    def __init__(self, message="..."):
        self.message = message

    def __str__(self):
        return "Not implemented : {}".format(self.message)
