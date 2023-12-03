import ast

# Example string
string_example = "('123.123.123.1', 60005)"
test = ("123.123.123.1", 60005)


def tuple_bytes(address):
    values = ', '.join(str(item) for item in address)
    tuple_string = bytes(''.join(('(', values, ')')), encoding='utf-8')
    return tuple_string


def bytes_tuple(data):
    string_tuple = str(data, encoding='utf-8').replace('(',
                                                       '').replace(')', '').replace(' ', '').split(',')
    return string_tuple


eexample = bytes_tuple(tuple_bytes(test))
print(eexample[1])
