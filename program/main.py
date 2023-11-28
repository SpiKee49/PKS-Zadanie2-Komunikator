
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
        self.payload = packet[6:]


##### CLIENT #####

def handle_inputs():
    sending_method = ''
    fragments = []
    while True:
        print("[x] Select option for sending")
        print("[1] Sending Message")
        print("[2] Sending File")
        sending_method = input()
        if sending_method in ["1", "2"]:
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
        print('Your message:')
        message = input()
        data = bytes(message, encoding='utf-8')
        fragments = to_fragments(data, fragment_size)
    # sending file
    elif sending_method == "2":
        print('File path:')
        file_path = input()
        file = open(file_path, 'rb')
        file_data = file.read()
        file.close()
        # TODO: separate fragments for path and file
        fragments = [*to_fragments(file_path, fragment_size),
                     *to_fragments(file_data, fragment_size)]

    return fragment_size, fragments


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
        self.send_data(Flag.SYN)
        data, self.server = self.sock.recvfrom(1500)
        packet = Packet(data)
        if (packet.flag == Flag.SYN.value):
            print('[i] Connection established')

        while True:
            fragment_size, fragments = handle_inputs()
            for i in range(0, len(fragments)):
                # sending packets 0 => n  but to server in order n => 0 so we know the last packet
                print("sent no. {} with: {}".format(i, fragments[i]))
                self.send_data(flag=Flag.FRAGMENT, fragment_size=len(fragments[i]), fragment_number=(
                    len(fragments)-1-i), data=fragments[i])

                # # sent 5 packets, now check if they were correctly recieved
                # if i > 0 and i % 5 == 0 or len(fragments)-1 == i:
                #     correct_packets = []
                #     while True:
                #         data, self.server = self.sock.recvfrom(1500)
                #         packet = Packet(data)
                #         if (packet.flag == Flag.CORRECT.value):
                #             correct_packets.append(packet.fragment_number)
                #             print('[i] Packet no.{} send successfully'.format(
                #                 packet_index))
                #         elif packet.flag == Flag.INCORRECT.value:
                #             packet_index = len(fragments) - \
                #                 1 - packet.fragment_number
                #             print('[i] Sending packet no.{} again'.format(
                #                 packet_index))
                #             self.send_data(flag=Flag.FRAGMENT, fragment_size=fragment_size,
                #                            fragment_number=packet_index, data=fragments[packet_index])
                #             continue

                #         if (len(correct_packets) == 5):
                #             print(
                #                 '[i] 5 packets send correctly, sending next 5...')
                #             break

            data, self.server = self.sock.recvfrom(1500)
            packet = Packet(data)
            if (packet.flag == Flag.FIN.value):
                self.send_data(flag.FIN)
                break

        self.quit()

    def keep_alive(self):

        while True:
            self.send_data(Flag.KEEP_ALIVE)
            time.sleep(5)

        self.quit()

    def send_data(self, flag, fragment_size=0, fragment_number=0, data=b''):
        packet = bytes([flag.value, *fragment_size.to_bytes(2),
                       *fragment_number.to_bytes(3), *data])
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
        self.sock.settimeout(60.0)
        try:
            while True:
                data, self.client = self.sock.recvfrom(1500)
                packet = Packet(data)
                print("F: {} S: {} N: {} P: {}".format(packet.flag, packet.fragment_size,
                                                       packet.fragment_number, packet.payload))
                if packet == "End":
                    break

                if packet.flag == Flag.SYN.value:
                    self.send_response(Flag.SYN)

                if packet.flag == Flag.KEEP_ALIVE.value:
                    self.send_response(Flag.KEEP_ALIVE)

                if packet.flag == Flag.FRAGMENT.value:
                    self.send_response(Flag.CORRECT)

            self.send_response(Flag.FIN)
            self.quit()

        except TimeoutError:
            print('[i] Server timeout...')
            self.quit()

    def send_response(self, flag, fragment_size=0, fragment_number=0, data=b''):
        packet = bytes([flag.value, *fragment_size.to_bytes(2),
                       *fragment_number.to_bytes(3), *data])
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
