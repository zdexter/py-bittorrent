import struct
import binascii

class WireMessage(object):
    LP = '!IB' # "Length Prefix" (req'd by protocol)
    MESSAGE_TYPES = {
        -1: 'keep_alive',
        0: ('choke', LP, 1),
        1: ('unchoke', LP, 1),
        2: ('interested', LP, 1),
        3: ('not interested', LP, 1),
        4: ('have', LP+'I', 5),
        # bitfield: Append <bitfield> later. Dynamic length.
        5: ('bitfield', LP),
        6: ('request', LP+'III', 13),
        # piece: Append <index><begin><block> later. Dynamic length.
        7: ('piece', LP+'II'),
        8: ('cancel', LP+'III', 13),
        9: ('port', LP+'BB', 3)
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
            handshake = buf[:68]
            expected_length, info_dict, info_hash, peer_id = struct.unpack(
                    "B"+str(len(pstr))+"s8x20s20s",
                    handshake)
            buf = buf[68:]
            return ('handshake', (info_hash, peer_id)), buf
        
        if len(buf) < 4:
            raise Exception("Too few bytes to form a protocol message.")

        # Try to match keep-alive
        try:
            keep_alive = struct.unpack("!I", buf[:4])[0]
            assert keep_alive == 0
            buf = buf[4:]
            return (cls.MESSAGE_TYPES[-1], None), buf
        except AssertionError:
            pass

        # First 5 bytes are always <4:total_message_length><1:msg_id>
        total_message_length, msg_id = struct.unpack("!IB", buf[:5])
        # Advance buffer to payload
        buf = buf[5:]
        # Calculate args and payload length
        fmt = '!' + cls.MESSAGE_TYPES[msg_id][1][3:] # Ignore length prefix
        args_and_payload_length = total_message_length - 1 # Discount msg_id byte
        args_and_payload = buf[:args_and_payload_length]

        # If there is a payload, this block will handle it.
        payload_length = args_and_payload_length # If only args; i.e., if no payload
        if msg_id == 7 or msg_id == 5: # Variable-length payload. Append length arg to fmt 
            if msg_id == 7:
                # <len=0009+X><id=7><4:index><4:begin><4:length>
                # Value of <4:length> does not include the 8 bytes in <4:index><4:begin>
                payload_length -= 8
            fmt += str(payload_length) + "s" 

        args = None
        args = (x for x in struct.unpack(fmt, args_and_payload))
        # Advance buffer past payload
        buf = buf[args_and_payload_length:] 
        try:
            # Get func name by message id
            return (cls.MESSAGE_TYPES[msg_id][0], args), buf
        except IndexError:
            raise Exception('Index error with msg:{}'.format(msg))

    @classmethod
    def construct_msg(cls, msg_id, *args):
        """Return raw bytes formatted according to the
            BitTorrent protocol's spec for msg_id.
           MESSAGE_TYPES[key] = (name,{complete,partial}fmt,len(fmt+id))
        """
        fmt = cls.MESSAGE_TYPES[msg_id][1]
        length = None
        try:
            length = cls.MESSAGE_TYPES[msg_id][2]
        except IndexError, e:
            # Match below --> constructing variable-length msg body
            if msg_id == 5:
                # bitfield: <bitfield>
                length = len(args[0])
                fmt += str(length) + 's'
            elif msg_id == 7:
                # piece: <index><begin><block>
                length = len(args[2])
                fmt += str(length) + 's'
            else:
                raise Exception(
                        'No length for unexpected msg id {}'.format(msg_id)
                        )
            length += 1 # Message ID
        packed = None
        assert msg_id != 0
        try:
            if len(args) == 0:
                packed = struct.pack(fmt, length, msg_id)
            else:
                packed = struct.pack(fmt, length, msg_id, *args)
        except struct.error, e:
            raise Exception('At struct error, args was', args, \
                ', msg_id was', msg_id, \
                ', fmt was', fmt, \
                ' and length was', length)
        return packed
