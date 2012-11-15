import struct
import binascii

class WireMessage(object):
    LP = '!IB' # "Length Prefix" (req'd by protocol)
    MESSAGE_TYPES = {
        -1: 'keep-alive',
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
            print 'decoded handshake'
            handshake = buf[:68]
            expected_length, info_dict, info_hash, peer_id = struct.unpack(
                    "B"+str(len(pstr))+"s8x20s20s",
                    handshake)
            buf = buf[68:]
            return ('handshake', (info_hash, peer_id)), buf
        
        if len(buf) < 4:
            raise Exception("Too few bytes to form a protocol message.")

        # Try to match keep-alive
        expected_length, msg_id = struct.unpack("!IB", buf[:5])
        if expected_length == 0:
            buf = buf[4:]
            return ('keep_alive'), buf

        fmt = '!' + cls.MESSAGE_TYPES[msg_id][1][3:] # Ignore length prefix
        args = None
        expected_length -= 1
        actual_length = None
        if msg_id == 7 or msg_id == 5:
            # Msg typ has variable length
            if msg_id == 7:
                fmt += str(expected_length-8) + "s"
            elif msg_id == 5:
                fmt += str(expected_length) + "s"
            #print 'fmt was', fmt
            #print 'expected_length was', expected_length
            #print 'len(buf[5:5+length])', len(buf[5:5+expected_length])
        if fmt:
            actual_length = len(buf[5:5+expected_length])
            #print 'actual', actual_length, 'expected', expected_length,\
            #    'msg_id', msg_id
            if expected_length == actual_length:
                args = (x for x in struct.unpack(fmt, buf[5:5+expected_length]))
            elif msg_id == 7: # End of piece
                print 'here, fmt was', fmt
                fmt.replace(str(expected_length+6), str(actual_length))
                print 'actual_length was', actual_length
                args = (x for x in struct.unpack(fmt, buf[5:actual_length]))
        try:
            length = actual_length or expected_length
            buf = buf[5+length:] # Advanced to next message
            # Get func name by message id
            return (cls.MESSAGE_TYPES[msg_id][0], args), buf
        except IndexError:
            print 'Index error with msg:{}'.format(msg)

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
        packed = None
        try:
            if len(args) == 0:
                packed = struct.pack(fmt, length, msg_id)
            else:
                packed = struct.pack(fmt, length, msg_id, *args)
        except struct.error, e:
            print 'At struct error, args was', args, \
                ', msg_id was', msg_id, \
                ', fmt was', fmt, \
                ' and length was', length
            raise Exception(e)
        # print 'repr of packed was', repr(packed)
        return packed
