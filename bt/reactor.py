import select
from util import DownloadCompleteException
import logging

class Reactor():
    def __init__(self):
        self.logger = logging.getLogger('bt.reactor')
        self._subscribers = {} # {peer_id: class instance}
        self._timers = []
    def add_callback(self, callback):
        self._timers.append(callback)
    def remove_subscriber(self, subscriber_id):
        del self._subscribers[subscriber_id]
    def add_connections(self, client_conn, peer_conns):
        conn_list = [client_conn]
        for pc in peer_conns:
            conn_list.append(pc)
        """Register connections with the event loop.
        """
        for conn in conn_list:
            self._subscribers[conn.parent.peer_id] = conn

    def select(self, timeout=10):
        """Block until at least one socket is readable or writeable.

        Run all callbacks every `timeout` seconds.

        """
        # inputs: file descriptors ready for reading
        # outputs: file descriptors ready for writing
        # select() calls fileno() on arguments
        inputs = self._subscribers.values()
        outputs = self._subscribers.values()
        while inputs:
            # select.select() looks for fileno() on inputs and outputs
            readable, writeable, exceptional = select.select(inputs, outputs, inputs, timeout)
            
            for s in readable:
                try:
                    s.recv_msg()
                except DownloadCompleteException, e:
                    return
            for s in writeable:
                while s.has_next_msg():
                    s.send_next_msg()
            for s in exceptional:
                self.logger.error('Exceptional: {}'.format(s))
            
            for t in self._timers:
                t()

            inputs = self._subscribers.values()
            outputs = self._subscribers.values()
