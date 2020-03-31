#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2020 ec0 <ec0@ec0.io>
#
# Distributed under terms of the GPL license.

"""Dump, write and modify the firmware from an Octean router (other devices possible) via failsafe u-boot."""

from util import Util
import argparse
import math
import re


class Dumper:
    """CLI for dumping firmware."""

    def __init__(self):
        """Entry point."""
        parser = argparse.ArgumentParser(
            description="Dump firmware via Octeon u-boot failsafe"
        )
        parser.add_argument(
            "serial",
            type=str,
            help="Serial port device connected to the router",
            default="/dev/ttyUSB0",
        )
        parser.add_argument(
            "--start",
            type=str,
            help="Start offset, in hex bytes.",
        )
        parser.add_argument(
            "--stop",
            type=str,
            help="End offset, in hex bytes.",
        )
        parser.add_argument(
            "baud",
            type=int,
            help="Baud rate to operate at on the attached serial console",
            default=115200,
        )
        parser.add_argument(
            "output", type=argparse.FileType("ab"), help="File to output dump into" ""
        )
        self.args = parser.parse_args()
        self.util = Util(self.args.serial, self.args.baud)
        self.read_re = re.compile(r"([0-9a-fA-F]+): 0x([0-9a-fA-F]+)")

    def prepare_file(self):
        """Prepare the file for output."""
        self.args.output.truncate(0)

    def parse_flinfo(self):
        """Parse flinfo command to get flash ranges."""
        flinfo = self.util.bl_wait_command("flinfo")
        if b"Bank # 1" in flinfo:
            self.util.print_console("Retrieved flinfo")
        else:
            self.util.print_console_error("Failed to retrieve flinfo", flinfo)
        flinfo_string = flinfo.decode()
        flinfo_sectors = re.findall(r"\s([a-fA-F0-9]{8})\s", flinfo_string)
        self.sectors = []
        for flinfo_sector in flinfo_sectors:
            self.util.print_console("Found flash sector: {}".format(flinfo_sector))
            self.sectors.append(flinfo_sector)

    def write_data(self, data):
        """Write raw data to dump file."""
        self.args.output.write(data)
        self.args.output.flush()

    def dump_flash(self):
        """Read all flash sectors using md."""
        if self.args.start and self.args.stop:
            start_offset = int(self.args.start, 16)
            end_offset = int(self.args.stop, 16)
        else:
            self.parse_flinfo()
            start_offset = int(self.sectors[0], 16)
            # the 0xffff below could probably be calculated from flinfo, but it just
            # makes sure we capture the entire contents of the last block
            end_offset = int(self.sectors[-1], 16) + 0xffff
        # in bytes
        flash_size = math.floor(end_offset - start_offset)
        self.util.print_console(
            "Dumping {0} bytes from 0x{1:x} ({1}) to 0x{2:x} ({2})".format(
                flash_size,
                start_offset,
                end_offset,
            )
        )
        iterable = range(start_offset, end_offset, 0x8)
        self.util.start_progress(iterable)
        for offset in iterable:
            self.util.write_serial(
                "read64 {0:#x}\n".format(offset)
            )
            data_match = False
            while(not data_match):
                read64_line = self.util.read_serial_line()
                data_match = re.search(self.read_re, read64_line)
            if data_match:
                self.util.update_progress(
                    offset,
                    0x8,
                    data_match.group(2),
                )
                self.write_data(self.util.hextobin(data_match.group(2)))

    def dump(self):
        """Dump the contents of flash to a file."""
        with self.args.output as outfile:
            self.util.print_console("Dumping firmware to {}".format(outfile.name))
            self.prepare_file()
            self.dump_flash()


if __name__ == "__main__":
    dumper = Dumper()
    dumper.dump()
