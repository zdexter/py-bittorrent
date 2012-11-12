import struct

class WireMessage(object):
    MESSAGE_TYPES = {
        -1: 'keep-alive',
        0: 'choke',
        1: 'unchoke',
        2: 'interested',
        3: 'not interested',
        4: 'have',
        5: 'bitfield',
        6: 'request',
        7: 'piece',
        8: 'cancel',
        9: 'port'
    }

    @staticmethod
    def build_handshake(client, peer, torrent):
        """Return formatted message ready for sending to peer:
            handshake: <pstrlen><pstr><reserved><info_hash><peer_id>
        """
        pstr = "BitTorrent protocol"
        reserved = "0"*8
        handshake = struct.pack("B"+str(len(pstr))+"s8x20s20s",
            len(pstr),
            pstr,
            torrent.info_hash,
            client.peer_id
            )
        assert len(handshake) == 49 + len(pstr)
        return handshake

    @classmethod
    def decode(cls, msg, pstr='BitTorrent protocol'):
        """Return tuple of (message type name, contents)
        """
        if msg[1:20] == pstr: # Received handshake
            handshake = msg[:68]
            handshake = struct.unpack("B"+str(len(pstr))+"s8x20s20s", handshake)
            print 'Decoded handshake:', handshake
            if len(msg[68:]) > 0:
                # Process remainder
                cls.decode(msg[68:])
            return ('handshake', handshake[2])

        length = len(msg) - 5 # Length of pyaload
        fmt = "!4sB"+str(length)+"s"
        msg = struct.unpack(fmt, msg)
        return (cls.MESSAGE_TYPES[msg[1]], msg[2]) # Look up name by message id
