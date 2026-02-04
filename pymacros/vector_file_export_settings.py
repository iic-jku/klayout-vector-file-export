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
    include_stipples: bool = False
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

        settings = VectorFileExportSettings()        
        if settings_str is not None:
            d = pya.AbstractMenu.unpack_key_binding(settings_str)
            
            file_format_str = d.get('file_format', None)
            if file_format_str is not None:
                settings.file_format = VectorFileFormat(file_format_str)
            
            output_path_str = d.get('output_path', None)
            if output_path_str is not None:
                settings.output_path = Path(output_path_str)
                
            title_str = d.get('title', None)
            if title_str is not None:
                settings.title = title_str
            
            page_format_str = d.get('page_format', None)
            if page_format_str is not None:
                settings.page_format = int(page_format_str)

            page_orientation_str = d.get('page_orientation', None)
            if page_orientation_str is not None:
                settings.page_orientation = PageOrientation(page_orientation_str)
                
            content_scaling_style_str = d.get('content_scaling_style', None)
            if content_scaling_style_str is not None:
                settings.content_scaling_style = ContentScaling(content_scaling_style_str)

            content_scaling_value_str = d.get('content_scaling_value', None)
            if content_scaling_value_str is not None:
                settings.content_scaling_value = float(content_scaling_value_str)

            color_mode_str = d.get('color_mode', None)
            if color_mode_str is not None:
                settings.color_mode = ColorMode(color_mode_str)

            include_background_color_str = d.get('include_background_color', None)
            if include_background_color_str is not None:
                settings.include_background_color = bool(int(include_background_color_str))

            include_stipples_str = d.get('include_stipples', None)
            if include_stipples_str is not None:
                settings.include_stipples = bool(int(include_stipples_str))

            font_family_str = d.get('font_family', None)
            if font_family_str is not None:
                settings.font_family = font_family_str

            font_size_mode_str = d.get('font_size_mode', None)
            if font_size_mode_str is not None:
                settings.font_size_mode = FontSizeMode(font_size_mode_str)

            font_size_pt_str = d.get('font_size_pt', None)
            if font_size_pt_str is not None:
                settings.font_size_pt = float(font_size_pt_str)

            font_size_percent_of_fig_width_str = d.get('font_size_percent_of_fig_width', None)
            if font_size_percent_of_fig_width_str is not None:
                settings.font_size_percent_of_fig_width = float(font_size_percent_of_fig_width_str)

            text_mode_str = d.get('text_mode', None)
            if text_mode_str is not None:
                settings.text_mode = TextMode(text_mode_str)

            text_layers_filter_enabled_str = d.get('text_layers_filter_enabled', None)
            if text_layers_filter_enabled_str is not None:
                settings.text_layers_filter_enabled = bool(int(text_layers_filter_enabled_str))

            text_layers_str = d.get('text_layers', None)
            if text_layers_str is not None:
                settings.text_layers = text_layers_str

            geometry_reduction_str = d.get('geometry_reduction', None)
            if geometry_reduction_str is not None:
                settings.geometry_reduction = GeometryReduction(geometry_reduction_str)

            layer_output_style_str = d.get('layer_output_style', None)
            if layer_output_style_str is not None:
                settings.layer_output_style = LayerOutputStyle(layer_output_style_str)

            layer_selection_mode_str = d.get('layer_selection_mode', None)
            if layer_selection_mode_str is not None:
                settings.layer_selection_mode = LayerSelectionMode(layer_selection_mode_str)

            custom_layers_str = d.get('custom_layers', None)
            if custom_layers_str is not None:
                settings.custom_layers = custom_layers_str

            return settings
                
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
            'include_stipples': str(int(self.include_stipples)),
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
    
