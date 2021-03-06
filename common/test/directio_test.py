# ovirt-imageio-daemon
# Copyright (C) 2015-2016 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import io
import string
import sys

import pytest

from ovirt_imageio_common import directio
from ovirt_imageio_common import errors

from . import ioutil

pytestmark = pytest.mark.skipif(sys.version_info[0] > 2,
                                reason='needs porting to python 3')


def fill(s, size):
    count, rest = divmod(size, len(s))
    return s * count + s[:rest]


BUFFER = fill(string.ascii_uppercase, directio.BUFFERSIZE)
PARTIAL = fill(string.ascii_lowercase, directio.BLOCKSIZE)
BYTES = fill(string.digits, 42)


def head(str):
    return str[:10]


@pytest.mark.parametrize("offset", [0, 42, 512])
@pytest.mark.parametrize("data", [
    BUFFER * 2,
    BUFFER + PARTIAL * 2,
    BUFFER + PARTIAL + BYTES,
    PARTIAL * 2,
    PARTIAL + BYTES,
], ids=head)
def test_send(tmpdir, data, offset):
    size = len(data) - offset
    expected = data[offset:]
    assert send(tmpdir, data, size, offset=offset) == expected


@pytest.mark.parametrize("offset", [0, 42, 512])
@pytest.mark.parametrize(
    "size", [511, 513, len(BUFFER) + 511, len(BUFFER) + 513])
def test_send_partial(tmpdir, size, offset):
    data = BUFFER * 2
    expected = data[offset:offset + size]
    assert send(tmpdir, data, size, offset=offset) == expected


@pytest.mark.parametrize("offset", [0, 42, 512])
@pytest.mark.parametrize("data", [
    BUFFER * 2,
    BUFFER + PARTIAL * 2,
    BUFFER + PARTIAL + BYTES,
    PARTIAL * 2,
    PARTIAL + BYTES,
], ids=head)
def test_send_partial_content(tmpdir, data, offset):
    size = len(data) - offset
    with pytest.raises(errors.PartialContent) as e:
        send(tmpdir, data[:-1], size, offset=offset)
    assert e.value.requested == size
    assert e.value.available == size - 1


def send(tmpdir, data, size, offset=0):
    src = tmpdir.join("src")
    src.write(data)
    dst = io.BytesIO()
    op = directio.Send(str(src), dst, size, offset=offset)
    op.run()
    return dst.getvalue()


@pytest.mark.parametrize("offset", [0, 42, 512])
@pytest.mark.parametrize("data", [
    BUFFER * 2,
    BUFFER + PARTIAL * 2,
    BUFFER + PARTIAL + BYTES,
    PARTIAL * 2,
    PARTIAL + BYTES,
    BYTES,
], ids=head)
def test_receive(tmpdir, data, offset):
    assert receive(tmpdir, data, len(data), offset=offset) == data


@pytest.mark.parametrize("offset", [0, 42, 512])
@pytest.mark.parametrize(
    "size", [511, 513, len(BUFFER) + 511, len(BUFFER) + 513])
def test_receive_partial(tmpdir, size, offset):
    data = BUFFER * 2
    assert receive(tmpdir, data, size, offset=offset) == data[:size]


@pytest.mark.parametrize("offset", [0, 42, 512])
@pytest.mark.parametrize("data", [
    BUFFER * 2,
    BUFFER + PARTIAL * 2,
    BUFFER + PARTIAL + BYTES,
    PARTIAL * 2,
    PARTIAL + BYTES,
    BYTES,
], ids=head)
def test_receive_partial_content(tmpdir, data, offset):
    with pytest.raises(errors.PartialContent) as e:
        receive(tmpdir, data[:-1], len(data), offset=offset)
    assert e.value.requested == len(data)
    assert e.value.available == len(data) - 1


def receive(tmpdir, data, size, offset=0):
    dst = tmpdir.join("dst")
    dst.write("x" * offset)
    src = io.BytesIO(data)
    op = directio.Receive(str(dst), src, size, offset=offset)
    op.run()
    with open(str(dst), "rb") as f:
        f.seek(offset)
        return f.read()


def test_send_repr():
    op = directio.Send("/path", None, 200, offset=24)
    rep = repr(op)
    assert "Send" in rep
    assert "path='/path' size=200 offset=24 buffersize=512 done=0" in rep


def test_recv_repr():
    op = directio.Receive("/path", None, 100, offset=42)
    rep = repr(op)
    assert "Receive" in rep
    assert "path='/path' size=100 offset=42 buffersize=512 done=0" in rep


@pytest.mark.parametrize("size,rounded", [
    (0, 0),
    (1, 512),
    (512, 512),
    (513, 1024),
])
def test_round_up(size, rounded):
    assert directio.round_up(size) == rounded


@pytest.mark.parametrize("bufsize", [512, 1024, 2048])
def test_receive_unbuffered_stream(tmpdir, bufsize):
    chunks = ["1" * 1024,
              "2" * 1024,
              "3" * 42,
              "4" * 982]
    data = ''.join(chunks)
    assert receive_unbuffered(tmpdir, chunks, len(data), bufsize) == data


def test_receive_unbuffered_stream_partial_content(tmpdir):
    chunks = ["1" * 1024,
              "2" * 1024,
              "3" * 42,
              "4" * 982]
    data = ''.join(chunks)
    with pytest.raises(errors.PartialContent):
        receive_unbuffered(tmpdir, chunks, len(data) + 1, 2048)


def receive_unbuffered(tmpdir, chunks, size, bufsize):
    dst = tmpdir.join("dst")
    dst.write("")
    src = ioutil.UnbufferedStream(chunks)
    op = directio.Receive(str(dst), src, size, buffersize=bufsize)
    op.run()
    return dst.read()


@pytest.mark.parametrize("offset", [0, 42, 512])
@pytest.mark.parametrize("data", [
    BUFFER * 2,
    BUFFER + PARTIAL * 2,
    BUFFER + PARTIAL + BYTES,
    PARTIAL * 2,
    PARTIAL + BYTES,
], ids=head)
def test_receive_no_size(tmpdir, data, offset):
    dst = tmpdir.join("dst")
    dst.write("x" * offset)
    src = io.BytesIO(data)
    op = directio.Receive(str(dst), src, offset=offset)
    op.run()
    assert dst.read()[offset:] == data


@pytest.mark.parametrize("offset", [0, 42, 512])
@pytest.mark.parametrize("data", [
    BUFFER * 2,
    BUFFER + PARTIAL * 2,
    BUFFER + PARTIAL + BYTES,
    PARTIAL * 2,
    PARTIAL + BYTES,
], ids=head)
def test_send_no_size(tmpdir, data, offset):
    src = tmpdir.join("src")
    src.write(data)
    dst = io.BytesIO()
    op = directio.Send(str(src), dst, offset=offset)
    op.run()
    assert dst.getvalue() == data[offset:]
