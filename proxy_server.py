import socket
import threading
import ssl

from configs import config


class Server:

    def __init__(self):

        # Create a TCP socket
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Re-use the socket
        self.listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # bind the socket to a public host, and a port
        self.listening_socket.bind((config['HOST_NAME'], config['BIND_PORT']))

        self.listening_socket.listen(5)  # become a server socket
        self.__clients = set()

    def start(self):
        while True:
            # Establish the connection
            (client_socket, client_addr) = self.listening_socket.accept()
            self.__clients.add(client_addr[0])

            t = threading.Thread(name=client_addr[1],
                                 target=self.connect_client, args=(client_socket, client_addr))
            t.start()

    def connect_client(self, client_conn, client_addr):
        data = client_conn.recv(config['MAX_REQUEST_LEN'])

        first_line = data.decode().split('\n')[0]

        url = first_line.split(' ')[1]

        http_pos = url.find("://")  # find pos of ://

        tmp = url if http_pos == -1 else url[(http_pos + 3):]

        port_pos = tmp.find(":")  # find the port pos (if any)

        # find end of web server
        webserver_pos = tmp.find("/")
        webserver_pos = len(tmp) if webserver_pos == -1 else webserver_pos

        webserver = ""
        port = -1
        if port_pos == -1 or webserver_pos < port_pos:
            # default port
            port = 80
            webserver = tmp[:webserver_pos]

        else:  # specific port
            port = int((tmp[(port_pos + 1):])[:webserver_pos - port_pos - 1])
            webserver = tmp[:port_pos]

        self.request(webserver, port, data, client_conn, client_addr)

    def request(self, webserver, port, data, client_conn, client_addr):
        context = ssl.create_default_context()
        with socket.create_connection((webserver, port)) as sock:
            with context.wrap_socket(sock, server_hostname=webserver) as ssock:
                ssock.sendall(data)

                while True:
                    # receive data from web server
                    response = ssock.recv(config['MAX_REQUEST_LEN'])

                    if len(response) > 0:
                        client_conn.sendall(response)  # send to browser/client
                    else:
                        break

                ssock.shutdown(socket.SHUT_RDWR)
