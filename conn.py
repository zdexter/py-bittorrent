import socket
from message import WireMessage

class AcceptConnection(object):
    """Facilitates creation of new socket when
       peers connect to an existing socket.
    """
    def __init__(self, parent, bind_to=6881):
        self._parent = parent
        self.socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
                )
        self.socket.bind(('localhost', bind_to))
        self.socket.listen(5)
    def recv_msg(self, msg):
        handshake = WireMessage.decode(msg)
        msg_type, msg_contents = WireMessage.decode(buf)
        if msg_type == 'handshake':
            print 'INCOMING HANDSHAKE'
            new_conn, addr = self.socket.accept()
            func = getattr(self._parent, msg_type)
            func(new_conn, addr, msg_contents)
            return True
        raise Exception('Non-handshake message received.')
    def fileno(self):
        return self.socket.fileno()

class MsgConnection(object):
    """Helps receive, queue and send messages.
       Wraps socket.socket.
    """
    def __init__(self, parent, socket=None):
        self._parent = parent
        self._outbound = []
        if socket:
            self.socket = socket
    def connect(self, ip, port, timeout=2):
        self.ip = ip
        self.port = port
        """Connect to address:port via TCP
            and return a file descriptor
            representing the new connection.
        """
        self.socket = socket.create_connection((ip, port), timeout)
        print('Success: Socket opened to {}:{}'.format(
            ip, port
            ))
    def send_next_msg(self):
        """Send next msg in queue.
        """
        try:
            msg = self._outbound.pop()
        except IndexError:
            return False
        print 'Sending message to {}:{}'.format(self.ip, self.port)
        bytes_sent = self.socket.send(msg)
        assert len(msg) == bytes_sent
    def recv_msg(self):
        """Receive all complete messages currently on wire.
        """
        buf = ""
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
        messages = WireMessage.decode_all(buf)
        for msg in messages:
            print 'conn: recv wire msg of type {}: {}'.format(msg[0],msg[1])
            func = getattr(self._parent, msg[0])
            func(msg[1])
    def enqueue_msg(self, msg):
        self._outbound.append(msg)
    def fileno(self):
        return self.socket.fileno()
