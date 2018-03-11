#!/usr/bin/python3
"""File transfer server program

This is for testing of the RDT3.0 layer.

"""

import sys
import os
import rdt3 as rdt


def main():
    MSG_LEN = rdt.PAYLOAD

    # Check the number of input arguments
    if len(sys.argv) != 4:
        print("Usage:  " + sys.argv[0] + "  <client IP>  <drop rate>  <error rate>")
        sys.exit(0)

    # check whether the folder exists
    try:
        os.stat("./Store")
    except OSError as emsg:
        print("Directory './Store' does not exist!!")
        print("Please create the directory before starting up the server")
        sys.exit(0)

    # set up the RDT simulation
    rdt.rdt_network_init(sys.argv[2], sys.argv[3])

    # create RDT socket
    sockfd = rdt.rdt_socket()
    if sockfd == None:
        sys.exit(0)

    # specify my own IP address & port number
    # if I do not specify, others can not send things to me.
    if rdt.rdt_bind(sockfd, rdt.SPORT) == -1:
        sys.exit(0)

    # specify the IP address & port number of remote peer
    if rdt.rdt_peer(sys.argv[1], rdt.CPORT) == -1:
        sys.exit(0)

    # implement a simple handshaking protocol at the application layer
    # First wait for client 1st message
    rmsg = rdt.rdt_recv(sockfd, MSG_LEN)
    if rmsg == b'':
        sys.exit(0)
    else:
        filelength = int(rmsg)
        print("Received client request: file size =", filelength)
    # then wait for client 2nd message
    rmsg = rdt.rdt_recv(sockfd, MSG_LEN)
    if rmsg == b'':
        sys.exit(0)
    else:
        filename = "./Store/" + rmsg.decode("ascii")
        # open file
        try:
            fobj = open(filename, 'wb')
        except OSError as emsg:
            print("Open file error: ", emsg)
        if fobj:
            print("Open file", filename, "for writing successfully")
            osize = rdt.rdt_send(sockfd, b'OKAY')
            if osize < 0:
                print("Cannot send response message")
                sys.exit(0)
        else:
            print("Cannot open the target file", filename, "for writing")
            osize = rdt.rdt_send(sockfd, b'ERROR')
            sys.exit(0)

    # start the data transfer
    print("Start receiving the file . . .")
    received = 0
    while received < filelength:
        print("server progress: %d / %d" % (received, filelength))
        rmsg = rdt.rdt_recv(sockfd, MSG_LEN)
        if rmsg == b'':
            print("Encountered receive error! Has received", received, "so far.")
            sys.exit(0)
        else:
            wsize = fobj.write(rmsg)
            received += wsize

    # Closing
    fobj.close()
    rdt.rdt_close(sockfd)
    print("Completed the file transfer.")
    print("Server program terminated")


if __name__ == "__main__":
    main()
