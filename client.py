import socket
import time
import util
import struct
from message import WireMessage

class NetworkedPeer(object):
    def __init__(self):
        self._outbound = []

    def send_next_msg(self):
        """Send next message in queue over socket.
        """
        try:
            msg = self._outbound.pop()
        except IndexError:
            return False
        print 'Sending message to {}:{}'.format(self.ip, self.port)
        bytes_sent = self.socket.send(msg)
        assert len(msg) == bytes_sent
    def recv_msg(self):
        """Receive msg on socket.
        """
        buf = ""
        #print self.__class__
        #print self.socket.fileno()
        #print self.socket.getpeername(), self.socket.getsockname()
        #conn, addr = self.socket.accept()
        #print 'Conn was {} and addr was {}'.format(conn,addr)
        while True:
            try:
                msg = self.socket.recv(512)
            except Exception, e:
                print 'Something went wrong with recv():', e
                print self.ip, self.port
                break
            else:
                if len(msg) == 0: break
                buf += msg
        if len(buf) == 0: return False
        msg_type, msg_contents = WireMessage.decode(msg)
        print 'Got wire msg of type {}: {}'.format(msg_type,msg_contents)

    def enqueue_msg(self, msg):
        self._outbound.append(msg)
    def fileno(self):
        return self.socket.fileno()

class Peer(NetworkedPeer):
    def __init__(self, ip, port, peer_id=None):
        self.ip = ip
        self.port = port

        if peer_id:
            self.peer_id = peer_id
        else:
            seed = self.ip + str(time.time())
            self.peer_id = util.sha1_hash(self.ip)

        self.am_choking = True
        self.am_interested = False
        self.choking = True
        self.interested = False
        super(Peer, self).__init__()
    def get_full_address(self):
        return (self.ip, self.port)
    def connect(self, timeout=2):
        """Connect to address:port via TCP
            and return a file descriptor
            representing the new connection.
        """
        self.socket = socket.create_connection((self.ip, self.port), timeout)
        print('Success: Socket opened to {}:{}'.format(
            self.ip, self.port
            ))

class Client(NetworkedPeer):
    def __init__(self, torrent_list, bind_to=6881):
        self.peer_id = self._gen_peer_id()
        self.peers = {}
        self.torrents = torrent_list
        self.torrent = torrent_list[0]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('localhost', bind_to))
        self.socket.listen(5)
        super(Client, self).__init__()

    def start_serving(self, torrent):
        self.info_hashes[torrent] = torrent_file
    def stop_serving(self, torrent):
        del self.torrents[torrent]
    def connect_to_peers(self, peer_list):
        for peer in peer_list:
            handshake = WireMessage.build_handshake(self, peer, self.torrent)
            try:
                peer.connect()
            except socket.error, e:
                print('Socket error while connecting to {}:{}: {}'.format(
                    peer.ip, peer.port, e
                    ))
            else:
                peer.enqueue_msg(handshake)
                self.peers[peer.peer_id] = peer
    def _gen_peer_id(self):
        """Return a hash of the (not necessarily fully qualified)
            hostname of the machine the Python interpreter
            is running on, plus a timestamp.
        """
        seed = socket.gethostname() + str(time.time())
        return util.sha1_hash(seed) 
