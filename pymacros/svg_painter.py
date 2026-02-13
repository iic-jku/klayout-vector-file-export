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
#-----------------

from pathlib import Path
import re
from typing import *
import unittest
import xml.etree.ElementTree as ET

import pya

from klayout_plugin_utils.debugging import debug, Debugging

from exception import ExportCancelledError
from progress_reporter import ProgressReporter


_transform_re = re.compile(r"(\w+)\(([^)]*)\)")


def parse_svg_transform(transform: str) -> pya.QTransform:
    """
    Parse a subset of SVG transform strings into a QTransform.
    Supports: translate, scale
    """
    t = pya.QTransform()

    for name, args in _transform_re.findall(transform):
        values = [float(v) for v in re.split(r"[ ,]+", args.strip()) if v]

        if name == "translate":
            if len(values) == 1:
                t.translate(values[0], 0.0)
            elif len(values) >= 2:
                t.translate(values[0], values[1])

        elif name == "scale":
            if len(values) == 1:
                t.scale(values[0], values[0])
            elif len(values) >= 2:
                t.scale(values[0], values[1])

        else:
            raise ValueError(f"Unsupported SVG transform: {name}")

    return t


def convert_svg_to_qpainter_paths(svg_path: Path,
                                  progress_reporter: Optional[ProgressReporter]) -> List[pya.QPainterPath]:
    if Debugging.DEBUG:
        debug(f"convert_svg_to_qpainter_paths: begin parsing SVG file {svg_path}")
    
    tree = ET.parse(str(svg_path))
    root = tree.getroot()
    
    if Debugging.DEBUG:
        debug(f"convert_svg_to_qpainter_paths: end parsing SVG file {svg_path}")
    
    if Debugging.DEBUG:
        debug(f"convert_svg_to_qpainter_paths: begin QPainterPath object creation")
    
    paths: List[pya.QPainterPath] = []
    
    token_re = re.compile(r"[MmLlCcZz]|-?\d+(?:\.\d+)?")
    
    def walk(node, transform: pya.QTransform):
        # Update transform if this node has one
        local_transform = transform
        transform_attr = node.attrib.get("transform")
        if transform_attr:
            local = parse_svg_transform(transform_attr)
            local_transform = transform * local
    
        # Process <path> elements
        if node.tag.endswith("path"):
            d = node.attrib.get("d", "")
            tokens = token_re.findall(d)
    
            path = pya.QPainterPath()
            cur = pya.QPointF(0.0, 0.0)
            start = pya.QPointF(0.0, 0.0)
    
            i = 0
            cmd = None
    
            while i < len(tokens):
                if progress_reporter is not None\
                   and progress_reporter.was_canceled():
                   raise ExportCancelledError()
            
                t = tokens[i]
    
                if re.match(r"[MmLlCcZz]", t):
                    cmd = t
                    i += 1
    
                if cmd in ("M", "m"):
                    x = float(tokens[i]); y = float(tokens[i+1])
                    i += 2
                    if cmd == "m":
                        cur += pya.QPointF(x, y)
                    else:
                        cur = pya.QPointF(x, y)
                    path.moveTo(cur)
                    start = pya.QPointF(cur.x, cur.y)
                    cmd = "L" if cmd == "M" else "l"
    
                elif cmd in ("L", "l"):
                    x = float(tokens[i]); y = float(tokens[i+1])
                    i += 2
                    if cmd == "l":
                        cur += pya.QPointF(x, y)
                    else:
                        cur = pya.QPointF(x, y)
                    path.lineTo(cur)
    
                elif cmd in ("C", "c"):
                    x1 = float(tokens[i]);   y1 = float(tokens[i+1])
                    x2 = float(tokens[i+2]); y2 = float(tokens[i+3])
                    x3 = float(tokens[i+4]); y3 = float(tokens[i+5])
                    i += 6
    
                    if cmd == "c":
                        p1 = cur + pya.QPointF(x1, y1)
                        p2 = cur + pya.QPointF(x2, y2)
                        cur += pya.QPointF(x3, y3)
                    else:
                        p1 = pya.QPointF(x1, y1)
                        p2 = pya.QPointF(x2, y2)
                        cur = pya.QPointF(x3, y3)
    
                    path.cubicTo(p1, p2, cur)
    
                elif cmd in ("Z", "z"):
                    path.closeSubpath()
                    cur = pya.QPointF(start.x, start.y)
    
            # 🔑 apply composed SVG transform here
            path = local_transform.map(path)
            paths.append(path)
    
        for child in node:
            walk(child, local_transform)
    
    walk(root, pya.QTransform())
    
    if Debugging.DEBUG:
        debug(f"convert_svg_to_qpainter_paths: end QPainterPath object creation")
    
    return paths

#--------------------------------------------------------------------------------

class BitmapVectorizerPdfRenderTests(unittest.TestCase):
    def test_render_svg_paths_to_pdf(self):
    
        svg_xml = """<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN"
 "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg version="1.0" xmlns="http://www.w3.org/2000/svg"
 width="16.000000pt" height="16.000000pt" viewBox="0 0 16.000000 16.000000"
 preserveAspectRatio="xMidYMid meet">
<metadata>
Created by potrace 1.16, written by Peter Selinger 2001-2019
</metadata>
<g transform="translate(0.000000,16.000000) scale(0.100000,-0.100000)"
fill="#000000" stroke="none">
<path d="M75 78 l-80 -83 83 80 c45 44 82 81 82 82 0 8 -11 -3 -85 -79z"/>
</g>
</svg>
        """    
    
        svg_path = Path("/tmp/svg2pdf_in.svg")
        svg_path.write_text(svg_xml)
        
        pdf_path = Path("/tmp/svg2pdf_out.pdf")
        
        try:
            # Convert SVG paths
            paths = convert_svg_to_qpainter_paths(svg_path)
            self.assertGreater(len(paths), 0, "No paths extracted from SVG")
            
            # Create PDF writer
            pdf = pya.QPdfWriter(str(pdf_path))
            pdf.setResolution(72)
            pdf.setTitle("BitmapVectorizer test")
            
            dev = pdf.asQPagedPaintDevice()
            dev.setPageSize(pya.QPageSize(pya.QPageSize.A4))
            
            painter = pya.QPainter(dev)
            try:
                painter.setRenderHint(pya.QPainter.Antialiasing)
                painter.setBrush(pya.QBrush(pya.QColor("black")))

                pen = pya.QPen(pya.QColor("black"))
                pen.setWidthF(0.5)
                pen.setCosmetic(True)
                painter.setPen(pen)
            
                # Coordinate system:
                # SVG uses +Y down; your parser flipped Y already.
                # We just need a convenient scale.                
                # painter.scale(1.0, 1.0)
                
                # Normalize placement
                bounds = pya.QPainterPath()
                for p in paths:
                    bounds.addPath(p)

                bbox = bounds.boundingRect()
                painter.translate(-bbox.left, -bbox.top)
            
                
                for path in paths:
                    painter.drawPath(path)
            
            finally:
                painter.end()
        finally:
            print(f"path exported to {pdf_path}")
            # os.remove(pdf_path)



if __name__ == "__main__": 
    unittest.main()
