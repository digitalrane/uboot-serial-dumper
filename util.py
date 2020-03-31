#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2020 ec0 <ec0@ec0.io>
#
# Distributed under terms of the GPL license.

"""Dump, write and modify the firmware from an Octean router (other devices possible) via failsafe u-boot."""

import binascii
import serial
import struct
import sys
from tqdm import tqdm


class Util():
    """Utility functions for firmware dumper."""

    PROMPT = "Failsafe # "

    def __init__(self, port, baud):
        """Instantiate variables."""
        self.port = port
        self.baud = baud
        self.open_serial()

    def open_serial(self):
        """Open the serial port."""
        self.serial = serial.Serial(
            self.port,
            self.baud,
            exclusive=True,
            xonxoff=True,
            timeout=10
        )

    def read_serial(self, size=1):
        """Read a byte, or more if the size parameter is set larger."""
        return self.serial.read(size)

    def read_serial_line(self):
        """Read a line up to a line terminator."""
        return self.serial.readline().decode()

    def write_serial(self, data):
        """Write data to the serial port."""
        byte_data = data.encode()
        self.serial.write(byte_data)
        self.serial.flush()

    def bl_wait_command(self, command, response=None):
        """Wait for specific text before returning."""
        if not response:
            response = self.PROMPT
            byte_response = response.encode()
        self.print_console("Waiting for '{}' to indicate command `{}` is done...".format(response, command))
        self.write_serial("{}\n".format(command))
        return self.serial.read_until(byte_response)

    def bl_wait_for_prompt(self):
        """Wait for the failsafe prompt."""
        return self.bl_wait_command("", self.PROMPT)

    def clear_prompt(self):
        """Clear prompt."""
        self.write_serial("\n")
        return self.read_serial(size=8)

    def print_console(self, text):
        """Print debug info to stderr."""
        sys.stderr.write("\033[92m{}\033[0m\n".format(text))

    def print_console_error(self, text, debug):
        """Print error with data."""
        sys.stderr.write("\033[91m{}\033[0m\nDebug: {}".format(
            text,
            debug
        ))

    def hextobin(self, hexstr):
        """Output binary data based on a MIPS64 hex string returned by read64."""
        data = binascii.a2b_hex(hexstr)
        bytestr = struct.unpack('>8B', data)
        return bytes(bytestr)

    def start_progress(self, iterable):
        """Start a progress bar for x total bytes."""
        self.tqdm = tqdm(total=len(iterable) * 0x08, unit="Bytes")

    def update_progress(self, offset, inc, data):
        """Update progress bar with current offset and data."""
        self.tqdm.update(inc)
        self.tqdm.set_description("{:X}: {:s}".format(
            offset,
            data
        ))
