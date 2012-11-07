import socket
import time
import util

class Peer():
    def __init__(self, peer_id=None):
        self.peer_id = peer_id
        self.am_choking = True
        self.am_interested = False
        self.choking = True
        self.interested = False
         
class Client():
    def __init__(self, torrent_list):
        self.peer_id = self._gen_peer_id()
        self.peers = {}
        self.torrents = torrent_list

    def send_handshake(self, peer):
        """Send wire message to peer:
            handshake: <pstrlen><pstr><reserved><info_hash><peer_id>
        """ 
    
    def add_peer(self, peer):
        self.peers[peer.peer_id] = peer
        self.handshake(peer)

    def start_serving(self, torrent):
        self.info_hashes[torrent] = torrent_file
    
    def stop_serving(self, torrent):
        del self.torrents[torrent]

    def _gen_peer_id(self):
        """Return a hash of the (not necessarily fully qualified)
            hostname of the machine the Python interpreter
            is running on, plus a timestamp.
        """
        seed = socket.gethostname() + str(time.time())
        return util.sha1_hash(seed)        
