import bencode
import math
import util

def read(file_name):
    """Return info dictionary based upon .torrent file's contents.
       This method leaves the file's contents bencoded.
    """
    f = open(file_name, 'r')
    f.read()
    length = f.seek(0, 2).tell()
    f.close()

    info_dict = {}
    return info_dict

def pieces_hashes(string, num_pieces):
    """Break string into num_pieces parts.
       Return array built from 20-byte SHA1 hashes
        of those parts.
    """
    split_interval = len(string) / num_pieces
    assert split_interval * num_pieces = len(string)

    output = None
    current_pos = 0
    while current_pos < len(string):
        piece_hash = util.sha1_hash(string[current_pos:current_pos+split_interval])
        output += piece_hash
        current_pos += split_interval
    return output

def generate(url, file_name, piece_length=512):
    """Write a metainfo file of name file_name to 
        current directory.
    """

    contents = 'Some random data!'

    num_pieces = math.ceil(
        length / piece_length
        )

    info_dict = {
        'name': file_name,
        'length': len(contents),
        # Fields common to single and multi-file below
        'piece_length': piece_length,
        'pieces': pieces_hashes(contents, num_pieces)
    }

    metainfo = {
        'info': info_dict,
        'announce': url
    }

    f = open(file_name, 'w')
    f.write(bencode(metainfo))
    f.close()

    return True
