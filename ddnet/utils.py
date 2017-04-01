import time

from queue import Queue

class Log:
    '''Class to allow non blocking reading from a log being generated.'''

    def __init__(self):
        '''Init with a queue where the log is going to be written.'''
        self._queue = Queue()
        self._log = ''

    def __str__(self):
        '''Take everything from the queue and store it within this object and return full log.'''
        s = ''
        while not self._queue.empty():
            s += self._queue.get_nowait()
        self._log += s
        return self._log

    @property
    def queue(self):
        '''The Queue this object is operating on.'''
        return self._queue


def log_exception(logfunc, *exceptions, default=None, retry_seconds=None):
    '''
    Catch exceptions and pass them to logfunc.

    Return default on exception or retry in retry_seconds if specified.
    '''

    def _decorator(func):
        def _wrapper(*args, **kwargs):
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logfunc(e)
                    if retry_seconds is None:
                        return default
                    else:
                        time.sleep(retry_seconds)
        _wrapper.__doc__ = func.__doc__
        return _wrapper
    return _decorator
