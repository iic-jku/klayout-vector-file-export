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
from enum import StrEnum
from functools import cached_property
import os
from pathlib import Path
from typing import *

import pya

from klayout_plugin_utils.debugging import debug, Debugging
from klayout_plugin_utils.str_enum_compat import StrEnum


CONFIG_KEY__VECTOR_FILE_EXPORT_SETTINGS = 'klayout_vector_file_export_settings'

#--------------------------------
# TODO: Color / B+W
#
# TODO: Layer Selection
#    Use visible layers
#    Use all layers
#    Custom layers
#--------------------------------

class VectorFileFormat(StrEnum):
    PDF = '.pdf'
    SVG = '.svg'


class LayerOutputStyle(StrEnum):
    SINGLE_PAGE = 'single_page'
    PAGE_PER_LAYER = 'page_per_layer'


class PageOrientation(StrEnum):
    PORTRAIT = 'portrait'
    LANDSCAPE = 'landscape'

class ContentScaling(StrEnum):
    FIGURE_WIDTH_MM = 'figure_width_mm'
    SCALING = 'scaling'

class GeometryReduction(StrEnum):
    NONE = 'none'
    OMIT_SMALL_POLYGONS = 'omit_small_polygons'

@dataclass
class VectorFileExportSettings:
    file_format: VectorFileFormat = VectorFileFormat.PDF
    output_path: str | Path = ""
    title: str = "KLayout Vector Export"
    page_format: int = pya.QPageSize.A4.to_i()
    page_orientation: PageOrientation = PageOrientation.PORTRAIT
    content_scaling_style: ContentScaling = ContentScaling.FIGURE_WIDTH_MM
    content_scaling_value: float = 120.0
    geometry_reduction: GeometryReduction = GeometryReduction.OMIT_SMALL_POLYGONS
    layer_output_style: LayerOutputStyle = LayerOutputStyle.SINGLE_PAGE
    custom_layers: str = ""   # empty string means all visible layers
    
    def page_size(self) -> pya.QPageSize:
        return pya.QPageSize(pya.QPageSize.PageSizeId(self.page_format))
    
    def fig_width_inch(self, width_um: float) -> float:
        match self.content_scaling_style:
            case ContentScaling.FIGURE_WIDTH_MM:
                return self.content_scaling_value / 25.4
            case ContentScaling.SCALING:
                return width_um * self.content_scaling_value
            case _:
                raise NotImplementedError(f"Unhandled enum case {self.content_scaling_style}")
    
    @classmethod
    def load(cls) -> VectorFileExportSettings:
        if Debugging.DEBUG:
            debug("VectorFileExportSettings.load")
            
        mw = pya.MainWindow.instance()
        settings_str = mw.get_config(CONFIG_KEY__VECTOR_FILE_EXPORT_SETTINGS)
        
        if settings_str is None:
            return VectorFileExportSettings()
        else:
            d = pya.AbstractMenu.unpack_key_binding(settings_str)
            
            return VectorFileExportSettings(
                file_format=d['file_format'],
                output_path=Path(d['output_path']),
                title=d['title'],
                page_format=int(d['page_format']),
                page_orientation=PageOrientation(d['page_orientation']),
                content_scaling_style=ContentScaling(d['content_scaling_style']),
                content_scaling_value=float(d['content_scaling_value']),
                geometry_reduction=GeometryReduction(d['geometry_reduction']),
                layer_output_style=LayerOutputStyle(d['layer_output_style']),
                custom_layers=d['custom_layers']
            )
    
    def save(self):
        if Debugging.DEBUG:
            debug("VectorFileExportSettings.save")
            
        mw = pya.MainWindow.instance()
            
        settings_str = pya.AbstractMenu.pack_key_binding(self.dict())
        mw.set_config(CONFIG_KEY__VECTOR_FILE_EXPORT_SETTINGS, settings_str)
    
    def dict(self) -> Dict[str, str]:
        return {
            'file_format': self.file_format.value,
            'output_path': str(self.output_path),
            'title': str(self.title),
            'page_format': self.page_format,
            'page_orientation': self.page_orientation.value,
            'content_scaling_style': self.content_scaling_style.value,
            'content_scaling_value': str(self.content_scaling_value),
            'geometry_reduction': self.geometry_reduction.value,
            'layer_output_style': self.layer_output_style.value,
            'custom_layers': self.custom_layers
        }
    
