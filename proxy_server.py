import concurrent.futures
import socket
import urllib.parse

from configs import config

DEFAULT_HTTP_PORT = 80
HTTP_LINEBREAK = '\r\n'
DOUBLE_LINEBREAK = b'\r\n\r\n'


class Server:

    def __init__(self):
        self.buffer_length = config['BUFFER_LENGTH']

        # Create a TCP socket
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Re-use the socket
        self.listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

        # bind the socket to a public host, and a port
        self.listening_socket.bind((config['HOST_NAME'], config['BIND_PORT']))

        self.listening_socket.listen(socket.SOMAXCONN)  # become a server socket

        self.__clients = set()

        self.executor = concurrent.futures.ThreadPoolExecutor()

    def start(self):
        while True:
            # Establish the connection
            client_conn, client_addr = self.listening_socket.accept()

            self.__clients.add(client_addr[0])

            self.executor.submit(self.handle, client_conn, client_addr)

    def handle(self, client_conn, client_addr):
        url = None

        try:
            first_chunk = client_conn.recv(self.buffer_length)

            url = self.parse_url(first_chunk)

            self.forward(url, first_chunk, client_conn, client_addr)

        except Exception as e:
            url_str = url.geturl() if url else None
            print(url_str, e)

    def forward(self, url, first_chunk, client_conn, client_addr):
        address = (url.hostname, url.port or DEFAULT_HTTP_PORT)

        with socket.create_connection(address) as sock:

            chunk = first_chunk

            while True:
                sock.sendall(chunk)
                if chunk.endswith(DOUBLE_LINEBREAK):
                    break
                chunk = client_conn.recv(self.buffer_length)

            while True:
                # receive data from web server
                response = sock.recv(self.buffer_length)
                if len(response) == 0:
                    break
                client_conn.sendall(response)  # send to browser/client

    @staticmethod
    def parse_url(first_chunk):
        first_chunk_str = first_chunk.decode()

        first_line = first_chunk_str[:first_chunk_str.index(HTTP_LINEBREAK)]

        url_str = first_line.split(' ')[1]

        url = urllib.parse.urlparse(url_str)

        return url
