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
from exception import ExportCancelledError
from progress_reporter import ProgressReporter
from stipple import Stipple, StippleString, StipplePanel
from svg_painter import convert_svg_to_qpainter_paths


@dataclass(frozen=True) 
class StippleCacheKey:
    tile_stipple_id: str
    width: int
    height: int


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
        self._painter_path_cache: Dict[StippleCacheKey, List[pya.QPainterPath]] = {}

    def panelize(self, 
                 stipple: Stipple,
                 min_w: int, 
                 min_h: int,
                 progress_reporter: Optional[ProgressReporter]) -> StipplePanel:
        panel_bitmap = stipple.bitmap.panelize(min_w, min_h)
        
        key = StippleCacheKey(stipple.id, panel_bitmap.width, panel_bitmap.height)
        
        stipple_panel_dir = self.cache_base_path / stipple.id / f"{panel_bitmap.width}x{panel_bitmap.height}"
        stipple_panel_dir.mkdir(parents=True, exist_ok=True)
        
        paths = self._painter_path_cache.get(key)
        if paths is None:
            svg_path = self._get_or_create_svg_for_bitmap(panel_bitmap, stipple_panel_dir)
            
            paths = convert_svg_to_qpainter_paths(svg_path, progress_reporter)
            
            self._painter_path_cache[key] = paths
        
        return StipplePanel(stipple, panel_bitmap.width, panel_bitmap.height, paths)
    
    def _get_or_create_svg_for_bitmap(self, 
                                      bitmap: Bitmap,
                                      run_dir: Path) -> Path:
        svg_path = run_dir / Path('stipple.svg')
        
        if not svg_path.exists() or not svg_path.is_file():  # load persisted SVG
            bmp_path = run_dir / Path('stipple.pbm')
            bmp_preproc_path = run_dir / Path('stipple_preprocessed.pbm')
            bitmap.to_pbm(bmp_path)
            BitmapVectorizer.convert_bitmap_to_svg(bmp_path, bmp_preproc_path, svg_path)
            
        return svg_path
    
