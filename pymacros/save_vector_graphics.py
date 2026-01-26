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

import pya

from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
import os
from pathlib import Path
from typing import *

#
# Export Options ideas
#
# Format: SVG / PDF
#
# Color / B+W
#
# Layer Selection
#    Use visible layers
#    Use all layers
#    Custom layers
# 
# 
#

class VectorFileFormat(StrEnum):
    PDF = '.pdf'
    SVG = '.svg'


@dataclass
class VectorFileExportSettings:
    format: VectorFileFormat
    dpi: int
    fig_width_inch: float
    output_path: str | Path
    title: str
    
    @property
    def resolution(self) -> int:
        return int(self.dpi)

@dataclass
class DesignInfo:
    bbox: pya.DBox
    dbu: float
    layer_indexes: List[int]
    settings: VectorFileExportSettings

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
        return max(self.width_um, self.height_um) / (self.settings.fig_width_inch * self.settings.dpi)
        
    @cached_property
    def min_feature_size_um(self):
        return self.um_per_pixel * 2  # Features smaller than 2 pixels won't be visible
        
    @cached_property
    def simplify_tolerance_um(self):
        return self.um_per_pixel * 0.5  # Simplify to half-pixel precision



class VectorFileExporter:
    def __init__(self):
        pass
        
    @property
    def view(self):
        return pya.LayoutView.current()

    @property
    def cell_view(self) -> pya.CellView:
        return self.view.active_cellview()

    @property
    def layout(self) -> pya.Layout:
        return self.cell_view.layout()
        
    @property
    def dbu(self) -> float:
        return self.layout.dbu

    def prepare_painter(self, 
                        settings: VectorFileExportSettings, 
                        design_info: DesignInfo) -> pya.QPainter:
        painter: pya.QPainter
    
        output_path = Path(settings.output_path).resolve()
    
        bbox = design_info.bbox
    
        match settings.format:
            case VectorFileFormat.PDF:
                pdf = pya.QPdfWriter(str(output_path))
                pdf.setPageSize(pya.QPagedPaintDevice.A4)
                pdf.setResolution(settings.resolution)
                pdf.setTitle(settings.title)
                painter = pya.QPainter(pdf.asQPagedPaintDevice())
                self._pdf = pdf
            
            case VectorFileFormat.SVG:
                svg = pya.QSvgGenerator()
                svg.setFileName(str(output_path))
                svg.setResolution(settings.resolution)
                svg.setTitle(settings.title)
                svg.setViewBox(pya.QRectF(
                    bbox.left, 
                    bbox.bottom, # Note: SVG Y=0 is top; but we flip in the painter
                    bbox.width(), 
                    bbox.height()))
                    
                # NOTE: we have unit=1µm, SVG wants unit=1mm
                    
                # TODO: clean this up
                svg.setViewBox(pya.QRectF(
                    0, 
                    0,
                    bbox.width() / 1000,
                    bbox.height() / 1000))
                painter = pya.QPainter(svg)
                self._svg = svg
                
            case _:
                raise NotImplementedError(f"Unexpected enum case {settings.format}")
        
        pen = pya.QPen(pya.QColor('black'))
        pen.setWidthF(self.dbu)
        # brush = pya.QBrush(pya.QColor(200, 200, 200))
        painter.setPen(pen)
        # painter.setBrush(brush)
        
        fontsize_um = max(4, min(8, design_info.bbox.width() / 50))
        
        # 1 pt == 0,35278 mm == 352,78 um
        fontsize_pt = fontsize_um / 352.78
        
        font = pya.QFont()
        font.setFamily('monospace')
        font.setPointSizeF(fontsize_pt)
        painter.setFont(font)
        
        # move origin to bottom-left of bbox
        painter.translate(-bbox.left, -bbox.bottom)        
        painter.scale(1, -1)  # flip Y-axis
        # optional: move origin again if needed
        painter.translate(0, -bbox.height())
        
        return painter

    def paint_layers(self, 
                     painter: pya.QPainter,
                     design_info: DesignInfo):
        top_cell = self.cell_view.cell
        dbu = self.dbu
        bbox = design_info.bbox
        
        def draw_text(self, 
                      pos: pya.QPointF, 
                      text: str):
            painter.save()
            painter.scale(1, -1)
            painter.drawText(pos, text)
            painter.restore()
        
        for lyr in design_info.layer_indexes:
            iter = top_cell.begin_shapes_rec(lyr)
            while not iter.at_end():
                sh = iter.shape()
                print(f"lyr {lyr}, sh = {sh}")
            
                if sh.is_box():
                    b = sh.dbox.transformed(iter.dtrans())
                    rect = pya.QRectF(b.left, b.bottom, b.width(), b.height())
                    painter.drawRect(rect)
                elif sh.is_polygon():
                    p = sh.dpolygon.transformed(iter.dtrans())
                    path = pya.QPainterPath()
                    pts = p.each_point_hull()
                    
                    first = next(pts)
                    path.moveTo(pya.QPointF(first.x, first.y))
                    for p in pts:
                        path.lineTo(pya.QPointF(p.x, p.y))
                    path.closeSubpath()
                    painter.drawPath(path)
                elif sh.is_path():
                    p = sh.path
                    # TODO
                    pass
                elif sh.is_text():
                    t = sh.text
                    disp = sh.text_trans.disp
                    pos = pya.QPointF(disp.x * dbu, - disp.y * dbu)
                    draw_text(painter, pos, sh.text_string)
                    
                iter.next()

    def visible_layer_indexes(self) -> List[int]:
        idxs = []
        for lref in self.view.each_layer():
            if lref.visible and lref.valid:
                if lref.layer_index() == -1:  # hidden by the user
                    continue
                # print(f"layer is visible, name={lref.name}, idx={lref.layer_index()}, "
                #       f"marked={lref.marked} cellview={lref.cellview()}, "
                #      f"source={lref.source}")
                idxs.append(lref.layer_index())
        return idxs
    
    def export(self):
        layer_indexes = self.visible_layer_indexes()

        top_cell = self.cell_view.cell
        dbu = self.dbu
        bbox = top_cell.dbbox()
                
        # format = VectorFileFormat.SVG
        format = VectorFileFormat.PDF
        
        settings = VectorFileExportSettings(
            format=format,
            dpi=300,
            fig_width_inch=10,
            output_path=os.path.join(os.environ['HOME'], f"out{format.value}"),
            title=f"KLayout Layer Export")
        
        design_info = DesignInfo(bbox=bbox,
                                 dbu=dbu,
                                 layer_indexes=layer_indexes,
                                 settings=settings)
        
        painter = self.prepare_painter(settings, design_info)
        try:
            self.paint_layers(painter, design_info)
        finally:
            painter.end()


exporter = VectorFileExporter()
exporter.export()


