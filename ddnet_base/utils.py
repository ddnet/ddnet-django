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
