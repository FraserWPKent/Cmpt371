# Name: Fraser Kent   Student number: 301476753
"""CMPT 371 Project 1 - HTTP/1.1 client on a raw TCP socket.

Usage: python3 client.py --host H --port P --path /a [--path /b] [--out FILE ...]
"""

import argparse
from socket import *
import sys

def parse_args(argv):
    """TASK 4. Parse --host (default 127.0.0.1), --port (int), --path
    (repeatable), --out (repeatable, paired with --path in order)."""


    parser = argparse.ArgumentParser()
    parser.add_argument("--host")
    parser.add_argument("--port")
    parser.add_argument("--path", action="append")
    parser.add_argument("--out", action="append")

    args = parser.parse_args()
    return args.host, args.port, args.path, args.out



def send_request(sock, host, path):    
    """TASK 4. Send one GET request line, a Host header, and the blank line
    that ends it."""

    response = "GET " + str(path) + " HTTP/1.1\r\n"
    response += "Host: " + host + "\r\n"
    response += "User-Agent: client\r\n"
    response += "Accept: */*\r\n\r\n"

    #print(response)
    sock.sendall(response.encode("utf-8"))

    bodyBytes = read_head(sock, "")
    return bodyBytes


def read_head(sock, pending):
    """TASK 4. Read until the blank line ending the response head.
    Return (head_bytes, leftover) where leftover is body already received. The
    leftover is the start of the body and cannot be read again, so it must be
    counted toward Content-Length rather than discarded."""
    lastChar = " "
    currentChar = " "
    currentString = ""
    lastFour = ["1","2","3","4"]
    while(lastFour != ["\n", "\r", "\n", "\r"]):
    #while(True):
        
        currentChar = sock.recv(1).decode("utf-8")
        if(len(currentChar) == 0):
            # Server closed before the client could get its response. closing the client
            sock.close()
            sys.exit(1)
        for i in range(3,0,-1):
            lastFour[i] = lastFour[i-1]
        lastFour[0] = currentChar
        currentString += currentChar

    #print(currentString)

    status, response, dict = parse_head(currentString)
    

    #print(headers)
    length = int(dict["content-length"])
    bodyBytes = read_body(sock, length, "")

    #print(bodyBytes.decode("utf-8"))

    print(str(status) + " " + response + " " + dict["content-length"] + " bytes")

    if(str(status) == "404"):
        return None

    return bodyBytes
    
def parse_head(head):

    code = ""
    status = ""
    spaces = 0
    for char in head:
        if(char == "\r"):
            break
        if(spaces >= 2):
            status += char
        elif(char == " "):
            spaces+=1
        elif(spaces == 1):
            code += char

    headers = head.split()

    dictionary = dict()

    for i in range(3, len(headers)-1):
        if(headers[i].lower() == "date:"):
            mergedDate = ""
            x = i+1
            while(headers[x].lower() != "server:"):
                mergedDate += headers[x]+" "
                x+=1
            #print(mergedDate)

    i = 3
    #for i in range(3, len(headers)-1):
    while(i < len(headers)-1):
        if(headers[i].lower() == "date:"):
            dictionary[headers[i].lower().replace(":","")] = mergedDate
            while(headers[i].lower() != "server:"):
                i+=1
        else:
            dictionary[headers[i].lower().replace(":","")] = headers[i+1]
            i+=2

    #print(headers)
    #print(dictionary)

    return code, status, dictionary
    """TASK 4. Split a response head into (status_code, reason, headers).
    headers is a dict with lower-cased names."""

def read_body(sock, length, pending):
    """TASK 4. Return exactly length body bytes, counting what is already in
    pending, plus any bytes left over past them. Do not read until the connection
    closes: the server keeps it open, so a read-to-EOF client never returns.
    Every check in task 4 runs against a server that holds the connection open
    for a full minute, so reading to EOF fails all four, not just the timing
    one."""
    byt = bytes()
    #print(length)
    #print(len(byt))
    while(len(byt) < length):
        byt += sock.recv(length-len(byt))
        #print(len(byt))
    return byt

def main(argv=None):
    """TASK 4. Connect once, then for each --path in turn: send the request,
    read the head, read exactly Content-Length bytes, print
    '<status> <reason> <n> bytes', and write the body to the matching --out file.
    Return 0 on success. All the paths travel over the one connection, so
    whatever is left in the buffer past one body is the start of the next
    response."""

    host, port, paths, outs = parse_args(argv)
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((host, int(port)))
    except(Exception):
        sys.exit(1)

    for i  in range(len(paths)):
        #for x in range(0, 1000):
        path = paths[i]
        out = outs[i]
        bodyBytes = send_request(clientSocket, str(host)+":"+str(port), path)
        if(bodyBytes != None):
            with open(out,"wb") as file:
                #print(bodyBytes)
                file.write(bodyBytes)
                file.close()

    #time.sleep(2)
    clientSocket.close()
    sys.exit(0)



if __name__ == "__main__":
    sys.exit(main())
