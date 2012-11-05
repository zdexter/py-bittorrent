import socket
import time
import util

class Client():
    def __init__(self):
        self.peer_id = self._gen_peer_id()
    def _gen_peer_id(self):
        """Return a hash of the (not necessarily fully qualified)
            hostname of the machine the Python interpreter
            is running on, plus a timestamp.
        """
        seed = socket.gethostname() + str(time.time())
        return util.sha1_hash(seed)        
