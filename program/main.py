
import socket
import sys
import math
from threading import Thread
import time
from enum import Enum
import zlib
import random


def to_fragments(data, fragment_size):
    fragments = []
    for i in range(0, math.ceil(len(data)/fragment_size)):
        if (((i+1)*fragment_size % fragment_size) == 0):
            fragments.append(data[i*fragment_size:(i+1)*fragment_size])
        else:
            fragments.append(data[i*fragment_size:])

    return fragments


def recieve_packet(socket):
    data, recieved_from = socket.recvfrom(1500)
    packet = Packet(data)
    return packet, recieved_from


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
        self.packet_without_crc = packet[:-4]
        self.flag = packet[0]
        self.fragment_size = packet[1:3]
        self.fragment_number = packet[3:6]
        self.payload = packet[6:-4]
        self.crc = packet[-4:]


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
        self.send_data(Flag.SYN.value)
        data, self.server = self.sock.recvfrom(1500)
        packet = Packet(data)
        if (packet.flag == Flag.SYN.value):
            print('[i] Connection established')

        while True:
            fragment_size, fragments = handle_inputs()
            for i in range(0, len(fragments)):
                # sending packets 0 => n  but to server in order n => 0 so we know the last packet
                print("sent no. {} with: {}".format(i, fragments[i]))
                if i < len(fragments)-1:
                    self.send_data(flag=Flag.FRAGMENT.value, fragment_size=len(
                        fragments[i]), fragment_number=i, data=fragments[i], can_break=True)
                else:
                    self.send_data(flag=Flag.FINAL_FRAG.value, fragment_size=len(
                        fragments[i]), fragment_number=i, data=fragments[i], can_break=True)

                # sent 5 packets, now check if they were correctly recieved
                if i > 0 and i % 4 == 0 or len(fragments)-1 == i:
                    packets_to_check = fragment_size
                    correct_packets = []
                    while True:
                        data, self.server = self.sock.recvfrom(1500)
                        packet = Packet(data)
                        if (packet.flag == Flag.CORRECT.value):
                            correct_packets.append(packet.fragment_number)
                            print('[i] Packet no.{} send successfully'.format(
                                packet.fragment_number))
                        elif packet.flag == Flag.INCORRECT.value:
                            wrong_packet_no = int.from_bytes(
                                packet.fragment_number)
                            print('[i] Sending packet no.{} again'.format(
                                wrong_packet_no))
                            self.send_data(flag=packet.flag, fragment_size=packet.fragment_size,
                                           fragment_number=packet.fragment_number, data=fragments[int.from_bytes(packet.fragment_number)])
                            continue

                        if (len(correct_packets) == 5):
                            print(
                                '[i] 5 packets send correctly, sending next 5...')
                            break
                        elif len(fragments)-1 == i and (len(correct_packets) == len(fragments) % 5):
                            print('[i] All packets send correctly')
                            break

        self.quit()

    def keep_alive(self):

        while True:
            self.send_data(Flag.KEEP_ALIVE)
            time.sleep(5)

        self.quit()

    def send_data(self, flag, fragment_size=0, fragment_number=0, data=b'', can_break=False):
        if type(fragment_size) == bytes:
            header_with_data = bytes([flag, *fragment_size,
                                      *fragment_number, *data])
        else:
            header_with_data = bytes([flag, *fragment_size.to_bytes(2),
                                      *fragment_number.to_bytes(3), *data])

        crc_value = zlib.crc32(header_with_data)

        if fragment_number == 0 or random.random() < .5 and can_break:
            crc_value += 1

        packet = bytes(
            [*header_with_data, *crc_value.to_bytes(4)])
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
                packet, self.client = recieve_packet(self.sock)
                # print("F: {} S: {} N: {} P: {}".format(packet.flag, packet.fragment_size,
                #                                        int.from_bytes(packet.fragment_number), packet.payload))
                if packet.flag == Flag.FIN.value:
                    break

                if packet.flag == Flag.SYN.value:
                    self.send_message(Flag.SYN)

                if packet.flag == Flag.KEEP_ALIVE.value:
                    self.send_message(Flag.KEEP_ALIVE)

                # first fragment
                if packet.flag == Flag.FRAGMENT.value:
                    packets = []
                    self.validate_packet(packets, packet)
                    # recieve all packets
                    self.sock.settimeout(1)
                    while packet.flag != Flag.FINAL_FRAG.value:
                        try:
                            data, self.client = self.sock.recvfrom(1500)
                            packet = Packet(data)
                            print(int.from_bytes(packet.fragment_number))
                            self.validate_packet(packets, packet)
                            print(packets)
                        except TimeoutError:
                            # if len(packets) > 0:
                            #     self.send_message(
                            #         Flag.INCORRECT, packet.fragment_size, packets[-1].fragment_number + int(1).to_bytes(1))
                            # else:
                            #     self.send_message(
                            #         Flag.INCORRECT, packet.fragment_size, 0)
                            continue

                    self.sock.settimeout(60.0)
                    print('Recieved message: {}'.format(
                        ''.join(list(map(lambda packet: str(packet.payload, encoding='utf-8'), packets)))))

            self.send_message(Flag.FIN)
            self.quit()

        except TimeoutError:
            print('[i] Server timeout...')
            self.quit()

    def send_message(self, flag, fragment_size=0, fragment_number=0, data=b''):
        packet = ''
        if type(fragment_size) == bytes:
            packet = bytes([flag.value, *fragment_size,
                            *fragment_number, *data])
        else:
            packet = bytes([flag.value, *fragment_size.to_bytes(2),
                            *fragment_number.to_bytes(3), *data])

        self.sock.sendto(packet, self.client)

    def validate_packet(self, packets, packet):
        if int.from_bytes(packet.crc) == zlib.crc32(packet.packet_without_crc):
            self.send_message(Flag.CORRECT)
            packets.append(packet)
        else:
            self.send_message(
                Flag.INCORRECT, packet.fragment_size, packet.fragment_size)

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
