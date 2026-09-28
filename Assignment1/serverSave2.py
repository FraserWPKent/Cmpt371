# Name: Fraser Kent   Student number: 301476753
"""CMPT 371 Project 1 - static HTTP/1.1 server on raw TCP sockets.

Usage: python3 server.py --port PORT --root DIR [--workers N]
"""

import argparse
import mimetypes
import os
import queue
import socket
import sys
import threading
import time
from email.utils import formatdate
from socket import *

KNOWN_METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "TRACE", "CONNECT"}

requests_served = 0
counter_lock = threading.Lock()


def parse_args(argv):
    """TASK 1. Parse --port (int, 0 means pick any free port), --root
    (directory), --workers (int, how many threads the pool starts with,
    default 8). Accept --workers from task 1 even though nothing uses it until
    task 5: every command in the handout passes it."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--port")
    parser.add_argument("--root")
    parser.add_argument("--workers")

    args = parser.parse_args()
    if(args.workers == None):
        args.workers = 8
    return int(args.port), args.root, int(args.workers)

def recv_request_head(conn):
    """TASK 3. Call recv() repeatedly until the blank line that ends the header
    block has arrived. Return the head bytes including that blank line, or None
    if the client closed the connection first.
    In task 1 handle_connection may read the head with a single recv(); this is
    what replaces that call, and is where reading becomes correct."""
    x = 0
    fullRequest = ""
    lastFour = ["1","2","3","4"]
    while(lastFour != ["\n", "\r", "\n", "\r"]):
            try:
                request = conn.recv(1).decode()
            except(ConnectionError) as e:
                return None
            if(len(request)==0):
                #Shutting down due to an empty request
                #conn.close()
                return None
            # Building an array of the last four elements to check for the end of request signal
            for i in range(3,0,-1):
                lastFour[i] = lastFour[i-1]
            lastFour[0] = request
            fullRequest += request

    return fullRequest


def parse_request(head):
    """TASK 3. Split a header block into (method, target, version, headers).
    headers is a dict with lower-cased names. Raise ValueError if the request
    line is not three fields or a header line has no colon; handle_request turns
    that into a 400."""

    #print(head)

    # Validating the first line of the request is three space seperated fields
    topLine = ""
    i = 0
    totalSpaces = 0
    while(head[i] != "\r"):
        if(head[i] == " "):
            totalSpaces +=1
        topLine+=head[i]
        i+=1
        if(totalSpaces > 2):
            raise ValueError
    if(totalSpaces != 2):
        raise ValueError
    
    array = head.split()
    if(not ("Host:" in array)):
        raise ValueError

    dictionary = dict()
    for i in range(3, len(array), 2):
        dictionary[array[i].lower().replace(":", "")] = array[i+1]
        if(array[i][len(array[i])-1] != ":"):
            raise ValueError

    #print(dictionary)
    return array, dictionary

def resolve_path(root, target):
    if(len(target) == 1):
        target = root + "/index.html"
    else:
        target = root + target

    return target

    """TASK 1. Turn a request target into an absolute path inside root: drop any
    query string, percent-decode, append index.html for a target ending in '/'.
    Return None if the target is malformed.
    All three rules are graded: /index.html?x=1 and /index.html are the same
    file, / is that directory's index.html, and /page/sub.html works."""


def build_response(status, reason, body, content_type, extra=None):
    """TASK 1. Return the full response as bytes: status line, the Date, Server,
    Content-Type, Content-Length and Connection headers, any extra headers,
    a blank line, then body.
    Every response goes through here, including 404, 400, 405 and 501, so every
    response carries all five headers. Content-Length is the number of body
    bytes that follow, and nothing else."""

    # Extra will store the content length

    #print("File Bytes 2: "+ str(len(body)))

    response = "HTTP/1.1 "+str(status) + " " + str(reason) +"\r\n"
    response += "Date: " + formatdate(usegmt=True) + "\r\n"
    response += "Server: cmpt371/1.0\r\n"
    response += "Content-Type: " + content_type + "\r\n"
    response += "Content-Length: "+str(extra) +"\r\n"
    if(status == 405):
        response += "Allow: GET, HEAD\r\n"
    response += "Connection: keep-alive\r\n\r\n"

    # Encoding the string response into raw bytes then combining those bytes with the bytes from the body
    responseBytes = response.encode("utf-8")

    bytes = responseBytes + body

    return bytes 

