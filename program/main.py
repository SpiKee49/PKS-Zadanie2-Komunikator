
import socket
import sys
from threading import Thread
import time


def to_fragments(data, fragment_size):
    fragments = []
    for i in range(0, len(data)//fragment_size):
        if ((i+1)*fragment_size % fragment_size):
            fragments.append(data[i*fragment_size:(i+1)*fragment_size])
        else:
            fragments.append(data[i*fragment_size:])

    return fragments


class Packet:
    def __init__(self, packet: bytes) -> None:
        self.flag = packet[0]
        self.id = packet[1]
        self.fragment_size = packet[2:4]
        self.fragment_number = packet[4:7]
        self.payload = packet[7:-4]


##### CLIENT #####


def handle_inputs():
    sending_method = ''
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

    while fragment_size <= 0 or fragment_size > 1461:
        print('Size of fragment has to be from interval 0 < x  <= 1461')
        fragment_size = input("Provide fragment size(def. 1461): ")

    # sending message
    if sending_method == 1:
        print('Your message:\n')
        message = input()
        data = bytes(message)
        fragments = to_fragments(data, fragment_size)
    # sending file
    elif sending_method == 2:
        print('File path:\n')
        file_path = input()
        file = open(file_path, 'rb')
        file_data = file.read()
        file.close()
        fragments = [bytes(file_path), *to_fragments(file_data)]

    return fragments


class Client:
    def __init__(self, server_ip, server_port) -> None:
        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket creation
        self.server_ip = server_ip
        self.server_port = server_port
        print('[i] Client created... (IP: {} )'.format(
            ':'.join([server_ip, str(server_port)])))

    def clientUp(self):
        data = None
        keep_alive_thread = Thread(target=self.keep_alive).start()

        # [i] Initializing connection with server
        print('[i] Initializing connection with server...')
        self.send_data(b'SYN')
        data = self.receive()
        if (data == 'SYN ACK'):
            print('[i] Connection established')
            keep_alive_thread.run()

        while data != "Server closing connection":
            fragments = handle_inputs()

            for fragment in fragments:
                self.send_data(fragment)

            data = self.receive()
            print(data)

        self.quit()

    def keep_alive(self):
        self.sock.settimeout(30.0)
        try:
            while True:
                self.send_data(b'Keep Alive')
                time.sleep(5)
        except TimeoutError:
            self.quit()

    def receive(self):
        data = None
        data, self.server = self.sock.recvfrom(1500)
        return str(data, encoding="utf-8")

    def send_data(self, data):
        self.sock.sendto(data, (self.server_ip, self.server_port))

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
                print('data: {} typeof: {}'.format(data, type(data)))
                if data == "End":
                    break
                if data == "SYN":
                    self.send_response('SYN ACK')

                if data == 'Keep Alive':
                    self.send_response('Keep Alive ACK')

                if data != "empty":
                    self.send_response('ACK')

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
            print("Received message: %s" % data)
            return str(data, encoding='utf-8')

        return str(data)

    def send_response(self, message):
        self.sock.sendto(bytes(message, encoding="utf-8"), self.client)

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
