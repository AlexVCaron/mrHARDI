class NotImplementedException(Exception):
    def __init__(self, message="..."):
        self.message = message

    def __str__(self):
        return "Not implemented : {}".format(self.message)


class ChannelInnerCancelException(Exception):
    pass


class StatefulException(Exception):
    def __init__(self, errored_item, exception, message=None):
        self.errored_item = errored_item
        self.exception = exception
        self.message = type(exception).__name__

        mess = "{} received and exception :\n{}".format(
            errored_item.name, exception
        )

        self.message = "{}\n{}".format(message, mess) if message else mess

    def __str__(self):
        return self.message


class UnrecoverableException(StatefulException):
    pass


class RecoverableException(StatefulException):
    pass


class UnexpectedUnitException(UnrecoverableException):
    pass


class UnexpectedLayerException(UnrecoverableException):
    pass


class TransmitClosedException(UnrecoverableException):
    def __init__(self, sub):
        super().__init__(sub, self)


class YieldClosedException(RecoverableException):
    def __init__(self, sub):
        super().__init__(sub, self)


class AlreadyShutdownException(RecoverableException):
    def __init__(self, sub):
        super().__init__(sub, self)