def handle_request(head, root):
    """TASK 1, extended in tasks 2 and 3. Turn one header block into a complete
    response.
    Task 1: 200 and 404. Task 2: HEAD, which carries no body, and Content-Type
    from the file extension. Task 3: 400 (malformed request line or header line,
    no Host), 405 (POST and the other known methods, with Allow: GET, HEAD) and
    501 (a token that is not an HTTP method)."""

    badRequest = False

    try:
        array, dictionary = parse_request(head)
    except(ValueError):
        badRequest= True
    if(badRequest):
        response = build_response(400, "Bad Request", "400 Bad Request".encode("utf-8"), "text/html", 16)
        #print(response)
        return response
    elif(array[0] == "GET" or array[0] == "HEAD"):
        path = ""

        for i in range(len(array[0])+1, len(head)):
            if(head[i] == " " or head[i] == "?"):
                break
            path += head[i]

        path = resolve_path(root, path)

        try:
            #Getting the files. If they dont exist then A FileNotFoundError is thrown
            #And I spit out a 404 message
            fileType = mimetypes.guess_type(path)[0]
            fileSize = os.path.getsize(path)
            try:
                with open(path, "rb") as file:
                    fileBytes = file.read()
                    #print(len(fileBytes))
                    #print(fileBytes)
            except(Exception) as e:
                #print(e)
                # This shoudnt happen but if it does I'll set the file bytes to be 0 to denote a bad file
                fileBytes = 0
                
            if(fileType == None):
                if(array[0] == "GET"):
                    response = build_response(200, "OK", fileBytes, "application/octet-stream", fileSize)
                else:
                    #Encoding an empty string to send no body
                    response = build_response(200, "OK", "".encode("utf-8"), "application/octet-stream", fileSize)
            else:
                if(array[0] == "GET"):
                    response = build_response(200, "OK", fileBytes, fileType, fileSize)
                else:
                    #Encoding an empty string to send no body
                    response = build_response(200, "OK", "".encode("utf-8"), fileType, fileSize)
            #print(response)
            return response

        except (Exception):
            
            if(array[0] == "GET"):
                response = build_response(404, "Not Found", "404 Not Found\n".encode("utf-8"), "text/html", 14)
            else:
                if(fileType == None):
                    response = build_response(404, "Not Found", "".encode("utf-8"), "application/octet-stream", 0)
                else:
                    response = build_response(404, "Not Found", "".encode("utf-8"), fileType, 0)

            #print(response)
            return response
                
    elif (array[0] in KNOWN_METHODS):
        response = build_response(405, "Method Not Allowed", "405 Method Not Allowed\n".encode("utf-8"), "text/html", 23)
        #print(response)
        return response
    else:
        response = build_response(501, "Not Implemented", "501 Not Implemented\n".encode("utf-8"), "text/html", 20)
        #print(response)
        return response



def handle_connection(conn, root):
    """TASK 1, extended in tasks 3 and 5. Serve requests on one connection until
    the client closes it or it goes idle -- a few seconds; five is reasonable.
    Task 1: read the head (one recv() is enough for now), call handle_request,
    sendall() the response, and loop. Task 3: replace that read with
    recv_request_head. Task 5: after each response, increment requests_served
    under counter_lock and print 'served <n>' to stderr, where n is the value
    this request produced, read inside the same lock that incremented it."""
    try:
        while True:
            fullRequest = recv_request_head(conn=conn)
            if(fullRequest == None):
                break
            resp = handle_request(fullRequest, root)
            try:
                conn.sendall(resp)
            except(ConnectionError) as e:
                #print("Failing")
                #print(e)
                # The connection shut down when trying to send data. Opening the thread again to handle another connection
                break
            # Code from the project pdf
            with counter_lock:
                global requests_served 
                requests_served += 1
                mine = requests_served
                print("served %d" % mine, file=sys.stderr, flush=True)
    except (TimeoutError):
        conn.close()
        return
    conn.close()



def worker(work_queue, root):
    """TASK 5. Take accepted connections off work_queue and serve them, forever.
    Every worker thread runs this; none of them is created per connection.
    Nothing before task 5 calls this, and main must not start any worker threads
    until you write it."""

    while(True):
        currentConn = work_queue.get()
        handle_connection(currentConn, root=root)
        #time.sleep(1)


def main(argv=None):
    """TASK 1, replaced in task 5. Bind 127.0.0.1 on the requested port, listen,
    print the port line below, then serve connections.
    Task 1: accept one connection at a time and pass each to handle_connection.
    Task 5: replace that loop -- create --workers threads running worker() and a
    queue.Queue, and let main do nothing but accept and enqueue."""

    port, root, workers = parse_args(argv)    

    serverSocket = socket(AF_INET, SOCK_STREAM)

    serverSocket.bind(('127.0.0.1',port))

    sockName = serverSocket.getsockname()

    assignedPort = sockName[1]

    # Only letting one waiting connection for now
    serverSocket.listen()

    print("Listening on port " + str(assignedPort), end="\n", flush=True)
    
    workQueue = queue.Queue()
    threads = []
    #Creating n threads to handle out connections
    for i in range(0, workers): 
        thread = threading.Thread(target=worker, args = (workQueue, root))
        threads.append(thread)
        thread.start()
        

    
    while True:
        connectionSocket, addr = serverSocket.accept()
        #setting a timeout of 5 seconds for my connection socket
        connectionSocket.settimeout(5)
        workQueue.put(connectionSocket)

if __name__ == "__main__":
    main()
