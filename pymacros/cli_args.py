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

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import *
import sys

import rich.console
import rich.markdown
import rich.text
from rich_argparse import RichHelpFormatter


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

#--------------------------------------------------------------------------------

PROGRAM_NAME = 'klayout-vector-export'
__version__ = '0.1'   # TODO: parse from grain.xml


#
# NOTE: as this file is used from klayout-vector-file-export-cli,
#       no dependency on pya is allowed!
#
from vector_file_export_settings import *

def build_parser() -> argparse.ArgumentParser:
    main_parser = argparse.ArgumentParser(
        prog='klayout-vector-export',
        description='Export KLayout layouts to vector file formats (PDF/SVG) via CLI.',
        add_help=False,
        formatter_class=RichHelpFormatter,
    )
    
    group_special = main_parser.add_argument_group("Special options")
    group_special.add_argument("--help", "-h", action='help', help="show this help message and exit")
    group_special.add_argument("--version", "-v", action='version', version=f'{PROGRAM_NAME} {__version__}')
    
    # --- Output ---
    group_io = main_parser.add_argument_group("I/O options")
    
    group_io.add_argument(
        '-i',
        '--in',
        dest='input_path',
        type=Path,
        help='Input layout file path (e.g. ~/inverter.gds)',
    )
    
    group_io.add_argument(
        '-o',
        '--out',
        dest='output_path',
        type=Path,
        help='Output file path (e.g. /tmp/export.pdf)',
    )
    
    group_io.add_argument(
        '-t', '--tech', 
        dest='technology',
        type=str,
        help="Techology name (as defined in KLayout, e.g. sg13g2, sky130, gf180mcu)",
    )
    
    group_io.add_argument(
        '--format', dest='file_format',
        type=VectorFileFormat,
        choices=list(VectorFileFormat),
        help='Output file format',
    )
    
    group_io.add_argument(
        '--title',
        type=str,
        help='Document title embedded in the output file',
    )

    # --- Page layout ---
    page_group = main_parser.add_argument_group('page layout')
    page_group.add_argument(
        '--page-format',
        type=str,
        metavar='PAGE_SIZE_ID',
        help='Page format (e.g. A4, B5, Letter)',
    )
    page_group.add_argument(
        '--orientation',
        dest='page_orientation',
        type=PageOrientation,
        choices=list(PageOrientation),
    )
    page_group.add_argument(
        '--scaling-style',
        dest='content_scaling_style',
        type=ContentScaling,
        choices=list(ContentScaling),
        help='How content scaling is specified',
    )
    page_group.add_argument(
        '--scaling-value',
        dest='content_scaling_value',
        type=float,
        metavar='VALUE',
        help='Figure width in mm (if --scaling-style=figure_width_mm) or scaling factor',
    )

    # --- Color ---
    color_group = main_parser.add_argument_group('color')
    color_group.add_argument(
        '--color-mode',
        type=ColorMode,
        choices=list(ColorMode)
    )
    color_group.add_argument(
        '--background', dest='include_background_color',
        action=argparse.BooleanOptionalAction,
        help='Include background color in output',
    )
    color_group.add_argument(
        '--stipples', dest='include_stipples',
        action=argparse.BooleanOptionalAction,
        help='Include layer stipple patterns',
    )

    # --- Text / fonts ---
    text_group = main_parser.add_argument_group('text and fonts')
    text_group.add_argument(
        '--font-family',
        type=str,
    )
    text_group.add_argument(
        '--font-size-mode',
        type=FontSizeMode,
        choices=list(FontSizeMode),
    )
    text_group.add_argument(
        '--font-size-pt',
        type=float,
        metavar='PT',
        help='Font size in points (used when --font-size-mode=absolute)',
    )
    text_group.add_argument(
        '--font-size-pct',
        dest='font_size_percent_of_fig_width',
        type=float,
        metavar='PCT',
        help='Font size as %% of figure width (used when --font-size-mode=percent_of_fig_width)',
    )
    
    allowed_text_mode_choices = [m for m in list(TextMode) if m.value != 'all_visible']
    
    text_group.add_argument(
        '--text-mode',
        type=TextMode,
        choices=allowed_text_mode_choices,
    )
    text_group.add_argument(
        '--text-layers-filter',
        dest='text_layers_filter_enabled',
        action=argparse.BooleanOptionalAction,
        help='Restrict text rendering to specific layers',
    )
    text_group.add_argument(
        '--text-layers',
        type=str,
        metavar='LAYER_SPEC',
        help='Comma-separated layer specs for text filter (e.g. "1/0,2/0")',
    )

    # --- Geometry ---
    geo_group = main_parser.add_argument_group('geometry')
    geo_group.add_argument(
        '--geometry-reduction',
        type=GeometryReduction,
        choices=list(GeometryReduction),
    )

    # --- Layer selection ---
    layer_group = main_parser.add_argument_group('layer selection (Shapes and Instances)')
    layer_group.add_argument(
        '--layer-output-style',
        type=LayerOutputStyle,
        choices=list(LayerOutputStyle),
    )
    
    allowed_layers_selection_choices = [m for m in list(LayerSelectionMode) if m.value != 'all_visible_layers']
        
    layer_group.add_argument(
        '--layer-selection',
        dest='layer_selection_mode',
        type=LayerSelectionMode,
        choices=allowed_layers_selection_choices,
    )
    
    layer_group.add_argument(
        '--custom-layers',
        dest='custom_layers',
        type=str,
        metavar='LAYER_SPEC',
        help='Layer spec list',
    )

    # --- Settings file (load/save) ---
    settings_group = main_parser.add_argument_group('settings file')
    settings_group.add_argument(
        '--load-settings',
        type=Path,
        metavar='JSON_PATH',
        help='Load settings from a JSON file (individual flags override loaded values)',
    )
    settings_group.add_argument(
        '--save-settings',
        type=Path,
        metavar='JSON_PATH',
        help='Save the resolved settings to a JSON file before running',
    )

    return main_parser


