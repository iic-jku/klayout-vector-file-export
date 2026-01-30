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


class ColorMode(StrEnum):
    BLACK_AND_WHITE = 'Black & White'
    GREYSCALE = 'Greyscale'
    COLOR = 'Color'


class FontSizeMode(StrEnum):
    ABSOLUTE = 'absolute'
    PERCENT_OF_FIG_WIDTH = 'percent_of_fig_width'


class TextMode(StrEnum):
    NONE = 'none'
    ALL_VISIBLE = 'all_visible'
    ONLY_TOP_CELL = 'only_top_cell'
    

class GeometryReduction(StrEnum):
    NONE = 'none'
    OMIT_SMALL_POLYGONS = 'omit_small_polygons'


class LayerSelectionMode(StrEnum):
    ALL_VISIBLE_LAYERS = 'all_visible_layers'
    CUSTOM_LAYER_LIST = 'custom_layer_list'


@dataclass
class VectorFileExportSettings:
    file_format: VectorFileFormat = VectorFileFormat.PDF
    output_path: str | Path = ""
    title: str = "KLayout Vector Export"
    page_format: int = pya.QPageSize.A4.to_i()
    page_orientation: PageOrientation = PageOrientation.PORTRAIT
    content_scaling_style: ContentScaling = ContentScaling.FIGURE_WIDTH_MM
    content_scaling_value: float = 120.0
    color_mode: ColorMode = ColorMode.BLACK_AND_WHITE
    include_background_color: bool = True
    font_family: str = 'monospace'
    font_size_mode: FontSizeMode = FontSizeMode.PERCENT_OF_FIG_WIDTH
    font_size_pt: float = 6.0
    font_size_percent_of_fig_width: float = 1.0
    text_mode: TextMode = TextMode.ALL_VISIBLE
    text_layers_filter_enabled: bool = False
    text_layers: str = ''
    geometry_reduction: GeometryReduction = GeometryReduction.OMIT_SMALL_POLYGONS
    layer_output_style: LayerOutputStyle = LayerOutputStyle.SINGLE_PAGE
    layer_selection_mode: LayerSelectionMode = LayerSelectionMode.ALL_VISIBLE_LAYERS
    custom_layers: str = ''   # only relevant for LayerSelectionMode.CUSTOM_LAYER_LIST
    
    def page_size(self) -> pya.QPageSize:
        return pya.QPageSize(pya.QPageSize.PageSizeId(self.page_format))
    
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
                file_format=VectorFileFormat(d['file_format']),
                output_path=Path(d['output_path']),
                title=d['title'],
                page_format=int(d['page_format']),
                page_orientation=PageOrientation(d['page_orientation']),
                content_scaling_style=ContentScaling(d['content_scaling_style']),
                content_scaling_value=float(d['content_scaling_value']),
                color_mode=ColorMode(d['color_mode']),
                include_background_color=bool(int(d['include_background_color'])),
                font_family=d['font_family'],
                font_size_mode=FontSizeMode(d['font_size_mode']),
                font_size_pt=float(d['font_size_pt']),
                font_size_percent_of_fig_width=float(d['font_size_percent_of_fig_width']),
                text_mode=TextMode(d['text_mode']),
                text_layers_filter_enabled=bool(int(d['text_layers_filter_enabled'])),
                text_layers=d['text_layers'],
                geometry_reduction=GeometryReduction(d['geometry_reduction']),
                layer_output_style=LayerOutputStyle(d['layer_output_style']),
                layer_selection_mode=LayerSelectionMode(d['layer_selection_mode']),
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
            'color_mode': self.color_mode.value,
            'include_background_color': str(int(self.include_background_color)),
            'font_family': self.font_family,
            'font_size_mode': self.font_size_mode.value,
            'font_size_pt': str(self.font_size_pt),
            'font_size_percent_of_fig_width': str(self.font_size_percent_of_fig_width),
            'text_mode': self.text_mode.value,
            'text_layers_filter_enabled': str(int(self.text_layers_filter_enabled)),
            'text_layers': self.text_layers,
            'geometry_reduction': self.geometry_reduction.value,
            'layer_output_style': self.layer_output_style.value,
            'layer_selection_mode': self.layer_selection_mode.value,
            'custom_layers': self.custom_layers
        }
    
