#!/usr/bin/python3
"""Implementation of RDT3.0

functions: rdt_network_init(), rdt_socket(), rdt_bind(), rdt_peer()
           rdt_send(), rdt_recv(), rdt_close()

Student name: ZHOU Jingran
Student No. : 3035232468
Date and version: 10 Mar - Version 1
Development platform: macOS High Sierra (Version 10.13.3)
Python version: Python 3.6.3
"""

import socket
import random
import struct
import select

# some constants
PAYLOAD = 1000  # size of data payload of the RDT layer
CPORT = 100  # Client port number - Change to your port number
SPORT = 200  # Server port number - Change to your port number
TIMEOUT = 0.05  # retransmission timeout duration
TWAIT = 10 * TIMEOUT  # TimeWait duration
TYPE_DATA = 12  # 12 means data
TYPE_ACK = 11  # 11 means ACK
MSG_FORMAT = 'B?HH'  # Format string for header structure
HEADER_SIZE = 6  # 6 bytes

# store peer address info
__peeraddr = ()  # set by rdt_peer()

# define the error rates
__LOSS_RATE = 0.0  # set by rdt_network_init()
__ERR_RATE = 0.0

# Data buffer
__data_buffer = []

# Packet sequence number
__send_seq_num = 0
__recv_seq_num = 0


# internal functions - being called within the module
def __udt_send(sockd, peer_addr, byte_msg):
    """This function is for simulating packet loss or corruption in an unreliable channel.

    Input arguments: Unix socket object, peer address 2-tuple and the message
    Return  -> size of data sent, -1 on error
    Note: it does not catch any exception
    """
    global __LOSS_RATE, __ERR_RATE
    if peer_addr == ():
        print("Socket send error: Peer address not set yet")
        return -1
    else:
        # Simulate packet loss
        drop = random.random()
        if drop < __LOSS_RATE:
            # simulate packet loss of unreliable send
            print("WARNING: udt_send: Packet lost in unreliable layer!!")
            return len(byte_msg)

        # Simulate packet corruption
        corrupt = random.random()
        if corrupt < __ERR_RATE:
            err_bytearr = bytearray(byte_msg)
            pos = random.randint(0, len(byte_msg) - 1)
            val = err_bytearr[pos]
            if val > 1:
                err_bytearr[pos] -= 2
            else:
                err_bytearr[pos] = 254
            err_msg = bytes(err_bytearr)
            print("WARNING: udt_send: Packet corrupted in unreliable layer!!")
            return sockd.sendto(err_msg, peer_addr)
        else:
            return sockd.sendto(byte_msg, peer_addr)


def __udt_recv(sockd, length):
    """Retrieve message from underlying layer

    Input arguments: Unix socket object and the max amount of data to be received
    Return  -> the received bytes message object
    Note: it does not catch any exception
    """
    (rmsg, peer) = sockd.recvfrom(length)
    return rmsg


def ___int_chksum(byte_msg):
    """Implement the Internet Checksum algorithm

    Input argument: the bytes message object
    Return  -> 16-bit checksum value
    Note: it does not check whether the input object is a bytes object
    """
    total = 0
    length = len(byte_msg)  # length of the byte message object
    i = 0
    while length > 1:
        total += ((byte_msg[i + 1] << 8) & 0xFF00) + ((byte_msg[i]) & 0xFF)
        i += 2
        length -= 2

    if length > 0:
        total += (byte_msg[i] & 0xFF)

    while (total >> 16) > 0:
        total = (total & 0xFFFF) + (total >> 16)

    total = ~total

    return total & 0xFFFF


# These are the functions used by application

def rdt_network_init(drop_rate, err_rate):
    """Application calls this function to set properties of underlying network.

    Input arguments: packet drop probability and packet corruption probability
    """
    random.seed()
    global __LOSS_RATE, __ERR_RATE
    __LOSS_RATE = float(drop_rate)
    __ERR_RATE = float(err_rate)
    print("Drop rate:", __LOSS_RATE, "\tError rate:", __ERR_RATE)


