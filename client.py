import os
import socket
import threading
import protocol
import hashlib
import multiprocessing

IP = '127.0.0.1'
PORT = 12345

CORES = os.cpu_count()


def range_generator(range_start, range_end):
    """
    Yields the range for each core.
    :param range_start: The start of the range.
    :type range_start: int
    :param range_end: The end of the range.
    :type range_end: int
    :return: A generator of tuples (start, end) for each core.
    """
    range_per_core = (range_end - range_start) // CORES + 1  # +1 to make sure no rounding errors
    for i in range(CORES):
        yield range_start, range_start + range_per_core
        range_start += range_per_core


def check_for_answer(target, range_start, range_end, found_event):
    """
    Checks for the answer in a given range.
    :param target: The target hash to be found.
    :type target: str
    :param range_start: The start of the range.
    :type range_start: int
    :param range_end: The end of the range.
    :type range_end: int
    :param found_event: The event that tells if the result was found.
    :return: The result if it was found in the range, else None.
    :rtype: int | None
    """
    print(f'Checking range {range_start}-{range_end}...')
    result = None

    for num in range(range_start, range_end):
        # if another process found the answer then stop
        if found_event.is_set():
            break

        test = hashlib.md5(str(num).encode()).hexdigest()
        if target == test:
            # set the event so other processes stop
            found_event.set()
            result = num
            break

    print(f'In range {range_start}-{range_end} found {result} {':(' if result is None else ':)'}')
    return result


def calculate_answer(sock, target, range_start, range_end, found_event):
    """
    Splits the range given by the server to each core and gets an answer.
    :param sock: The socket.
    :type sock: socket.socket
    :param target: The target hash to be found.
    :type target: str
    :param range_start: The start of the range.
    :type range_start: int
    :param range_end: The end of the range.
    :type range_end: int
    :param found_event: The event that tells if the result was found.
    :return: None.
    """
    result = None

    # uses each core
    with multiprocessing.Pool(CORES) as pool:
        parameters = [(target, check[0], check[1], found_event) for check in range_generator(range_start, range_end)]
        results = pool.starmap(check_for_answer, parameters)

    for res in results:
        if res is not None:
            print(f'Found answer: {res}')
            result = res
            break

    # sends correct command
    if result is not None:
        protocol.send_cmd(sock, protocol.FOUND_CMD, [str(result)])
    else:
        protocol.send_cmd(sock, protocol.ENDED_CMD, [])


def thread_socket(sock, found_event):
    """
    Listens for a command from the socket.
    :param sock: The socket.
    :type sock: socket.socket
    :param found_event: The event that tells if the result was found.
    :return: None.
    """
    cmd, arguments = protocol.receive_cmd(sock)
    if cmd == protocol.ENDED_CMD and not found_event.is_set():
        print('Another client found the answer, exiting...')
        found_event.set()


def receive_range(sock):
    """
    Receives the range from the server.
    :param sock: The socket.
    :type sock: socket.socket
    :return: A tuple representing the range (start, end). If received incorrect command, returns (None, None).
    :rtype: tuple[int, int]
    """
    cmd, arguments = protocol.receive_cmd(sock)
    if cmd != protocol.RANGE_CMD:
        print(f'Expected RANGE command, instead got {cmd} command. Aborts.')
        return None, None

    range_start = int(arguments[0])
    range_end = int(arguments[1])
    return range_start, range_end


def receive_start(sock):
    """
    Receives the start command and the target.
    :param sock: The socket.
    :type sock: socket.socket
    :return: The target. If received incorrect command, returns None.
    :rtype: str
    """
    cmd, arguments = protocol.receive_cmd(sock)
    if cmd != protocol.START_CMD:
        print(f'Expected START command, instead got {cmd} command. Aborts.')
        return None

    return arguments[0]


def main():
    """
    The main function.
    :return: None.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((IP, PORT))
        protocol.send_cmd(sock, protocol.CORES_CMD, [str(CORES)])

        print('Waiting for server...')

        # receive range command
        range_start, range_end = receive_range(sock)
        if range_start is None:
            return
        print(f'Received range {range_start}-{range_end}.')

        # receive start command
        target = receive_start(sock)
        if target is None:
            return
        print(f'Received target {target}')

        with multiprocessing.Manager() as manager:
            # create the event
            found_event = manager.Event()

            # create the socket thread
            socket_thread = threading.Thread(target=thread_socket, args=(sock, found_event))
            socket_thread.start()

            print('Starting!')
            calculate_answer(sock, target, range_start, range_end, found_event)

            socket_thread.join()

    except socket.error as err:
        print('Client socket error: ', err)

    finally:
        sock.close()


if __name__ == '__main__':
    print('Starting tests...')

    hash_of_712 = '19bc916108fc6938f52cb96f7e087941'
    test_712 = check_for_answer(hash_of_712, 500, 1000, multiprocessing.Event())
    assert test_712 == 712

    hash_of_123456 = 'e10adc3949ba59abbe56e057f20f883e'
    test_123456 = check_for_answer(hash_of_123456, 100000, 200000, multiprocessing.Event())
    assert test_123456 == 123456

    print('Tests successful!')

    main()
