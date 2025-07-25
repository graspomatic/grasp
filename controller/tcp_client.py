import socket


def sendReq(message):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ('localhost', 8888)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)

    try:

        # Send data
        #message = b'?function=retrieve&id=13&side=0'
        # message = b'?function=put_away&side=0'
        print('sending {!r}'.format(message))
        sock.sendall(str.encode(message))

        # Look for the response
        amount_received = 0
        amount_expected = 1

        while amount_received < amount_expected:
            data = sock.recv(32)
            amount_received += len(data)
            print('received {!r}'.format(data))

    finally:
        print('closing socket')
        sock.close()