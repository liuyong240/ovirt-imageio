# ovirt-imageio-daemon
# Copyright (C) 2015-2016 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import


class Error(Exception):
    msg = "Overide this in a subclass"

    def __str__(self):
        return self.msg.format(self=self)


class PartialContent(Error):
    msg = "Requested {self.requested} bytes, available {self.available} bytes"

    def __init__(self, requested, available):
        self.requested = requested
        self.available = available
