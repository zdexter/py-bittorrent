from collections import defaultdict
from reactor import Reactor
from tracker import Tracker
import socket
import time
import util
from conn import AcceptConnection
from message import WireMessage
from peer import Peer
import logging
import urllib2

class Client(object):
    def __init__(self, torrent):
        self.logger = logging.getLogger('bt.peer.client')
        self.torrent = torrent
        self.peer_id = self._gen_peer_id()
        self.peers = {}
        self.bad_peers = defaultdict(int)
        self._pending_peers = []
        self.conn = AcceptConnection(self)
        self._reactor = Reactor()

        self.tracker = Tracker(self.torrent, self)
        resp = self.tracker.connect()
        self.update_peers()
        self._reactor.add_connections(self.conn, list(p.conn for p in self.peers.values()))
    def start(self):
        self._reactor.select()
    def _new_peers(self, peer_list, client):
        """Return new Peer instances for each peer the tracker tells us about.
        """
        own_ext_ip = urllib2.urlopen('http://ifconfig.me/ip').read() # HACK
        return [Peer(p[0], p[1], client) for p in peer_list if p[0] != own_ext_ip]
    def _get_peers(self, resp):
        raw_bytes = [ord(c) for c in resp['peers']]
        peers = []
        for i in range(0,len(raw_bytes) / 6):
            start = i*6
            end = start + 6
            ip = ".".join(str(i) for i in raw_bytes[start:end-2])
            port = raw_bytes[end-2:end]
            port = (port[1]) + (port[0] * 256)
            peers.append([ip,port])
        return peers
    def connect_to_peers(self, peer_list):
        for peer in peer_list:
            try:
                if self.peers[peer.peer_id] or self.bad_peers[peer.peer_id] > 0:
                    continue
            except KeyError:
                pass
            handshake = WireMessage.build_handshake(self, peer, self.torrent)
            try:
                peer.conn.connect(peer.ip, peer.port)
            except socket.error, e:
                self.logger.debug('Socket error while connecting to {}:{}: {}'.format(
                    peer.ip, peer.port, e
                    ))
            else:
                peer.conn.enqueue_msg(handshake)
                self.peers[peer.peer_id] = peer
    def update_peers(self, seconds=120):
        """Add peers we haven't tried to add yet.
            TODO: Make this happen only ever `seconds` seconds.
        """
        self.logger.debug('UPDATING PEERS >>>>>')
        resp = self.tracker.connect()
        self.connect_to_peers(
                self._new_peers(self._get_peers(resp), self)
                )
    def handshake(self, new_conn, addr, msg):
        peer_id = repr(msg[20:])
        self.logger.debug('Testing for peer existence:', self.peers[peer_id])
        # Python will use repr(peer_id) in data structures; store it as such.
        self.peers[peer_id] = Peer(addr[0], addr[1], peer_id, conn)
    def notify_closed(self, peer_id):
        """Callback for peer to inform client that it has
            disconnected.
        """
        self._reactor.remove_subscriber(peer_id)
        del self.peers[peer_id]
        self.logger.debug('Removed {} from peers.'.format(peer_id))
    def _gen_peer_id(self):
        """Return a hash of the (not necessarily fully qualified)
            hostname of the machine the Python interpreter
            is running on, plus a timestamp.
        """
        seed = socket.gethostname() + str(time.time())
        return util.sha1_hash(seed) 
