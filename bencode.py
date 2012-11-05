def encode(value):
    """Figure out type of value and call the appropriate
        encoding function.
       Return encoded value.
    """
    value_type = type(value)
    if value_type == int:
        return encode_int(value)
    elif value_type == str:
        return encode_str(value)
    elif value_type == list:
        return encode_list(value)
    elif value_type == dict:
        return encode_dict(value)

    raise Exception(
        'Invalid type supplied to encode().'
        )

def encode_str(the_str):
    """
    >>> encode_str("spam")
    "4:spam"
    """

    prefix = str(len(the_str))
    return prefix + ":" + the_str

def encode_int(the_int):
    """
    >>> encode(3)
    "i3f"
    """
    prefix = "i"
    suffix = "e"
    return prefix + str(the_int) + suffix

def encode_list(the_list):
    pass

def encode_dict(the_dict):
    """Return bencoded contents of a dict.
    """
    prefix = "d"
    suffix = "e"
    output = ""

    first = False
    # Convert each key to a string.
    # Determine type of value. Then, append key:val to output.
    for k in the_dict.keys():
        output += str(k) + ":" + encode(the_dict[k])
        if not first:
            output += ":"

    output = output [:len(output)-1] # Trim last colon
    return output

def decode(the_dict):
    """Return unescaped contents of a dict.
       Reverses encode_dict() operation.
    """

    return the_dict
