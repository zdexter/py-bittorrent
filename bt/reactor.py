import select
from util import DownloadCompleteException
class Reactor():
    def __init__(self):
        self._subscribers = {} # {peer_id: class instance}
        self._timers = []
    def add_callback(self, callback):
        self._timers.append(callback)
    def remove_subscriber(self, subscriber_id):
        del self._subscribers[subscriber_id]
    def add_torrent(self, torrent):
        """Add torrent's client peers to the event loop.
        """
        # print 'Peers were', torrent.client.peers
        for peer_id in torrent.client.peers.keys():
            self._subscribers[peer_id] = torrent.client.peers[peer_id].conn
        self._subscribers[torrent.client.peer_id] = torrent.client.conn

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
                print 'Exceptional', s
            
            for t in self._timers:
                t()

            inputs = self._subscribers.values()
            outputs = self._subscribers.values()
