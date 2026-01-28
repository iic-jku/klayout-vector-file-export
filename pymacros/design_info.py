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
from typing import *
import unittest

import pya

from klayout_plugin_utils.layer_list_string import LayerList

from vector_file_export_settings import *


@dataclass
class DesignInfo:
    layout_view: pya.LayoutView
    cell: pya.Cell

    bbox: pya.DBox    
    dbu: float
    layer_indexes: List[int]
    settings: VectorFileExportSettings

    @classmethod
    def for_layout_view(cls, 
                        layout_view: pya.LayoutView,
                        settings: VectorFileExportSettings):
        def visible_layer_indexes() -> List[int]:
            idxs = []
            for lref in layout_view.each_layer():
                if lref.visible and lref.valid:
                    if lref.layer_index() == -1:  # hidden by the user
                        continue
                    idxs.append(lref.layer_index())
            return idxs

        cellview = layout_view.active_cellview()
        cell = cellview.cell             
        layout = cell.layout()
        
        layer_indexes: List[int]
        if settings.custom_layers == '':
            layer_indexes = visible_layer_indexes()
        else:
            layer_list_parse_result = LayerList.parse_layer_list_string(settings.custom_layers)
            if len(layer_list_parse_result.errors) == 0:
                layer_indexes = [layout.find_layer(l) for l in layer_list_parse_result.result.layers]
            else: 
                # TODO: report error
                layer_indexes = visible_layer_indexes()
        
        return DesignInfo(
            layout_view=layout_view,
            cell=cell,
            bbox=cell.dbbox(),
            dbu=layout.dbu,
            layer_indexes=layer_indexes,
            settings=settings
        )

    @property
    def width_um(self) -> float:
        return self.bbox.width()
        
    @property
    def height_um(self) -> float:
        return self.bbox.height()
    
    # Calculate minimum visible feature size at target DPI
    # pixels = inches * dpi, so µm_per_pixel = design_width_µm / (fig_width_inches * dpi)
    
    @cached_property
    def um_per_pixel(self) -> float:
        return self.width_um / (self.settings.fig_width_inch(self.width_um) * 72)
    
    @cached_property
    def min_feature_size_um(self):
        return self.um_per_pixel * 2  # Features smaller than 2 pixels won't be visible
    
    @cached_property
    def simplify_tolerance_um(self):
        return self.um_per_pixel * 0.5  # Simplify to half-pixel precision
    
    @property
    def pt_per_inch(self) -> float:
        return 72.0
        
    @cached_property
    def fig_width_pt(self) -> float:
        return self.settings.fig_width_inch(self.width_um) * self.pt_per_inch
    
    @cached_property
    def fig_height_pt(self) -> float:
        return self.scale_um_to_pt * self.height_um
    
    @property
    def mm_per_pt(self) -> float:
        return 0.35277777777777777
    
    @cached_property
    def fig_width_mm(self) -> float:
        return round(self.fig_width_pt * self.mm_per_pt, 6)
    
    @cached_property
    def scale_um_to_pt(self) -> float:
        return self.fig_width_pt / self.width_um
        
    @cached_property
    def scaling(self) -> float:
        return self.scale_um_to_pt * self.mm_per_pt * 1e3
        

#--------------------------------------------------------------------------------

class LayerListTests(unittest.TestCase):
    def test_scaling_1(self):
        settings = VectorFileExportSettings(
            file_format=VectorFileFormat.PDF,
            output_path='out.pdf',
            title='Title',
            page_format=pya.QPageSize.A4.to_i(),
            page_orientation=PageOrientation.PORTRAIT,
            content_scaling_style=ContentScaling.FIGURE_WIDTH_MM,
            content_scaling_value=127.0,  # 127mm!
            geometry_reduction=GeometryReduction.NONE,
            layer_output_style=LayerOutputStyle.SINGLE_PAGE,
            custom_layers=''
        )
    
        # bounding box 12.7µm x 6.96µm
        di = DesignInfo(layout_view=None,
                        cell=None,
                        bbox=pya.DBox(0, 0, 12.7, 6.96),
                        dbu=0.001,
                        layer_indexes=[],
                        settings=settings)

        self.assertEqual(12.7, di.width_um)
        self.assertEqual(6.96, di.height_um)
        self.assertEqual(127.0, di.fig_width_mm)
        self.assertEqual(10000.0, di.scaling)

    def test_scaling_2(self):
        settings = VectorFileExportSettings(
            file_format=VectorFileFormat.PDF,
            output_path='out.pdf',
            title='Title',
            page_format=pya.QPageSize.A4.to_i(),
            page_orientation=PageOrientation.PORTRAIT,
            content_scaling_style=ContentScaling.SCALING,
            content_scaling_value=10000.0,
            geometry_reduction=GeometryReduction.NONE,
            layer_output_style=LayerOutputStyle.SINGLE_PAGE,
            custom_layers=''
        )
    
        # bounding box 12.7µm x 6.96µm
        di = DesignInfo(layout_view=None,
                        cell=None,
                        bbox=pya.DBox(0, 0, 12.7, 6.96),
                        dbu=0.001,
                        layer_indexes=[],
                        settings=settings)

        self.assertEqual(12.7, di.width_um)
        self.assertEqual(6.96, di.height_um)
        self.assertEqual(127.0, di.fig_width_mm)
        self.assertEqual(10000.0, di.scaling)

#--------------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
        