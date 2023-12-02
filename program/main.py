
import socket
import sys
import math
from threading import Thread
import time
import signal
import sys
from enum import Enum
import zlib
import random


FIN = 1
SYN = 2
FILE_NAME_FRAGMENT = 3
MESSAGE_FRAGMENT = 4
FINAL_MESSAGE_FRAGMENT = 5
FILE_FRAGMENT = 6
FINAL_FILE_FRAGMENT = 7
CORRECT = 8
INCORRECT = 9
KEEP_ALIVE = 10
ROLE_SWITCH = 11
FINAL_FILE_NAME_FRAGMENT = 12

CONNECTION_ERROR = 'Connection error'
SWITCH = 'Switch roles'
CLOSE_CONNECTION = 'Close connection'
SWITCH = 'Switch roles'


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
    fragment_size = ''
    fragments = []
    while True:
        print("[x] Select option for sending")
        print("[1] Sending Message")
        print("[2] Sending File")
        print("[3] Switch roles")
        sending_method = input()
        if sending_method in ["1", "2", "3", "4"]:
            break
        else:
            print('[i] Invalid method selected!')
            continue

    if sending_method in ["1", "2"]:
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
        file_name = bytes(file_path, encoding='utf-8')
        fragments = {}
        fragments['path'] = to_fragments(file_name, fragment_size)
        fragments['file'] = to_fragments(file_data, fragment_size)

    return fragment_size, fragments, sending_method


