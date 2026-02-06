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
from functools import cached_property
import os
from pathlib import Path
from typing import *

import pya

from bitmap import Bitmap
from bitmap_vectorizer import BitmapVectorizer
from svg_painter import convert_svg_to_qpainter_paths


StippleString = str


@dataclass(slots=True)
class Stipple:
    stipple_string: StippleString
    bitmap: Bitmap
    painter_paths: List[pya.QPainterPath]


class StippleCache:
    @classmethod
    def instance(cls) -> StippleCache:
        if not hasattr(cls, '_instance'):
            cls._instance = StippleCache()
        return cls._instance

    @cached_property
    def cache_base_path(self) -> Path:
        KLAYOUT_HOME = Path(os.getenv('KLAYOUT_HOME') or Path.home() / '.klayout')
        BASE_PATH = KLAYOUT_HOME / 'plugin_data' / 'klayout_vector_file_export' / 'stipple_cache'
        return BASE_PATH
    
    def __init__(self):
        self._svg_cache: Dict[StippleString, Path] = {}
        self._stipple_cache: Dict[StippleString, Stipple] = {}

    def _get_or_create_svg_for_stipple_string(self, stipple_string: StippleString) -> Path:
        svg_path = self._svg_cache.get(stipple_string, None)
        if svg_path is not None:
            return svg_path
        
        bitmap = Bitmap.from_klayout_string(stipple_string)
        stipple_id = bitmap.to_compact_filename()        
        # print(f"stipple string: {stipple_string}, stipple_id: {stipple_id}")
        
        stipple_dir = self.cache_base_path / stipple_id
        svg_path = stipple_dir / Path('stipple.svg')
        
        if not svg_path.exists() or not svg_path.is_file():  # load persisted SVG
            stipple_dir.mkdir(parents=True, exist_ok=True)
            bmp_path = stipple_dir / Path('stipple.pbm')
            bmp_preproc_path = stipple_dir / Path('stipple_preprocessed.pbm')
            bitmap.to_pbm(bmp_path)
            BitmapVectorizer.convert_bitmap_to_svg(bmp_path, bmp_preproc_path, svg_path)
            
        self._svg_cache[stipple_string] = svg_path
        return svg_path
    
    def _painter_paths_for_stipple(self, stipple_string: StippleString) -> List[pya.QPainterPath]:
        svg_path = self._get_or_create_svg_for_stipple_string(stipple_string)
        paths = convert_svg_to_qpainter_paths(svg_path)
        return paths

    def stipple_for_string(self, stipple_string: StippleString) -> Stipple:
        # check in-memory cache first
        stipple = self._stipple_cache.get(stipple_string)
        if stipple is not None:
            return stipple
        
        bitmap = Bitmap.from_klayout_string(stipple_string)        
        paths = self._painter_paths_for_stipple(stipple_string)
        stipple = Stipple(stipple_string, bitmap, paths)
        
        self._stipple_cache[stipple_string] = stipple
        return stipple
        
        
    