def rdt_socket():
    """Application calls this function to create the RDT socket.

    Null input.
    Return the Unix socket object on success, None on error

    Note: Catch any known error and report to the user.
    """
    # Your implementation
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as err_msg:
        print("Socket creation error: ", err_msg)
        return None
    return sock


def rdt_bind(sockd, port):
    """Application calls this function to specify the port number
    used by itself and assigns them to the RDT socket.

    Input arguments: RDT socket object and port number
    Return	-> 0 on success, -1 on error

    Note: Catch any known error and report to the user.
    """
    # Your implementation
    try:
        sockd.bind(("", port))
    except socket.error as err_msg:
        print("Socket bind error: ", err_msg)
        return -1
    return 0


def rdt_peer(peer_ip, port):
    """Application calls this function to specify the IP address
    and port number used by remote peer process.

    Input arguments: peer's IP address and port number
    """
    # Your implementation
    global __peeraddr
    __peeraddr = (peer_ip, port)


def __make_data(seq_num, data):
    """Make DATA [seq_num].

    Input arguments: sequence number, data, checksum
    Return  -> assembled packet
    """
    global TYPE_DATA, MSG_FORMAT
    # print("__make_data() for data = " + data)

    # Header
    # {
    # __Type        (1 byte)
    # __Seq num     (1 byte)
    # __Checksum    (2 bytes)
    # __Payload len (2 bytes)
    # }

    # Make initial message
    msg_format = struct.Struct(MSG_FORMAT)
    checksum = 0  # First set checksum to 0
    init_msg = msg_format.pack(TYPE_DATA, seq_num, checksum, len(data)) + data

    # Calculate checksum
    checksum = ___int_chksum(bytearray(init_msg))
    # print("checksum = " + str(checksum))

    # A complete msg with checksum
    complete_msg = msg_format.pack(TYPE_DATA, seq_num, checksum, len(data)) + data
    # print("__make_data() finished --> " + str(__unpack_helper(complete_msg)))
    return complete_msg


def __unpack_helper(msg):
    """Helper function to unpack msg."""
    global MSG_FORMAT
    size = struct.calcsize(MSG_FORMAT)
    return struct.unpack(MSG_FORMAT, msg[:size]), msg[size:]


def __is_corrupt(recv_pkt):
    """Check if the received packet is corrupted.

    Input arguments: received packet
    Return  -> True if corrupted, False if not corrupted.
    """
    global MSG_FORMAT

    # Header
    # {
    # __Type        (1 byte)
    # __Seq num     (1 byte)
    # __Checksum    (2 bytes)
    # __Payload len (2 bytes)
    # __Payload
    # }

    print("           Checking msg -> " + __unpack_helper(recv_pkt))

    # Dissect received packet
    (msg_type, seq_num, recv_checksum, payload_len), payload = __unpack_helper(recv_pkt)
    print("           : received checksum = ", recv_checksum)

    # Reconstruct initial message
    init_msg = struct.Struct(MSG_FORMAT).pack(msg_type, seq_num, 0, payload_len) + payload

    # Calculate checksum
    calc_checksum = ___int_chksum(bytearray(init_msg))
    print("           : calc checksum = ", calc_checksum)

    result = recv_checksum != calc_checksum
    # print("corrupt -> " + str(result))

    return result


def __is_ack(recv_pkt, seq_num):
    """Check if the received packet is ACK 0/1.

    Input arguments: received packet, sequence number
    Return  -> True if received ACK [seq_num]
    """
    global TYPE_ACK

    # Dissect the received packet
    (msg_type, recv_seq_num, _, _), _ = __unpack_helper(recv_pkt)
    return msg_type == TYPE_ACK and recv_seq_num == seq_num
    # if msg_type == TYPE_ACK:
    #     print("is ack")
    #     if recv_seq_num == seq_num:
    #         print("seq num same")
    #         return True
    #     else:
    #         print("seq num DIFF!")
    #         return False
    # else:
    #     print("NOT ack!")
    #     return False


