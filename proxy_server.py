import socket
import threading
import traceback
import urllib.parse

from configs import config

DEFAULT_HTTP_PORT = 80
DEFAULT_HTTPS_PORT = 443
CR_LF = '\r\n'
CONNECTION_ESTABLISHED = b'HTTP/1.1 200 Connection established\r\n\r\n'
IGNORED_ERROR_TYPES = (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError, TimeoutError)


class Proxy:

    def __init__(self):
        self.buffer_length = config['BUFFER_LENGTH']

        # Create a TCP socket
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Re-use the socket
        self.listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

        # Bind the socket to a public host, and a port
        self.listening_socket.bind((config['HOST_NAME'], config['BIND_PORT']))

        self.listening_socket.listen(socket.SOMAXCONN)  # become a server socket

        self.__clients = set()

    def start(self):
        while True:
            # Establish the connection
            client_conn, client_addr = self.listening_socket.accept()

            self.__clients.add(client_addr[0])

            threading.Thread(target=self.try_handle, args=(client_conn, client_addr)).start()

    def try_handle(self, client_conn, client_addr):
        url = None

        try:
            self.handle(client_conn, client_addr)

        except IGNORED_ERROR_TYPES:
            pass
        except:
            url_str = url.geturl() if url else None
            print(url_str)
            traceback.print_exc()

    def handle(self, client_conn, client_addr):
        request = client_conn.recv(self.buffer_length)

        if not request:
            return

        method, address = self.parse_method_and_address(request)

        with socket.create_connection(address) as server_conn:
            if method == 'CONNECT':
                client_conn.sendall(CONNECTION_ESTABLISHED)
                threading.Thread(target=self.try_forward, args=(server_conn, client_conn)).start()

            else:
                threading.Thread(target=self.try_forward, args=(server_conn, client_conn)).start()
                server_conn.sendall(request)

            self.forward(client_conn, server_conn)

    def try_forward(self, source, target):
        try:
            self.forward(source, target)

        except IGNORED_ERROR_TYPES:
            pass
        except:
            traceback.print_exc()

    def forward(self, source, target):
        while True:
            # Receive data from source
            response = source.recv(self.buffer_length)

            if not response:
                break

            # Forward to target
            target.sendall(response)

    @staticmethod
    def parse_method_and_address(request):
        method, url = Proxy.parse_method_and_url(request)

        port = url.port or Proxy.get_default_port(url.scheme)
        address = (url.hostname, port)

        return method, address

    @staticmethod
    def parse_method_and_url(request):
        request_str = request.decode()

        first_line = request_str[:request_str.index(CR_LF)]

        method, url_str = first_line.split(' ')[:2]

        if '://' not in url_str:
            url_str = '//' + url_str

        url = urllib.parse.urlparse(url_str)

        return method, url

    @staticmethod
    def get_default_port(scheme):
        if not scheme or scheme == 'http':
            return DEFAULT_HTTP_PORT

        if scheme == 'https':
            return DEFAULT_HTTPS_PORT
