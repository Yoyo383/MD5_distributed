"""
protocol: COMMAND:arg1,arg2,...;
COMMAND is 5 letters - START, CORES, FOUND, RANGE, ENDED
"""
import socket

START_CMD = 'START'  # Server sends to clients to start, argument is the target hash
CORES_CMD = 'CORES'  # Clients send to server, argument is number of cores
FOUND_CMD = 'FOUND'  # Clients send to server, argument is the found number
RANGE_CMD = 'RANGE'  # Server sends to clients, arguments are the start and end of the range
ENDED_CMD = 'ENDED'  # Can be sent both from the client and from the server, no arguments


def receive_cmd(sock):
    """
    Receives a command and its arguments from the socket.
    :param sock: The socket.
    :type sock: socket.socket
    :return: A tuple with the command and a list of the arguments.
    :rtype: tuple[str, list[str]]
    """
    # get command
    cmd = sock.recv(5).decode()
    arguments = []

    # colon
    sock.recv(1)

    # get arguments
    cur_byte = sock.recv(1).decode()
    current_arg = ''
    while cur_byte != ';':
        if cur_byte == ',':
            arguments.append(current_arg)
            current_arg = ''
        else:
            current_arg += cur_byte

        cur_byte = sock.recv(1).decode()

    if current_arg != '':
        arguments.append(current_arg)

    return cmd, arguments


def send_cmd(sock, cmd, arguments):
    """
    Sends a command through the socket.
    :param sock: The socket.
    :type sock: socket.socket
    :param cmd: The command to send.
    :type cmd: str
    :param arguments: The arguments for the command.
    :type arguments: list[str | None]
    :return: None.
    """
    message = cmd + ':' + ','.join(arguments) + ';'
    sock.send(message.encode())


def broadcast_cmd(sockets, cmd, arguments):
    """
    Broadcasts a command.
    :param sockets: The list of the sockets to send.
    :type sockets: list[socket.socket]
    :param cmd: The command to send.
    :type cmd: str
    :param arguments: The arguments for the command.
    :type arguments: list[str]
    :return: None.
    """
    for sock in sockets:
        send_cmd(sock, cmd, arguments)
