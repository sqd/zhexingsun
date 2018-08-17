#!/bin/sh

mkdir -p certs/
openssl genrsa -out certs/ca.key 2048
openssl req -new -x509 -days 3650 -key certs/ca.key -out certs/ca.crt -subj "/CN=proxy2 CA"
openssl genrsa -out certs/cert.key 2048
