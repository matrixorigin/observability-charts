#!/usr/bin/env python3

import datetime
import socket
import sys
import curl
import requests


original_stdout = sys.stdout # Save a reference to the original standard output



# Block size is set to 8192 because thats usually the max header size
BLOCK_SIZE = 8192

def serve(host='0.0.0.0', port=3246, verbosity=1):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(1)

        if verbosity > 0:
            print('Echoing from http://{}:{}'.format(host, port))

        while True:
            connection, client_address = sock.accept()
            requestDict = {}
            bytes_left = BLOCK_SIZE
            while bytes_left > 0:
                if bytes_left > BLOCK_SIZE:
                    data = connection.recv(BLOCK_SIZE)
                else:
                    data = connection.recv(max(0, bytes_left))
                if not 'header' in requestDict:
                    requestDict = build_request(data)
                    header_length = len(requestDict['raw']) - len(requestDict['body'])
                    body_length_read = BLOCK_SIZE - header_length
                    if 'content-length' in requestDict['header']:
                        bytes_left = int(requestDict['header']['content-length']) - body_length_read
                    else:
                        bytes_left = 0
                else:
                    requestDict['raw'] += data
                    requestDict['body'] += data.decode('utf-8', 'ignore')
                    bytes_left -= BLOCK_SIZE
            req = requests.Request(method=requestDict['header']['request-line'].split(' ')[0],url= 'http://'+requestDict['header']['host'], headers=requestDict['header'], data=requestDict['body']).prepare()
            curl_cmd=curl.parse(req,return_it=True,print_it=False)
            request_time = datetime.datetime.now().ctime()
            if verbosity > 0:
                print(' - '.join([client_address[0], request_time, requestDict['header']['request-line']]))
                print('receive from alertmanager, transfer to curl-cmd to test your webhook:')
                print(curl_cmd)
                with open('curl.txt', 'a') as f:
                    sys.stdout = f # Change the standard output to the file we created.
                    print(curl_cmd+"\n")
                    sys.stdout = original_stdout # Reset the standard output to its original value
            raw_decoded = requestDict['raw'].decode('utf-8', 'ignore')
            req = "HTTP/1.1 200 OK\nAccess-Control-Allow-Origin: *\n\n{}".format(raw_decoded)
            if verbosity == 2:
                print("-"*10)
                print(req)
                print("-"*40)
            connection.sendall(req.encode())
            connection.close()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sock.close()


def build_request(first_chunk):
    lines = first_chunk.decode('utf-8', 'ignore').split('\r\n')
    h = {'request-line': lines[0]}
    i = 1
    while i < len(lines[1:]) and lines[i] != '':
        k, v = lines[i].split(': ')
        h.update({k.lower(): v})
        i += 1
    r = {
        "header": h, 
        "raw": first_chunk,
        "body": lines[-1]
    }
    print("receive request details:")
    print(r["header"])
    print(r["raw"])
    print(r["body"])
    return r


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Server that returns any http request made to it")
    parser.add_argument('-b', '--bind', default='localhost', help='host to bind to')
    parser.add_argument('-p', '--port', default=3246, type=int, help='port to listen on')
    parser.add_argument('-v', '--verbose', action='store_true', help='print all requests to terminal')
    parser.add_argument('-q', '--quiet', action='store_true', help='silence all output (overrides --verbose)')
    args = parser.parse_args()
    host = args.bind
    port = args.port
    verbose = args.verbose
    quiet = args.quiet

    verbosity = 1
    if verbose:
        verbosity = 2
    if quiet:
        verbosity = 0

    serve(host, port, verbosity)