def __has_seq(recv_msg, seq_num):
    """Check if the received packet has sequence number [seq_num]

    Input arguments: received packet, sequence number
    Return True if received packet of sequence number [seq_num] and False otherwise
    """
    # Dissect the received packet
    (msg_type, recv_seq_num, _, _), _ = __unpack_helper(recv_msg)
    return recv_seq_num == seq_num


def rdt_send(sockd, byte_msg):
    """Application calls this function to transmit a message to
    the remote peer through the RDT socket.

    Input arguments: RDT socket object and the message bytes object
    Return  -> size of data sent on success, -1 on error

    Note: Make sure the data sent is not longer than the maximum PAYLOAD
    length. Catch any known error and report to the user.
    """
    # Your implementation
    global PAYLOAD, __peeraddr, __data_buffer, HEADER_SIZE, __send_seq_num

    # Ensure data not longer than max PAYLOAD
    if len(byte_msg) > PAYLOAD:
        msg = byte_msg[0:PAYLOAD]
    else:
        msg = byte_msg

    # Make packet
    snd_pkt = __make_data(__send_seq_num, msg)  # Make PKT 0
    # print("rdt_send(): Sending DATA -> " + str(struct.unpack(MSG_FORMAT, snd_pkt)))

    # Try to send packet
    try:
        sent_len = __udt_send(sockd, __peeraddr, snd_pkt)
    except socket.error as err_msg:
        print("Socket send error: ", err_msg)
        return -1
    print("rdt_send(): Sent one message [%d] of size %d --> " % (__send_seq_num, sent_len) + str(msg))
    # print("rdt_send(): Sent one message [%d] of size %d --> " % (__send_seq_num, sent_len))

    r_sock_list = [sockd]  # Used in select.select()
    recv_expected = False  # Received expected response or not

    while not recv_expected:  # While not received expected ACK
        # Wait for ACK or timeout
        r, _, _ = select.select(r_sock_list, [], [], TIMEOUT)
        if r:  # ACK (or DATA) came
            for sock in r:
                # Try to receive ACK (or DATA)
                try:
                    recv_msg = __udt_recv(sock, PAYLOAD + HEADER_SIZE)
                except socket.error as err_msg:
                    print("__udt_recv error: ", err_msg)
                    return -1

                # If corrupted or undesired ACK, keep waiting
                if __is_corrupt(recv_msg) or __is_ack(recv_msg, 1 - __send_seq_num):
                    print("rdt_send(): Recv msg [corrupted] OR is wrong [ACK %d]... Keep waiting for ACK [%d]..."
                          % (1-__send_seq_num, __send_seq_num))
                    print("rdt_send() msg is this -> " + str(__unpack_helper(recv_msg)[0]))
                # Happily received expected ACK
                elif __is_ack(recv_msg, __send_seq_num):
                    print("rdt_send(): Received expected ACK [%d]" % __send_seq_num)
                    __send_seq_num ^= 1  # Flip sequence number
                    return sent_len  # Return size of data sent
                # Received intact DATA while waiting for ACK
                else:  # TODO: find right logic!
                    # Assume ACK has been received (otherwise it cannot send DATA)
                    print("rdt_send(): Received DATA?!  -> " + str(__unpack_helper(recv_msg)[0])
                          + "... Assume received expected ACK [%d]" % __send_seq_num)
                    __send_seq_num ^= 1  # Flip sequence number
                    __data_buffer.append(recv_msg) # Buffer data...
                    # Assume successfully sent, return
                    return sent_len

        else:  # Timeout
            print("Timeout!")
            # Re-transmit packet
            try:
                sent_len = __udt_send(sockd, __peeraddr, snd_pkt)
            except socket.error as err_msg:
                print("Socket send error: ", err_msg)
                return -1
            (_), payload = __unpack_helper(snd_pkt)
            # print("rdt_send(): Re-sent one message [%d] of size %d --> " % (__send_seq_num, sent_len) + str(payload))
            print("rdt_send(): Re-sent one message [%d] of size %d " % (__send_seq_num, sent_len))


