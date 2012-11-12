import select

class Reactor():
    def __init__(self):
        self._subscribers = {} # {peer_id: callback}
        self.timers = []
    def add_torrent(self, torrent):
        """Add torrent's client peers to the event loop.
        """
        print 'Peers were', torrent.client.peers
        for peer_id in torrent.client.peers.keys():
            self._subscribers[peer_id] = torrent.client.peers[peer_id]
        self._subscribers[torrent.client.peer_id] = torrent.client

    def select(self):
        # peers = self._subscribers.keys()
        # inputs: file descriptors ready for reading
        # outputs: file descriptors ready for writing
        # select() calls fileno() on arguments
        inputs = self._subscribers.values()
        outputs = self._subscribers.values()
        while inputs:
            # select.select() looks for fileno() on inputs and outputs
            readable, writeable, exceptional = select.select(inputs, outputs, inputs, 10)
            
            for s in readable:
                s.recv_msg()
            for s in writeable:
                s.send_next_msg()
            for s in exceptional:
                print 'Exceptional', s

            for t in self.timers:
                pass
