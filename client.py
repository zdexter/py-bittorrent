import socket
import time
import util
import struct

class NetworkedPeer(object):
    def __init__(self):
        self._outbound = []

    def connect_to(self, full_address):
        """Connect to address:port via TCP
            and return a file descriptor
            representing the new connection.
        """
        print type(full_address[0])
        self._socket = socket.create_connection(full_address)
        print('Success: Socket opened to {}:{}'.format(
            full_address[0], full_address[1]
            ))
        return self._socket
    def send_next_msg(self):
        """Send next message in queue over socket.
        """
        try:
            msg = self._outbound.pop()
        except IndexError:
            return False
        print 'Sending message:', msg
        self._socket.send(msg)
    def recv_msg(self):
        """Receive msg on socket.
        """
        msg = self._socket.recv(2048)
        if len(msg) == 0: return
        print 'Receiving message:', msg
        # decode_wire_msg(msg)
    def enqueue_msg(self, msg):
        self._outbound.append(msg)
    def fileno(self):
        return self._socket.fileno()

class Peer(NetworkedPeer):
    def __init__(self, ip, port, peer_id=None):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.am_choking = True
        self.am_interested = False
        self.choking = True
        self.interested = False
        super(Peer, self).__init__()

class Client(NetworkedPeer):
    def __init__(self, torrent_list):
        self.peer_id = self._gen_peer_id()
        self.peers = {}
        self.torrents = torrent_list
        self.torrent = torrent_list[0]
        super(Client, self).__init__()

    def build_handshake(self, peer):
        """Return formatted message ready for sending to peer:
            handshake: <pstrlen><pstr><reserved><info_hash><peer_id>
        """
        pstr = "BitTorrent protocol"
        reserved = "0"*8
        handshake = [
            str(len(pstr)),pstr,reserved,
            self.torrent.info_hash,
            self.peer_id
            ]
        return ''.join(handshake) # This doesn't seem like the best way to concat.
    def start_serving(self, torrent):
        self.info_hashes[torrent] = torrent_file
    def stop_serving(self, torrent):
        del self.torrents[torrent]
    def connect_to_peers(self, peer_list):
        for peer in peer_list:
            handshake = self.build_handshake(peer)
            try:
                self.connect_to((peer.ip, peer.port))
            except socket.error, e:
                print('Socket error while connecting to {}:{}: {}'.format(
                    peer.ip, peer.port, e
                    ))
                continue
            peer.enqueue_msg(handshake)
    def parse_msg(self, msg):
        length, msg_id, payload = struct.unpack('4s1Bs')
        if len(payload) == int(length):
            return (length, msg_id, payload)
        return False
    def _gen_peer_id(self):
        """Return a hash of the (not necessarily fully qualified)
            hostname of the machine the Python interpreter
            is running on, plus a timestamp.
        """
        seed = socket.gethostname() + str(time.time())
        return util.sha1_hash(seed) 