def args_to_settings(args: argparse.Namespace) -> VectorFileExportSettings:
    """
    Convert parsed args to a VectorFileExportSettings instance.
    If --load-settings was given, that file provides the base; any explicitly
    supplied CLI flags override individual fields.
    """
    if args.load_settings is not None:
        settings = VectorFileExportSettings.load_json(args.load_settings)
    else:
        settings = VectorFileExportSettings()

    # Map every argparse dest directly onto the dataclass field of the same name.
    # Fields that share a name need no special treatment.
    field_names = {f.name for f in VectorFileExportSettings.__dataclass_fields__.values()}
    for dest, value in vars(args).items():
        if dest in field_names and value is not None:
            setattr(settings, dest, value)
        
    if settings.layer_selection_mode == LayerSelectionMode.ALL_VISIBLE:
        raise ValueError(f"WARNING: Runset file provided contains layer selection of 'All Visible'.\n\n"
                         f"\tThis setting only works in interactive GUI mode.\n"
                         f"\tPlease override this setting using the arguments --layer-selection='custom_layer_list' --custom_layers")

    if settings.text_mode == TextMode.ALL_VISIBLE:
        raise ValueError(f"WARNING: Runset file provided contains text mode of 'All Visible'.\n\n"
                         f"\tThis setting only works in interactive GUI mode.\n"
                         f"\tPlease override this setting using the arguments --text-mode='all' --text-layers")
    
    return settings


def validate_settings(settings: VectorFileExportSettings) -> None:
    """Raise ValueError for cross-field constraints that argparse alone can't catch."""
    if settings.layer_selection_mode == LayerSelectionMode.CUSTOM_LIST:
        if not settings.custom_layers.strip():
            raise ValueError(
                "--layers must not be empty when "
                "--layer-selection-mode=custom_layer_list"
            )
    if settings.text_layers_filter_enabled and not settings.text_layers.strip():
        raise ValueError(
            "--text-layers must not be empty when --text-layers-filter is set"
        )
    if settings.content_scaling_value <= 0:
        raise ValueError("--scaling-value must be > 0")
    if settings.font_size_pt <= 0:
        raise ValueError("--font-size-pt must be > 0")
    if not (0 < settings.font_size_percent_of_fig_width <= 100):
        raise ValueError("--font-size-pct must be in (0, 100]")


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args(sys.argv)

    settings = args_to_settings(args)
    validate_settings(settings)
