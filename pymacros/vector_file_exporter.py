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

from klayout_plugin_utils.debugging import debug, Debugging

from progress_reporter import ProgressReporter
from vector_file_export_settings import *


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
        return self.scale * self.height_um
    
    @cached_property
    def scale(self) -> float:
        return self.fig_width_pt / self.width_um
        

class ExportCancelledError(BaseException):
    """Raised when an export operation is cancelled by the user."""
    pass
        

class VectorFileExporter:
    def __init__(self, 
                 layout_view: pya.LayoutView,
                 settings: VectorFileExportSettings,
                 progress_reporter: Optional[ProgressReporter]):
        self.layout_view = layout_view
        self.settings = settings
        self.progress_reporter = progress_reporter
        
        layer_indexes: List[int]
        if self.settings.custom_layers == '':
            layer_indexes = self.visible_layer_indexes()
        else:
            layer_indexes
        
        self.design_info = DesignInfo(bbox=self.cell_view.cell.dbbox(),
                                      dbu=self.dbu,
                                      layer_indexes=layer_indexes,
                                      settings=settings)
    
    @property
    def cell_view(self) -> pya.CellView:
        return self.layout_view.active_cellview()

    @property
    def layout(self) -> pya.Layout:
        return self.cell_view.layout()
        
    @property
    def dbu(self) -> float:
        return self.layout.dbu

    def visible_layer_indexes(self) -> List[int]:
        idxs = []
        for lref in self.layout_view.each_layer():
            if lref.visible and lref.valid:
                if lref.layer_index() == -1:  # hidden by the user
                    continue
                # print(f"layer is visible, name={lref.name}, idx={lref.layer_index()}, "
                #       f"marked={lref.marked} cellview={lref.cellview()}, "
                #      f"source={lref.source}")
                idxs.append(lref.layer_index())
        return idxs
    
    def create_painter(self) -> pya.QPainter:
        painter: pya.QPainter
    
        output_path = Path(self.settings.output_path).resolve()
    
        bbox = self.design_info.bbox
        page_size: pya.QPageSize = self.settings.page_size()

        match self.settings.file_format:
            case VectorFileFormat.PDF:
                pdf = pya.QPdfWriter(str(output_path))
                pdf.setResolution(72)
                pdf.setTitle(self.settings.title)
                dev = pdf.asQPagedPaintDevice()
                dev.setPageSize(page_size)
                match self.settings.page_orientation:
                    case PageOrientation.PORTRAIT:
                        dev.setPageOrientation(pya.QPageLayout.Portrait)
                    case PageOrientation.LANDSCAPE:
                        dev.setPageOrientation(pya.QPageLayout.Landscape)
                    case _:
                        raise NotImplementedError()
                painter = pya.QPainter(dev)
                self._pdf = pdf
            
            case VectorFileFormat.SVG:
                svg = pya.QSvgGenerator()
                svg.setFileName(str(output_path))
                svg.setResolution(72)
                svg.setTitle(self.settings.title)
                painter = pya.QPainter(svg)
                self._svg = svg
                
            case _:
                raise NotImplementedError(f"Unhandled enum case {self.settings.format}")
        
        return painter

    def prepare_painter(self, painter: pya.QPainter):
        pen = pya.QPen(pya.QColor('black'))
        pen.setWidthF(self.dbu)
        painter.setPen(pen)

        # brush = pya.QBrush(pya.QColor(200, 200, 200))
        # painter.setBrush(brush)
        
        fontsize_pt = 0.01 * self.design_info.fig_width_pt  # ~1% of figure width
        
        font = pya.QFont()
        font.setFamily('monospace')
        font.setPointSizeF(fontsize_pt)
        painter.setFont(font)
        
        page_size = self.settings.page_size()
        page_size_pt = page_size.sizePoints()
        
        width: float
        height: float
        
        match self.settings.page_orientation:
            case PageOrientation.PORTRAIT:
                width = page_size_pt.width
                height = page_size_pt.height
            case PageOrientation.LANDSCAPE:
                width = page_size_pt.height
                height = page_size_pt.width
            case _:
                raise NotImplementedError()
        
        offset_x = (width - self.design_info.fig_width_pt) / 2
        offset_y = (height - self.design_info.fig_height_pt) / 2
        
        # print(f"Bounding box: {design_info.width_um} x {design_info.height_um} µm")
        # print(f"Target bounding box: {design_info.fig_width_pt:.2f} x {design_info.fig_height_pt:.2f} pt  (scale {design_info.scale:.6f})")
        # page_size_mm = page_size.size(pya.QPageSize_Unit.Millimeter)
        # print(f"Page size: {page_size_mm.width} x {page_size_mm.height} mm "
        #       f"({page_size_pt.width} x {page_size_pt.height} pt)")
        
        # center on page
        painter.translate(offset_x, offset_y + self.design_info.fig_height_pt)
        
        # flip Y (PDF Y is down, layout Y is up)
        painter.scale(self.design_info.scale, -self.design_info.scale)
        
        # optional: move origin again if needed
        # painter.translate(0, -bbox.height())
        painter.translate(-self.design_info.bbox.left, -self.design_info.bbox.bottom)

    def draw_shape(self,
                   painter: pya.QPainter,
                   shape: pya.Shape,
                   trans: pya.DTrans) -> bool:
        dbu = self.dbu
        font_metrics = pya.QFontMetrics(painter.font)
        def draw_text(shape: pya.Shape):
            text = shape.text
                      
            disp = shape.text_trans.disp
            world_pos_um = pya.QPointF(disp.x * dbu, - disp.y * dbu)
            
            t = painter.worldTransform
            # Remove Y flip
            t_no_flip = pya.QTransform(
                t.m11(),  t.m12(),  0,
                t.m21(), -t.m22(),  0,
                t.dx(),   t.dy()
            )
            device_pos = t_no_flip.map(world_pos_um)

            text_rect = font_metrics.boundingRect(text.string)
            x = device_pos.x
            y = device_pos.y
            
            match text.halign:
                case pya.Text.HAlignLeft:
                    pass
                case pya.Text.HAlignCenter:
                    x -= text_rect.width / 2
                case pya.Text.HAlignRight:
                    x -= text_rect.width
            
            match text.valign:
                case pya.Text.VAlignTop:
                    y -= font_metrics.ascent()
                case pya.Text.VAlignCenter:
                    y += text_rect.height / 2 - font_metrics.descent()
                case pya.Text.VAlignBottom:
                    y += text_rect.height - font_metrics.descent()
            
            painter.save()
            painter.resetTransform()  # no scaling, no flipping
            painter.drawText(pya.QPointF(x, y), text.string)
            painter.restore()
        
        def draw_polygon(p: pya.DPolygon):
            p = shape.dpolygon.transformed(trans)
            path = pya.QPainterPath()
            pts = p.each_point_hull()
            
            first = next(pts)
            path.moveTo(pya.QPointF(first.x, first.y))
            for p in pts:
                path.lineTo(pya.QPointF(p.x, p.y))
            path.closeSubpath()
            painter.drawPath(path)
        
        if shape.is_box()\
           or shape.is_polygon()\
           or shape.is_path():
            bbox = shape.dbbox()
            
            # Skip small shapes
            if bbox.width() < self.design_info.min_feature_size_um \
               or bbox.height() < self.design_info.min_feature_size_um:
                # NOTE: do not log, hotspot
                # if Debugging.DEBUG:
                #    debug(f"VectorFileExporter.draw_shape: {shape} is too small ({bbox.width()} x {bbox.height()} µm)")
                return False
        
        if shape.is_box():
            b = shape.dbox.transformed(trans)
            rect = pya.QRectF(b.left, b.bottom, b.width(), b.height())
            painter.drawRect(rect)
        elif shape.is_polygon():
            draw_polygon(shape.dpolygon)
        elif shape.is_path():
            draw_polygon(shape.dpolygon)
        elif shape.is_text():
            draw_text(shape)
        else:
            return False
        return True

    def paint_layers(self, painter: pya.QPainter, preview_mode: bool):
        top_cell = self.cell_view.cell
        dbu = self.dbu
        bbox = self.design_info.bbox
                
        new_page_needed = False
        
        num_layers = len(self.design_info.layer_indexes)
        exported_layers = 0
        if self.progress_reporter is not None:
            self.progress_reporter.begin_progress(maximum=num_layers)
            
        max_preview_shapes = 1000
        if preview_mode:
            painter.drawRect(pya.QRectF(bbox.left, bbox.bottom, bbox.width(), bbox.height()))
            
        drawn_shapes = 0
        for lyr in self.design_info.layer_indexes:
            found_shapes_on_layer = False
            
            iter = top_cell.begin_shapes_rec(lyr)
            if preview_mode:
                iter.min_depth = 0
                iter.max_depth = 1
            else:
                iter.min_depth = max(self.layout_view.min_hier_levels-1, 0)
                iter.max_depth = max(self.layout_view.max_hier_levels-1, 0)
            
            while not iter.at_end():
                sh = iter.shape()
                ### print(f"lyr {lyr}, sh = {sh}")

                if new_page_needed:
                    self._pdf.newPage()
                    new_page_needed = False
                
                found_shapes = self.draw_shape(painter, sh, iter.dtrans())
                found_shapes_on_layer = found_shapes_on_layer or found_shapes
                
                if preview_mode and found_shapes:
                    drawn_shapes += 1
                    if drawn_shapes >= max_preview_shapes:
                        return
                
                iter.next()
                
                if self.progress_reporter is not None:
                    if self.progress_reporter.was_canceled():
                        raise ExportCancelledError()
                
            exported_layers += 1
            if self.progress_reporter is not None:
                self.progress_reporter.progress(dict(total_layers=num_layers, exported_layers=exported_layers))
            
            if found_shapes_on_layer\
               and self.settings.layer_output_style == LayerOutputStyle.PAGE_PER_LAYER:
                new_page_needed = found_shapes
            else:
                new_page_needed = False

    def render_preview(self, dpi: int) -> pya.QImage:
        size_inch = self.settings.page_size().size(pya.QPageSize_Unit.Inch)
        image = pya.QImage(size_inch.width * dpi, size_inch.height * dpi, pya.QImage.Format_ARGB32)
        image.fill(pya.Qt.white)

        painter = pya.QPainter(image)
        self.prepare_painter(painter)
        painter.setRenderHint(pya.QPainter.Antialiasing)
        try:
            pen = pya.QPen(pya.QColor('black'))
            pen.setWidthF(self.dbu)
            painter.setPen(pen)
        
            self.paint_layers(painter=painter, preview_mode=True)
        except ExportCancelledError as e:
            raise
        finally:
            painter.end()
        return image
    
    def export(self):
        painter = self.create_painter()
        self.prepare_painter(painter)
        try:
            pen = pya.QPen(pya.QColor('black'))
            pen.setWidthF(self.dbu)
            painter.setPen(pen)
        
            self.paint_layers(painter=painter, preview_mode=False)
        except ExportCancelledError as e:
            raise
        finally:
            painter.end()    