def __make_ack(seq_num):
    """Make ACK [seq_num].

    Input argument: sequence number
    Return  -> assembled ACK packet
    """
    global TYPE_ACK, MSG_FORMAT
    # print("making ACK " + str(seq_num))

    # Header
    # {
    # __Type        (1 byte)
    # __Seq num     (1 byte)
    # __Checksum    (2 bytes)
    # __Payload len (2 bytes)
    # __Payload
    # }

    # Make initial message
    msg_format = struct.Struct(MSG_FORMAT)
    checksum = 0  # First set checksum to 0
    init_msg = msg_format.pack(TYPE_ACK, seq_num, checksum, 0) + b''

    # Calculate checksum
    checksum = ___int_chksum(bytearray(init_msg))
    # print("checksum = ", checksum)

    # A complete msg with checksum
    return msg_format.pack(TYPE_ACK, seq_num, checksum, 0) + b''


def rdt_recv(sockd, length):
    """Application calls this function to wait for a message from the
    remote peer; the caller will be blocked waiting for the arrival of
    the message. Upon receiving a message from the underlying UDT layer,
    the function returns immediately.

    Input arguments: RDT socket object and the size of the message to
    received.
    Return  -> the received bytes message object on success, b'' on error

    Note: Catch any known error and report to the user.
    """
    # Your implementation
    global __peeraddr, __data_buffer, __recv_seq_num

    recv_expected_data = False
    while not recv_expected_data:  # Repeat until received expected DATA
        # Receive packet
        if len(__data_buffer) > 0:
            recv_pkt = __data_buffer.pop(0)
            print("rdt_recv(): <!> Something in buffer! -> " + str(__unpack_helper(recv_pkt)[0]))
        else:
            try:
                recv_pkt = __udt_recv(sockd, length)
            except socket.error as err_msg:
                print("rdt_recv(): Socket receive error: " + str(err_msg))
                return b''

        # If packet is corrupt or has wrong seq num, send old ACK
        if __is_corrupt(recv_pkt) or __has_seq(recv_pkt, 1-__recv_seq_num):
            print("rdt_recv(): Received [corrupted] or [wrong seq_num (%d)] -> " % (1-__recv_seq_num)
                  + str(__unpack_helper(recv_pkt)[0]))
            print("-- is corrupt ? => " + str(__is_corrupt(recv_pkt)))
            print("rdt_recv(): Keep expecting seq [%d]" % __recv_seq_num)
            # Send old ACK
            snd_ack = __make_ack(1-__recv_seq_num)
            __udt_send(sockd, __peeraddr, snd_ack)
            print("rdt_recv(): Sent ACK [%d]" % (1-__recv_seq_num))
        # If received DATA with expected seq num, send ACK
        elif __has_seq(recv_pkt, __recv_seq_num):
            (_), payload = __unpack_helper(recv_pkt)  # Extract payload
            # print(("rdt_recv(): Received expected DATA [%d] -> " % __recv_seq_num) + str(payload))
            print(("rdt_recv(): Received expected DATA [%d]" % __recv_seq_num))
            # Send right ACK
            snd_ack = __make_ack(__recv_seq_num)
            __udt_send(sockd, __peeraddr, snd_ack)
            print("rdt_recv(): Sent ACK [%d]" % __recv_seq_num)
            __recv_seq_num ^= 1  # Flip seq num
            return payload


def rdt_close(sockd):
    """Application calls this function to close the RDT socket.

    Input argument: RDT socket object

    Note: (1) Catch any known error and report to the user.
    (2) Before closing the RDT socket, the reliable layer needs to wait for TWAIT
    time units before closing the socket.
    """
    # Your implementation
    # TODO: Add logic
    try:
        sockd.close()
    except socket.error as emsg:
        print("Socket close error: ", emsg)
