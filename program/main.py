import socket
SERVER_IP = "127.0.0.1"  # Server host ip (public IP) A.B.C.D
SERVER_PORT = 50601

##### CLIENT #####


class Client:
    def __init__(self, server_ip, server_port) -> None:
        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket creation
        self.server_ip = server_ip
        self.server_port = server_port


    def clientUp(self):
        while data != "End connection message recieved... closing connection":
            print("Input your message: ")
            self.send_message(input())
            data = self.receive()
            print(data)

    def receive(self):
        data = None
        data, self.server = self.sock.recvfrom(1024)
        return str(data, encoding="utf-8")

    def send_message(self, message):
        self.sock.sendto(bytes(message, encoding="utf-8"),
                         (self.server_ip, self.server_port))

    def quit(self):
        self.sock.close()  # correctly closing socket
        print("Client closed..")


##### SERVER #####
class Server:

    def __init__(self, ip, port) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))

    def serviceUp(self):
        data = "empty"
        while data != "End connection":
            if data != "empty":
                self.send_response()
            data = self.receive()

    def receive(self):
        data = None

        while data == None:
            data, self.client = self.sock.recvfrom(1024)
            print("Received message: %s" % data)
            return data

        return str(data, encoding="utf-8")

    def send_response(self):
        self.sock.sendto(
            b"Message received... closing connection", self.client)

    def quit(self):
        self.sock.close()  # correctly closing socket
        print("Server closed..")


if __name__ == "__main__":
    server = Server(SERVER_IP, SERVER_PORT)

    client = Client(CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)

