from enum import Enum

# class syntax


class Flag(Enum):
    FIN = b'1'
    SYN = 2


flags = Flag.FIN.value

print(flags)
