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

from design_info import DesignInfo
from progress_reporter import ProgressReporter
from vector_file_export_settings import *


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
        
        self.design_info = DesignInfo.for_layout_view(layout_view, settings)
        
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
        dbu = self.design_info.dbu
    
        pen = pya.QPen(pya.QColor('black'))
        pen.setWidthF(dbu)
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
        # print(f"Target bounding box: {design_info.fig_width_pt:.2f} x {design_info.fig_height_pt:.2f} pt  (scale_um_to_pt {design_info.scale_um_to_pt:.6f})")
        # page_size_mm = page_size.size(pya.QPageSize_Unit.Millimeter)
        # print(f"Page size: {page_size_mm.width} x {page_size_mm.height} mm "
        #       f"({page_size_pt.width} x {page_size_pt.height} pt)")
        
        # center on page
        painter.translate(offset_x, offset_y + self.design_info.fig_height_pt)
        
        # flip Y (PDF Y is down, layout Y is up)
        painter.scale(self.design_info.scale_um_to_pt, -self.design_info.scale_um_to_pt)
        
        # optional: move origin again if needed
        # painter.translate(0, -bbox.height())
        painter.translate(-self.design_info.bbox.left, -self.design_info.bbox.bottom)

    def draw_shape(self,
                   painter: pya.QPainter,
                   shape: pya.Shape,
                   trans: pya.DTrans) -> bool:
        dbu = self.design_info.dbu
        font_metrics = pya.QFontMetrics(painter.font)
        def draw_text(shape: pya.Shape):
            text = shape.text
            full_trans = trans * shape.text_trans
            # full_trans = shape.text_trans
            disp = full_trans.disp
            world_pos_um = pya.QPointF(disp.x * dbu, - disp.y * dbu)
            
            t = painter.worldTransform
            
            # Remove Y flip
            t_no_flip = pya.QTransform(t)
            t_no_flip.scale(1.0, -1.0)
            # t_no_flip = pya.QTransform(
            #    t.m11(),  t.m12(),  0,
            #    t.m21(), -t.m22(),  0,
            #    t.dx(),   t.dy()
            #)
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
            painter.translate(pya.QPointF(x, y))
            # painter.rotate(-full_trans.rot() * 90)
            painter.drawText(0, 0, text.string)
            # painter.drawText(pya.QPointF(x, y), text.string)
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
                #return False
                pass
        
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
        top_cell = self.design_info.cell
        dbu = self.design_info.dbu
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
        page_size_pt = self.settings.page_size().sizePoints()
        px_per_pt = dpi / 72.0
        
        image = pya.QImage(int(page_size_pt.width * px_per_pt), 
                           int(page_size_pt.height * px_per_pt),
                           pya.QImage.Format_ARGB32)
        image.fill(pya.Qt.blue)
        
        painter = pya.QPainter(image)
        painter.setRenderHint(pya.QPainter.Antialiasing)
        
        # Pen width in layout units (µm)
        pen = pya.QPen(pya.QColor('black'))
        pen.setWidthF(max(self.design_info.dbu, self.design_info.um_per_pixel))
        painter.setPen(pen)
        
        # Layout → page scaling (points) and centering
        self.prepare_painter(painter)
        
        # Pixel scaling (points → pixels)
        painter.scale(px_per_pt, px_per_pt)
        
        painter.save()
        painter.resetTransform()
        painter.setPen(pya.QPen(pya.QColor('red')))
        painter.drawRect(0, 0, image.width(), image.height())
        painter.restore()
        
        try:
            self.paint_layers(painter=painter, preview_mode=True)
        except ExportCancelledError as e:
            if Debugging.DEBUG:
                debug(f"VectorFileExporter.render_preview caught exception {e}")
            raise
        finally:
            painter.end()
        return image
    
    def export(self):
        painter = self.create_painter()
        self.prepare_painter(painter)
        try:
            pen = pya.QPen(pya.QColor('black'))
            pen.setWidthF(self.design_info.dbu)
            painter.setPen(pen)
        
            self.paint_layers(painter=painter, preview_mode=False)
        except ExportCancelledError as e:
            raise
        finally:
            painter.end()    
