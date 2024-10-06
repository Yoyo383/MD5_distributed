import socket
import threading
import protocol

QUEUE_LEN = 1
IP = '0.0.0.0'
PORT = 12345

result = None

total_cores = 0
sockets_cores: dict[socket.socket, int] = {}  # socket: num_of_cores
threads = []

lock = threading.Lock()
barrier: threading.Barrier | None = None  # to make sure that all cores have been counted
found_event = threading.Event()


def thread_main(client_sock):
    """
    Receives commands from the client.
    :param client_sock: The socket.
    :type client_sock: socket.socket
    :return: None.
    """
    global total_cores
    global result

    while not found_event.is_set():
        cmd, arguments = protocol.receive_cmd(client_sock)

        # sent number of cores
        if cmd == protocol.CORES_CMD:
            cores = int(arguments[0])
            with lock:
                sockets_cores[client_sock] = cores
                total_cores += cores
            barrier.wait()

        # client found the answer
        elif cmd == protocol.FOUND_CMD:
            with lock:
                result = arguments[0]

            # notify the main thread
            found_event.set()
            break

        # client did not find the answer
        elif cmd == protocol.ENDED_CMD:
            break


def send_ranges(max_check):
    """
    Sends each client the range they need to check.
    :param max_check: The maximum number to check.
    :type max_check: int
    :return: None.
    """
    with lock:
        range_per_core = max_check // total_cores + 1  # +1 to make sure no rounding errors

    start_range = 0
    for sock, cores in sockets_cores.items():
        end_range = start_range + range_per_core * cores
        protocol.send_cmd(sock, protocol.RANGE_CMD, [str(start_range), str(end_range)])

        start_range += range_per_core * cores


def connect_all_clients(sock, num_of_clients):
    """
    Connects all clients and returns only when no more clients needed.
    :param sock: The socket.
    :type sock: socket.socket
    :param num_of_clients: The number of clients needed.
    :type num_of_clients: int
    :return: None.
    """
    while len(sockets_cores) < num_of_clients:
        print(f'Waiting for {num_of_clients - len(sockets_cores)} clients...')
        client_sock, client_addr = sock.accept()
        with lock:
            sockets_cores[client_sock] = 0

        client_thread = threading.Thread(target=thread_main, args=(client_sock,))
        threads.append(client_thread)
        client_thread.start()


def main():
    """
    The main function.
    :return: None
    """
    global barrier

    target = input('Enter the target to find: ').lower()
    num_of_digits = int(input('Enter the number of digits: '))
    max_check = 10 ** num_of_digits
    num_of_clients = int(input('Enter the number of clients: '))
    barrier = threading.Barrier(num_of_clients + 1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((IP, PORT))
        sock.listen(QUEUE_LEN)

        # connect all clients
        connect_all_clients(sock, num_of_clients)

        barrier.wait()
        send_ranges(max_check)

        print('Starting!')
        protocol.broadcast_cmd(list(sockets_cores.keys()), protocol.START_CMD, [target])

        # wait for the result
        while not found_event.is_set():
            pass

        print(f'Result is {result}')

        # tell all clients to stop.
        protocol.broadcast_cmd(list(sockets_cores.keys()), protocol.ENDED_CMD, [])
        for t in threads:
            t.join()

        for client_sock in sockets_cores:
            client_sock.close()

    except socket.error as err:
        print('Server socket error: ', err)

    finally:
        sock.close()


if __name__ == '__main__':
    main()
