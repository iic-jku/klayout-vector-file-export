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

from dataclasses import dataclass
import subprocess
import tempfile
import os
from pathlib import Path
import sys

import pya

from klayout_plugin_utils.str_enum_compat import StrEnum

from bitmap import Bitmap


class TurnPolicy(StrEnum):
    MINORITY = 'minority'
    

@dataclass
class BitmapVectorizerSettings:
    # preprocessing options
    hpf: int = 4  # high pass filter, 0 to turn off
    scale_factor: int = 2        # equivalent to PotraceDrag "Scale"
    threshold: int = 128         # binarization threshold (0-255)
    
    # tracer settings
    turdsize: int = 2            # ignore tiny speckles
    alphamax: float = 0.0        # disable smoothing
    opttolerance: float = 0.0    # disable curve optimization
    turnpolicy: TurnPolicy = TurnPolicy.MINORITY   # Potrace corner policy


class BitmapVectorizer:
    @staticmethod
    def convert_bitmap_to_svg(input_bitmap_path: Path,
                              preprocessed_bitmap_path: Path,
                              svg_path: Path,
                              settings: BitmapVectorizerSettings = BitmapVectorizerSettings()):
        """
        Convert a bitmap to a list of QPainterPath objects using Potrace.
        """
        
        # -----------------------------
        # Load and preprocess image
        # -----------------------------

        mkbitmap_cmd = [
            'mkbitmap',
            '--output', str(preprocessed_bitmap_path.resolve()),
        ]

        if settings.hpf <= 0:
            mkbitmap_cmd += ['--nofilter']
        else:
            mkbitmap_cmd += ['--filter', str(settings.hpf)]
        
        mkbitmap_cmd += [
            '--threshold', str(float(settings.threshold) / 256.0),
            '--scale', str(settings.scale_factor),
            '--cubic',
            str(input_bitmap_path.resolve())
        ]

        subprocess.run(mkbitmap_cmd, check=True)
        
        # -----------------------------
        # Run Potrace CLI
        # -----------------------------
        
        potrace_cmd = [
            'potrace', 
            str(preprocessed_bitmap_path),
            '--svg', 
            '--output', str(svg_path.resolve()),
            '--turdsize', str(settings.turdsize),
            '--alphamax', str(settings.alphamax),
            '--opttolerance', str(settings.opttolerance),
            '--turnpolicy', settings.turnpolicy.value
        ]
        
        subprocess.run(potrace_cmd, check=True)