class Client:
    def __init__(self, server_ip, server_port) -> None:
        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket creation
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock.settimeout(5)
        self.connection_retries = 0
        self.keep_alive_retries = 0
        self.keep_alive_on = True
        self.not_terminated = True
        self.keep_alive_thread = Thread(target=self.keep_alive)
        print('[i] Client created... (IP: {} )'.format(
            ':'.join([server_ip, str(server_port)])))

    def clientUp(self):
        data = None
        # [i] Initializing connection with server
        print('[i] Initializing connection with server...')

        connection_established = False
        while not connection_established:
            try:
                self.send_data(SYN)
                data, self.server = self.sock.recvfrom(1500)
                packet = Packet(data)
                self.connection_retries = 0
                if (packet.flag == SYN):
                    print('[i] Connection established')
                    connection_established = True
            except TimeoutError:
                if self.connection_retries == 10:
                    return "connection not established after 50s"

        self.keep_alive_thread.start()

        while True:
            self.keep_alive_on = True
            fragment_size, fragments, sending_method = handle_inputs()
            self.keep_alive_on = False

            if sending_method == "1":  # sending message
                value = self.sending_cycle(
                    MESSAGE_FRAGMENT, FINAL_MESSAGE_FRAGMENT, fragments)
                if value == CLOSE_CONNECTION:
                    return CLOSE_CONNECTION

            elif sending_method == "2":  # sending file
                value1 = self.sending_cycle(FILE_NAME_FRAGMENT,
                                            FINAL_FILE_NAME_FRAGMENT, fragments['path'])

                value2 = self.sending_cycle(FILE_FRAGMENT,
                                            FINAL_FILE_FRAGMENT, fragments['file'])

                if value1 == CLOSE_CONNECTION or value2 == CLOSE_CONNECTION:
                    return CLOSE_CONNECTION

            elif sending_method == "3":  # switching role
                self.send_data(flag=ROLE_SWITCH)
                # wait for ACK
                while True:
                    try:
                        data, self.server = self.sock.recvfrom(1500)
                        response = Packet(data)
                        self.keep_alive_retries = 0
                        print('Packet flag: {}  {}'.format(
                            response.flag, CORRECT))
                        return SWITCH
                    except TimeoutError:
                        if (self.keep_alive_retries == 10):
                            self.keep_alive_on = False
                            self.keep_alive_thread.join()
                            print(
                                'Response not received 10 times, closing connection')
                            return CLOSE_CONNECTION
                        self.keep_alive_retries += 1
                        time.sleep(5)

            elif sending_method == "4":
                self.send_data(flag=FIN)
                return 'End'

    def keep_alive(self):
        self.sock.settimeout(5)
        while self.not_terminated:
            while self.keep_alive_on:
                try:
                    self.send_data(KEEP_ALIVE)
                    data, self.server = self.sock.recvfrom(1500)
                    response = Packet(data)
                    self.keep_alive_retries = 0
                    time.sleep(5)
                except TimeoutError:
                    if (self.keep_alive_retries == 5):
                        self.keep_alive_on = False
                        self.keep_alive_thread.join()
                        print('Keep alive not received 5 times, closing connection')
                        self.quit()
                        return
                    self.keep_alive_retries += 1
                    time.sleep(5)

    def sending_cycle(self, body_flag, final_flag, fragments):
        for i in range(0, len(fragments)):
            print("sent no. {} with: {}".format(i, fragments[i]))
            if i < len(fragments)-1:
                self.send_data(flag=body_flag, fragment_size=len(
                    fragments[i]), fragment_number=i, data=fragments[i], can_break=True)
            else:
                self.send_data(flag=final_flag, fragment_size=len(
                    fragments[i]), fragment_number=i, data=fragments[i], can_break=True)

            # wait for ACK
            while True:
                try:
                    data, self.server = self.sock.recvfrom(1500)
                    response = Packet(data)
                    self.keep_alive_retries = 0
                    print('Packet flag: {}  {}'.format(
                        response.flag, CORRECT))
                    # if valid, dont send again
                    if response.flag == CORRECT:
                        break

                    flag = body_flag if int.from_bytes(
                        response.fragment_number) < len(fragments)-1 else final_flag
                    print('Sending again no.{}'.format(
                        int.from_bytes(response.fragment_number)))
                    self.send_data(flag, fragment_size=len(
                        fragments[i]), fragment_number=i, data=fragments[i])
                except TimeoutError:
                    if (self.keep_alive_retries == 5):
                        self.keep_alive_on = False
                        self.keep_alive_thread.join()
                        print('Keep alive not received 5 times, closing connection')
                        self.quit()
                        return CLOSE_CONNECTION
                    self.keep_alive_retries += 1
                    tiem.sleep(5)

    def send_data(self, flag, fragment_size=0, fragment_number=0, data=b'', can_break=False):
        if type(fragment_size) == bytes:
            header_with_data = bytes([flag, *fragment_size,
                                      *fragment_number, *data])
        else:
            header_with_data = bytes([flag, *fragment_size.to_bytes(2),
                                      *fragment_number.to_bytes(3), *data])

        crc_value = zlib.crc32(header_with_data)

        if can_break and (fragment_number == 0 or random.random() < .5):
            crc_value += 1

        packet = bytes(
            [*header_with_data, *crc_value.to_bytes(4)])
        self.sock.sendto(packet, (self.server_ip, self.server_port))

    def quit(self):
        self.not_terminated = False
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
        correct_packets = []
        filename_packets = []
        filename = ''
        file_packets = []

        self.sock.settimeout(60.0)
        try:
            while True:
                packet, self.client = recieve_packet(self.sock)

                if packet.flag == ROLE_SWITCH:
                    self.send_message(CORRECT)
                    return SWITCH

                if packet.flag == FIN:
                    return 'End'

                if packet.flag == SYN:
                    self.send_message(SYN)

                if packet.flag == KEEP_ALIVE:
                    print("keep alive recieved")
                    self.send_message(KEEP_ALIVE)

                ############# MESSAGE TRANSFER #########################
                if packet.flag == MESSAGE_FRAGMENT:
                    self.check_crc(correct_packets, packet)

                if packet.flag == FINAL_MESSAGE_FRAGMENT:
                    is_valid = self.check_crc(correct_packets, packet)
                    print('is last valid: {}'.format(is_valid))
                    if (is_valid):

                        print('Recieved message: {}'.format(
                            ''.join(list(map(lambda packet: str(packet.payload, encoding='utf-8'), correct_packets)))))

                ############# FILE NAME TRANSFER #########################

                if packet.flag == FILE_NAME_FRAGMENT:
                    self.check_crc(filename_packets, packet)

                if packet.flag == FINAL_FILE_NAME_FRAGMENT:
                    is_valid = self.check_crc(filename_packets, packet)
                    print('is last valid: {}'.format(is_valid))
                    if (is_valid):
                        filename = ''.join(list(map(lambda packet: str(
                            packet.payload, encoding='utf-8'), filename_packets)))
                        print('Filename: {}'.format(filename))

                ############# FILE TRANSFER #########################

                if packet.flag == FILE_FRAGMENT:
                    self.check_crc(file_packets, packet)

                if packet.flag == FINAL_FILE_FRAGMENT:
                    is_valid = self.check_crc(file_packets, packet)
                    print('is last valid: {}'.format(is_valid))
                    if (is_valid):
                        file = open("./received/{}".format(filename), 'wb')
                        file.write(
                            bytes(b"".join(list(map(lambda packet: packet.payload, file_packets)))))
                        file.close()
                        ## reset variables ##
                        filename = ""
                        filename_packets = []
                        file_packets = []

        except TimeoutError:
            print('[i] Server timeout...')
            return 'End'

    def check_crc(self, correct_packets, packet):
        if packet.crc == zlib.crc32(packet.packet_without_crc).to_bytes(4):
            print('Packet no.{} valid'.format(
                int.from_bytes(packet.fragment_number)))
            correct_packets.append(packet)
            self.send_message(
                CORRECT, fragment_size=packet.fragment_size, fragment_number=packet.fragment_number)
            return True

        else:
            print('Packet no.{} !NOT! valid'.format(
                int.from_bytes(packet.fragment_number)))
            self.send_message(
                INCORRECT, fragment_size=packet.fragment_size, fragment_number=packet.fragment_number)

        return False

    def send_message(self, flag, fragment_size=0, fragment_number=0, data=b''):
        packet = ''
        if type(fragment_size) == bytes:
            packet = bytes([flag, *fragment_size,
                            *fragment_number, *data])
        else:
            packet = bytes([flag, *fragment_size.to_bytes(2),
                            *fragment_number.to_bytes(3), *data])

        self.sock.sendto(packet, self.client)

    def quit(self):
        self.sock.close()  # correctly closing socket
        print("Server closed...")


if __name__ == "__main__":

    device_type = ''
    server_ip = ''
    server_port = ''
    returned_state = ''

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

    while returned_state != 'End':
        # Get server informations since it's same for server and client
        if (returned_state == '' or returned_state == CONNECTION_ERROR):
            server_ip = input("Server IP (def: 127.0.0.1):")
            server_port = input("Server port (def: 50601):")

            if (server_ip == ''):
                server_ip = "127.0.0.1"

            if (server_port == ''):
                server_port = "50601"
        # Initialize, what device are we using

        if returned_state == SWITCH:
            if device_type == 'server':
                device_type = 'client'
            else:
                device_type = 'server'

        if device_type == 'server':
            server = Server(server_ip, int(server_port))
            returned_state = server.serverUp()
            server.quit()
        else:
            client = Client(server_ip, int(server_port))
            returned_state = client.clientUp()
            client.quit()
