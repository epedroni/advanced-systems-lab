#!/usr/bin/bash

echo "Install build tools and memcached"

sudo apt-get install build-essential libevent-dev

echo "Get and build memaslap (will take a while)"

#use exactly this version of libmemcached!

wget https://launchpad.net/libmemcached/1.0/1.0.18/+download/libmemcached-1.0.18.tar.gz

tar xvf libmemcached-1.0.18.tar.gz

cd libmemcached-1.0.18

export LDFLAGS=-lpthread

./configure --enable-memaslap && make clients/memaslap
