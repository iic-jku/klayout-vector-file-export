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

import subprocess
import tempfile
import os
from pathlib import Path
from typing import *
from xml.dom import minidom

import pya

from bitmap import Bitmap


class BitmapVectorizer:
    @staticmethod
    def convert_bitmap_to_svg(bitmap_path: Path,
                              svg_path: Path):
        """
        Convert a bitmap to a list of QPainterPath objects using Potrace.
        """
        subprocess.run(["potrace", bitmap_path, "-s", "-o", svg_path], check=True)
    
    @staticmethod
    def convert_svg_to_qpainter_paths(svg_path: Path) -> List[pya.QPainterPath]:
        doc = minidom.parse(svg_path)
        path_strings = [path.getAttribute("d") for path in doc.getElementsByTagName("path")]
        doc.unlink()
        
        paths: List[pya.QPainterPath] = []
        
        for d in path_strings:
            path = pya.QPainterPath()
            # Very simple SVG parser: only supports 'M', 'L', 'Z' (you can expand to curves later)
            commands = d.split()
            i = 0
            while i < len(commands):
                cmd = commands[i]
                if cmd == 'M':
                    x = float(commands[i+1])
                    y = float(commands[i+2])
                    path.moveTo(pya.QPointF(x, -y))  # Flip Y
                    i += 3
                elif cmd == 'L':
                    x = float(commands[i+1])
                    y = float(commands[i+2])
                    path.lineTo(pya.QPointF(x, -y))
                    i += 3
                elif cmd == 'Z':
                    path.closeSubpath()
                    i += 1
                else:
                    i += 1  # Skip unknown commands
            paths.append(path)
        
        return paths
