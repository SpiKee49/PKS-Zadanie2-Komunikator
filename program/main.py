
import socket
import sys
import math
from threading import Thread
import time
from enum import Enum


def to_fragments(data, fragment_size):
    fragments = []
    for i in range(0, math.ceil(len(data)/fragment_size)):
        if (((i+1)*fragment_size % fragment_size) == 0):
            fragments.append(data[i*fragment_size:(i+1)*fragment_size])
        else:
            fragments.append(data[i*fragment_size:])

    return fragments


class Flag(Enum):
    FIN = 1
    SYN = 2
    FILE_NAME = 3
    FRAGMENT = 4
    CORRECT = 5
    INCORRECT = 6
    FINAL_FRAG = 7
    KEEP_ALIVE = 8
    ROLE_SWITCH = 9


class Packet:
    def __init__(self, packet) -> None:
        self.flag = packet[0]
        self.fragment_size = packet[1:3]
        self.fragment_number = packet[3:6]
        self.payload = packet[6:-4]


##### CLIENT #####

def handle_inputs():
    sending_method = ''
    fragments = []
    while True:
        print("[x] Select option for sending")
        print("[1] Sending Message")
        print("[2] Sending File")
        sending_method = input()
        if int(sending_method) in [1, 2]:
            break
        else:
            print('[i] Invalid method selected!')
            continue

    fragment_size = input("Provide fragment size(def. 1461): ")
    if fragment_size == '':
        fragment_size = 1461
    else:
        fragment_size = int(fragment_size)
    while int(fragment_size) <= 0 or int(fragment_size) > 1461:
        print('Size of fragment has to be from interval 0 < x  <= 1461')
        fragment_size = input("Provide fragment size(def. 1461): ")

    # sending message
    if sending_method == "1":
        print('Your message:\n')
        message = input()
        data = bytes(message, encoding='utf-8')
        fragments = to_fragments(data, fragment_size)
    # sending file
    elif sending_method == "2":
        print('File path:\n')
        file_path = input()
        file = open(file_path, 'rb')
        file_data = file.read()
        file.close()
        # TODO: separate fragments for path and file
        fragments = [*to_fragments(file_path, fragment_size),
                     *to_fragments(file_data, fragment_size)]

    return fragments


class Client:
    def __init__(self, server_ip, server_port) -> None:
        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket creation
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock.settimeout(20)
        print('[i] Client created... (IP: {} )'.format(
            ':'.join([server_ip, str(server_port)])))

    def clientUp(self):
        data = None
        # [i] Initializing connection with server
        print('[i] Initializing connection with server...')
        self.send_data(Flag.SYN, int(0).to_bytes(1), int(0).to_bytes(2), b'')
        data = self.receive()
        if (data.flag == Flag.SYN):
            print('[i] Connection established')

        while data != "Server closing connection":
            fragments = handle_inputs()
            number
            for fragment in fragments:
                self.send_data(fragment)

            data = self.receive()
            print(data)

        self.quit()

    def keep_alive(self):
        try:
            while True:
                self.send_data(Flag.KEEP_ALIVE)
                time.sleep(5)
        except TimeoutError:
            self.quit()

    def receive(self):
        data = None
        data, self.server = self.sock.recvfrom(1500)
        packet = Packet(data)
        return packet

    def send_data(self, flag, fragment_size, fragment_number, data):
        packet = bytes([*flag.value.to_bytes(1), *
                       fragment_size, *fragment_number, *data])
        self.sock.sendto(packet, (self.server_ip, self.server_port))

    def quit(self):
        self.sock.close()  # correctly closing socket
        print("[i] Client closed..")


##### SERVER #####
class Server:

    def __init__(self, ip, port) -> None:
        self.server_ip = ip
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))

    def serverUp(self):
        print('[i] Server is up and listening... (IP: {} )'.format(
            ':'.join([self.server_ip, str(self.server_port)])))
        data = "empty"
        self.sock.settimeout(30.0)
        try:
            while True:
                if data == "End":
                    break

                if data == "SYN":
                    self.send_response('SYN ACK')

                if data == 'Keep Alive':
                    self.send_response('Keep Alive ACK')

                if data != "empty":
                    self.send_response(Flag.SYN)

                data = self.receive()

            self.send_response('Server closing connection')
            self.quit()
        except TimeoutError:
            print('[i] Server timeout...')
            self.quit()

    def receive(self):
        data = None

        while data == None:
            data, self.client = self.sock.recvfrom(1500)
            packet = Packet(data)
            print("flag: {}".format(packet.flag))
            print("fragment_size: {}".format(packet.fragment_size))
            print("fragment_number: {}".format(packet.fragment_number))
            print("playload: {}".format(packet.payload))
            return packet

        return str(data)

    def send_response(self, flag, fragment_size=int(
            0).to_bytes(1), fragment_number=int(
            0).to_bytes(1), data=b''):
        packet = bytes([*flag.value.to_bytes(1), *
                       fragment_size, *fragment_number, *data])
        self.sock.sendto(packet, self.client)

    def quit(self):
        self.sock.close()  # correctly closing socket
        print("Server closed..")


if __name__ == "__main__":

    device_type = ''
    # Landing menu, device choice
    while (True):
        print('Choose device')
        user_input = input("client / server :")
        if (user_input == "client" or user_input == "server"):
            device_type = user_input
            break
        else:
            print('Invalid device type use "client" or "server".')
            continue

    # Get server informations since it's same for server and client
    server_ip = input("Server IP (def: 127.0.0.1):")
    server_port = input("Server port (def: 50601):")

    if (server_ip == ''):
        server_ip = "127.0.0.1"

    if (server_port == ''):
        server_port = "50601"
    # Initialize, what device are we using
    if (device_type == 'server'):
        server = Server(server_ip, int(server_port))
        server.serverUp()
    else:
        client = Client(server_ip, int(server_port))
        client.clientUp()
