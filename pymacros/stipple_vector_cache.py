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
from functools import cached_property
import os
from pathlib import Path
from typing import *

import pya

from bitmap import Bitmap
from bitmap_vectorizer import BitmapVectorizer


StippleString = str


class StippleVectorCache:
    @classmethod
    def instance(cls) -> StippleVectorCache:
        if not hasattr(cls, '_instance'):
            cls._instance = StippleVectorCache()
        return cls._instance

    @cached_property
    def cache_base_path(self) -> Path:
        KLAYOUT_HOME = Path(os.getenv('KLAYOUT_HOME') or Path.home() / '.klayout')
        BASE_PATH = KLAYOUT_HOME / 'plugin_data' / 'klayout_vector_file_export' / 'stipple_cache'
        return BASE_PATH
    
    def __init__(self):
        self._svg_cache: Dict[StippleString, Path] = {}
        self._paint_path_cache: Dict[StippleString, List[pya.QPainterPath]] = {}

    def _get_or_create_svg_for_stipple_string(self, stipple_string: StippleString) -> Path:
        svg_path = self._svg_cache.get(stipple_string, None)
        if svg_path is not None:
            return svg_path
        
        bitmap = Bitmap.from_klayout_string(stipple_string)
        stipple_id = bitmap.to_compact_filename()
        

        stipple_dir = self.cache_base_path / stipple_id
        svg_path = stipple_dir / Path(f"{stipple_id}.svg")
        
        if not svg_path.exists() or not svg_path.is_file():  # load persisted SVG
            stipple_dir.mkdir(parents=True, exist_ok=True)
            bmp_path = stipple_dir / Path(f"{stipple_id}.pbm")
            bitmap.to_pbm(bmp_path)
            BitmapVectorizer.convert_bitmap_to_svg(bmp_path, svg_path)
            
        self._svg_cache[stipple_string] = svg_path
        return svg_path
    
    def painter_paths_for_stipple(self, stipple_string: StippleString) -> List[pya.QPainterPath]:
        # check in-memory painter cache first
        paths = self._paint_path_cache.get(stipple_string)
        if paths is not None:
            return paths
        
        svg_path = self._get_or_create_svg_for_stipple_string(stipple_string)
        paths = BitmapVectorizer.convert_svg_to_qpainter_paths(svg_path)
        self._paint_path_cache[stipple_string] = paths
        return paths
