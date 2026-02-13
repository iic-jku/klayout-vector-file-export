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
#--------------------------

from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
from typing import *

import pya

from bitmap import Bitmap


StippleString = str


@dataclass
class Stipple:
    stipple_string: StippleString
    bitmap: Bitmap
    
    @property
    def width(self) -> int:
        return self.bitmap.width
        
    @property
    def height(self) -> int:
        return self.bitmap.height

    @cached_property
    def id(self) -> str:
        return self.bitmap.to_compact_filename()        
        
    @classmethod
    def from_klayout_string(cls, stipple_string: StippleString) -> Stipple:
        bitmap = Bitmap.from_klayout_string(stipple_string)
        stipple = Stipple(stipple_string, bitmap)
        return stipple
        

@dataclass
class StipplePanel:
    stipple: Stipple
    width: int
    heigth: int
    painter_paths: List[pya.QPainterPath]