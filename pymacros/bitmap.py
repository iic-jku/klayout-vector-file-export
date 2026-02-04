# --------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 Martin Jan Köhler
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0-or-later
#--------------------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
import os
import tempfile
from typing import *
import unittest

import pya


@dataclass(slots=True)
class Bitmap:
    width: int
    height: int
    data: bytearray  # flat, row-major, 0 or 1 per pixel
    
    # ----------------------------------------
    # KLayout String format read/write
    # ----------------------------------------
    
    @classmethod
    def from_klayout_string(cls, s: str) -> Bitmap:
        """
        From the KLayout documentation ( https://www.klayout.de/doc-qt5/code/class_LayoutView.html#method36 )
        
        's' is a string describing the pattern. 
        It consists of one or more lines composed of '.' or '*' characters and separated by newline characters. 
        A '.' is for a missing pixel and '*' for a set pixel. The length of each line must be the same. 
        Blanks before or after each line are ignored.
        """
        
        lines = [
            line.strip()
            for line in s.splitlines()
            if line.strip()
        ]
        
        if not lines:
            return cls(0, 0, bytearray())
        
        width = len(lines[0])
        height = len(lines)
        data = bytearray(width * height)
        
        rows: list[bytearray] = []
        for y, line in enumerate(lines):
            if len(line) != width:
                raise ValueError(f"inconsistent line length on line {y}: "
                                 f"{len(line)} != {width}")

            row_offset = y * width
            for x, c in enumerate(line):
                if c == '*':
                    data[row_offset + x] = 1
                elif c == '.':
                    pass
                else:
                    raise ValueError(f"invalid character {c!r} on line {y}")
        
        return cls(width, height, data)
    
    def to_klayout_string(self) -> str:
        if self.width == 0 or self.height == 0:
            return ""

        lines: list[str] = []
        for y in range(self.height):
            row_offset = y * self.width
            line = ''.join(
                '*' if self.data[row_offset + x] else '.'
                for x in range(self.width)
            )
            lines.append(line)

        return "\n".join(lines)
        
    # ----------------------------------------
    # PBM (binary) read/write
    # ----------------------------------------
    
    @classmethod
    def from_pbm(cls, path: str) -> Bitmap:
        """
        Read a PBM (binary, P4) file into a Bitmap.
        """
        with open(path, 'rb') as f:
            # Read header
            magic = f.readline().strip()
            if magic != b'P4':
                raise ValueError(f"Unsupported PBM format {magic}")
            
            # Skip comments
            while True:
                line = f.readline()
                if not line.startswith(b'#'):
                    break
            
            # Width and height
            width_height = line.split()
            if len(width_height) != 2:
                # maybe width and height are on separate lines
                width_height += f.readline().split()
            width, height = map(int, width_height)
            
            # Read bitmap data
            data = bytearray(width * height)
            row_bytes = (width + 7) // 8
            for y in range(height):
                row_data = f.read(row_bytes)
                for x in range(width):
                    byte_idx = x // 8
                    bit_idx = 7 - (x % 8)
                    if row_data[byte_idx] & (1 << bit_idx):
                        data[y * width + x] = 1
            return cls(width, height, data)
    
    def to_pbm(self, path: str):
        """
        Write the bitmap to a PBM (binary, P4) file.
        """
        with open(path, 'wb') as f:
            f.write(f"P4\n{self.width} {self.height}\n".encode('ascii'))
            
            row_bytes = (self.width + 7) // 8
            for y in range(self.height):
                byte = 0
                bits_filled = 0
                row_offset = y * self.width
                for x in range(self.width):
                    bit = self.data[row_offset + x]
                    byte = (byte << 1) | (bit & 1)
                    bits_filled += 1
                    if bits_filled == 8:
                        f.write(bytes([byte]))
                        byte = 0
                        bits_filled = 0
                if bits_filled > 0:  # pad remaining bits
                    byte <<= (8 - bits_filled)
                    f.write(bytes([byte]))

    # ----------------------------------------
    # bitmap data accessors
    # ----------------------------------------
    
    def get(self, x: int, y: int) -> int:
        return self.data[y * self.width + x]
    
    def set(self, x: int, y: int, value: int):
        self.data[y * self.width + x] = 1 if value else 0

    
#--------------------------------------------------------------------------------

class BitmapTests(unittest.TestCase):
    def test_round_trip(self):
        s = """
            .*..
            *.**
            ..*.
            """        
        b = Bitmap.from_klayout_string(s)
        self.assertEqual('.*..\n*.**\n..*.', b.to_klayout_string())
        
    def test_whitespace_ignored(self):
        b = Bitmap.from_klayout_string("  .*.\n\n  ***  \n")
        self.assertEqual(3, b.width)
        self.assertEqual(2, b.height)
    
    def test_invalid_character(self):
        with self.assertRaises(ValueError):
            Bitmap.from_klayout_string(".*@\n***")

    def test_inconsistent_width(self):
        with self.assertRaises(ValueError):
            Bitmap.from_klayout_string("**.\n****")

    def test_empty_string(self):
        b = Bitmap.from_klayout_string("")
        self.assertEqual(0, b.width)
        self.assertEqual(0, b.height)
        self.assertEqual(bytearray(), b.data)
    
    def test_get_set(self):
        b = Bitmap.from_klayout_string("...\n...")
        b.set(1, 0, 1)
        self.assertEqual(1, b.get(1, 0))
        self.assertEqual(".*.\n...", b.to_klayout_string())

    def test_pbm_rount_trip(self):
        s = """
            .*..
            *.**
            ..*.
            """        
        original = Bitmap.from_klayout_string(s)
        
        # Write to a temporary PBM file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pbm") as tmp:
            path = tmp.name

        try:
            pbm = original.to_pbm(path)
            
            loaded = Bitmap.from_pbm(path)
            
            self.assertEqual('.*..\n*.**\n..*.', loaded.to_klayout_string())            
        finally:
            # os.remove(path)
            print(f"pbm path is {path}")
        

if __name__ == "__main__":
    unittest.main()
