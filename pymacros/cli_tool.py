#! /usr/bin/env python3

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

import os
from pathlib import Path
import sys

import pya

# this file is intended to be run using
# klayout -z -nc -rx -r cli_tool.py -rd input_path=foo.gds -rd settings_path=/tmp/settings.json

#--------------------------------------------------------------------------------

directory_containing_this_script = os.path.realpath(os.path.dirname(__file__))
for name in (
    'KLayoutPluginUtils',   # deployed via Salt
    'klayout-plugin-utils'  # source code
):
    path = os.path.realpath(os.path.join(directory_containing_this_script,
                                         '..', '..', name, 'python'))
    if os.path.exists(path):
        sys.path.append(path)
sys.path.append(directory_containing_this_script)


from vector_file_export_settings import VectorFileExportSettings
from vector_file_exporter import VectorFileExporter

#--------------------------------------------------------------------------------

def main():
    global input_path
    global settings_path
    global technology

    print(f"Input Path: {input_path}")
    print(f"Settings Path: {settings_path}")
    print(f"Technology: {technology}")
    
    input_layout_path = Path(input_path)
    settings_json_path = Path(settings_path)
        
    errors = []
    if not input_layout_path.exists():
        errors += [f"Input layout path does not exist: {input_layout_path}"]

    if not settings_json_path.exists():
        errors += [f"Settings JSON path does not exist: {settings_json_path}"]
    
    if not pya.Technology.has_technology(technology):
        available =[f"'{n}'" for n in pya.Technology.technology_names()]
        errors += [
            f"Technology '{technology}' is not registered in KLayout.\n"
            f"\tAvailable technologies: {', '.join(available) or '(none)'}"
        ]
    
    if errors:
        raise Exception('\n'.join(errors))

    settings = VectorFileExportSettings.load_json(settings_json_path)

    lv = pya.LayoutView()
    lv.load_layout(str(input_layout_path), technology)

    tech = pya.Technology.technology_by_name(technology)

    lyp_path = tech.eff_path("layer_properties.lyp")
    if lyp_path and Path(lyp_path).exists():
        lv.load_layer_props(lyp_path)
    else:
        lv.add_missing_layers()   # fallback: auto-create entries without colors

    lv.max_hier()
    
    exporter = VectorFileExporter(    
        layout_view=lv,
        settings=settings,
        progress_reporter=None
    )
    exporter.export()

    
if __name__ == "__main__":
    main()
