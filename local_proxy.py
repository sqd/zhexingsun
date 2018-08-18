#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import socket
import ssl
import threading
import time
import re
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from subprocess import Popen, PIPE
import httplib
from argparse import ArgumentParser

PROXY_SERVER_SECRET_HEADER = 'X-Proxy-Secret'
PROXY_SERVER_SCHEME_HEADER = 'X-Proxy-Scheme'
PROXY_SELF_SIGNED = True

args = None


def join_with_script_dir(path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True

    def handle_error(self, request, client_address):
        # surpress socket/ssl related errors
        cls, e = sys.exc_info()[:2]
        if cls is socket.error or cls is ssl.SSLError:
            pass
        else:
            return HTTPServer.handle_error(self, request, client_address)


class ProxyRequestHandler(BaseHTTPRequestHandler):
    cakey = join_with_script_dir('certs/ca.key')
    cacert = join_with_script_dir('certs/ca.crt')
    certkey = join_with_script_dir('certs/cert.key')
    certdir = join_with_script_dir('certs/')
    timeout = 5
    protocol_version = "HTTP/1.1"
    lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        # Will be initialized in StreamRequestHandler <- BaseHTTPRequestHandler
        self.connection = None

        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def log_error(self, format, *args):
        # surpress "Request timed out: timeout('timed out',)"
        if len(args) and isinstance(args[0], socket.timeout):
            return

        self.log_message(format, *args)

    def connect_intercept(self):
        hostname = self.path.split(':')[0]
        certpath = "%s/%s.crt" % (self.certdir.rstrip('/'), hostname)

        with self.lock:
            if not os.path.isfile(certpath):
                epoch = "%d" % (time.time() * 1000)
                p1 = Popen(["openssl", "req", "-new", "-key", self.certkey, "-subj", "/CN=%s" % hostname], stdout=PIPE)
                p2 = Popen(["openssl", "x509", "-req", "-days", "3650", "-CA", self.cacert, "-CAkey", self.cakey, "-set_serial", epoch, "-out", certpath], stdin=p1.stdout, stderr=PIPE)
                p2.communicate()

        self.wfile.write("%s %d %s\r\n" % (self.protocol_version, 200, 'Connection Established'))
        self.end_headers()

        self.connection = ssl.wrap_socket(self.connection, keyfile=self.certkey, certfile=certpath, server_side=True)
        self.rfile = self.connection.makefile("rb", self.rbufsize)
        self.wfile = self.connection.makefile("wb", self.wbufsize)

        conntype = self.headers.get('Proxy-Connection', '')
        if self.protocol_version == "HTTP/1.1" and conntype.lower() != 'close':
            self.close_connection = 0
        else:
            self.close_connection = 1

    def do_GET(self):
        if self.path in ('http://proxy2.test/', 'http://install_ca/'):
            self.send_cacert()
            return

        req = self
        content_length = int(req.headers.get('Content-Length', 0))
        req_body = self.rfile.read(content_length) if content_length else None

        isSSL = isinstance(req.connection, ssl.SSLSocket)

        conn = None
        try:
            scheme = 'https' if isinstance(self.connection, ssl.SSLSocket) else 'http'
            path = req.path
            headers = dict(req.headers)
            headers[PROXY_SERVER_SECRET_HEADER] = args.password
            headers[PROXY_SERVER_SCHEME_HEADER] = scheme

            conn = httplib.HTTPSConnection(args.server, timeout=self.timeout,
                                           context=ssl._create_unverified_context() if args.self_signed else None)
            conn.request(self.command, path, req_body, headers)
            res = conn.getresponse()

            version_table = {10: 'HTTP/1.0', 11: 'HTTP/1.1'}
            setattr(res, 'headers', res.msg)
            setattr(res, 'response_version', version_table[res.version])

            res_body = res.read()
        except Exception as e:
            self.log_error('Exception: %s', e)
            if isinstance(e, ssl.SSLError):
                self.log_error('If you\'re signing your own certificates, make sure you use --self-signed')
            self.send_error(502)
            if conn.sock and not isinstance(e, ssl.SSLError):
                conn.sock = conn.sock.unwrap()
            conn.sock.close()
            if isSSL:
                self.connection = self.connection.unwrap()
            self.connection.close()
            return

        setattr(res, 'headers', self.filter_headers(res.headers))

        self.wfile.write("%s %d %s\r\n" % (self.protocol_version, res.status, res.reason))
        for line in res.headers.headers:
            self.wfile.write(line)
        self.end_headers()
        self.wfile.write(res_body)
        self.wfile.flush()
        if isSSL:
            self.connection = self.connection.unwrap()
        self.connection.close()
        if conn.sock:
            conn.sock = conn.sock.unwrap()
            conn.sock.close()


    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET
    do_OPTIONS = do_GET
    do_CONNECT = connect_intercept

    def filter_headers(self, headers):
        # http://tools.ietf.org/html/rfc2616#section-13.5.1
        hop_by_hop = ('connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade')
        for k in hop_by_hop:
            del headers[k]

        # accept only supported encodings
        if 'Accept-Encoding' in headers:
            ae = headers['Accept-Encoding']
            filtered_encodings = [x for x in re.split(r',\s*', ae) if x in ('identity', 'gzip', 'x-gzip', 'deflate')]
            headers['Accept-Encoding'] = ', '.join(filtered_encodings)

        return headers

    def send_cacert(self):
        with open(self.cacert, 'rb') as f:
            data = f.read()

        self.wfile.write("%s %d %s\r\n" % (self.protocol_version, 200, 'OK'))
        self.send_header('Content-Type', 'application/x-x509-ca-cert')
        self.send_header('Content-Length', len(data))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)

    def request_handler(self, req, req_body):
        pass

    def response_handler(self, req, req_body, res, res_body):
        pass


def main():
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', help='port the local HTTP proxy listens on', type=int, default=8080)
    parser.add_argument('-d', '--host', help='host the local HTTP proxy listens on', default='')
    parser.add_argument('-s', '--server', required=True, help='address of the remote proxy server')
    parser.add_argument('-x', '--password', required=True, help='password')
    parser.add_argument('-k', '--self-signed', action='store_true', help='[DANGEROUS] ignore SSL certification '
                                                                         'warning when connecting to the proxy server')
    global args
    args = parser.parse_args()

    server_address = (args.host, args.port)

    httpd = ThreadingHTTPServer(server_address, ProxyRequestHandler)

    sa = httpd.socket.getsockname()
    print "Serving HTTP Proxy on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()


if __name__ == '__main__':
    main()
