import struct
import binascii

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
    def decode_all(cls, buf):
        """Return [(msg_type, msg_contents)] for all msg in buffer.
        """
        msg_list = []
        while len(buf) > 0:
            msg_items, buf = cls.decode(buf)
            msg_list.append(msg_items)
        return msg_list

    @classmethod
    def decode(cls, buf, pstr='BitTorrent protocol'):
        """Return tuple of (message type name, contents encoded in ASCII)
        """
        if buf[1:20] == pstr: # Received handshake
            print 'handshake'
            handshake = buf[:68]
            handshake = struct.unpack("B"+str(len(pstr))+"s8x20s20s", handshake)
            buf = buf[68:]
            return ('handshake', handshake[2]), buf
        
        if len(buf) < 4:
            raise Exception("Too few bytes to form a protocol message.")

        # Try to match keep-alive
        length = struct.unpack("!I", buf[:4])[0]
        print 'msg was', repr(buf), 'and length was', length
        if length == 0:
            print 'Trying to call keep_alive()'
            buf = buf[4:]
            return ('keep_alive'), buf

        fmt = "B"+str(length-1)+"s"
        try:
            msg = struct.unpack(fmt, buf[4:4+length])
            print 'msg was', repr(msg)
        except struct.error, e:
            print 'Struct error with format {} and msg {}: {}'.format(fmt, repr(msg), e)
        try:
            buf = buf[4+length:]
            return (cls.MESSAGE_TYPES[msg[0]], msg[1]), buf # Look up name by message id
        except IndexError:
            print 'Index error with msg:{}'.format(msg)
