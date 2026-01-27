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
import os 
from pathlib import Path
import re
import sys
import traceback
from typing import *

import pya

from klayout_plugin_utils.debugging import debug, Debugging
from klayout_plugin_utils.file_system_helpers import FileSystemHelpers
from klayout_plugin_utils.qt_helpers import qmessagebox_critical
from klayout_plugin_utils.str_enum_compat import StrEnum

from vector_file_export_dialog import VectorFileExportDialog
from vector_file_export_settings import *

#--------------------------------------------------------------------------------

path_containing_this_script = os.path.realpath(os.path.join(os.path.dirname(__file__)))
    

#--------------------------------------------------------------------------------

class VectorFileExportPluginFactory(pya.PluginFactory):
    def __init__(self):
        super().__init__()
        
        if Debugging.DEBUG:
            debug("VectorFileExportPluginFactory.ctor")
        
        self.has_tool_entry = False
        self.register(-1000, "klayout_vector_file_export", "Vector File Export")
        
        try:
            self.setup()
        except Exception as e:
            print("VectorFileExportPluginFactory.ctor caught an exception", e)
            traceback.print_exc()
  
    def configure(self, name: str, value: str) -> bool:
        if Debugging.DEBUG:
            debug(f"VectorFileExportPluginFactory.configure, name={name}, value={value}")

        if name == CONFIG_KEY__VECTOR_FILE_EXPORT_SETTINGS:
            self.setup()
        
        return False
    
    def open_vector_file_export_dialog(self, action: pya.Action):
        if Debugging.DEBUG:
            debug("VectorFileExportPluginFactory.open_vector_file_export_dialog")
        
        cw = pya.CellView.active()
        if cw is None or cw.cell is None:
            qmessagebox_critical('Error', 'Export failed', 'No layout open to export')
            return

        settings: VectorFileExportSettings
        try:
            settings = VectorFileExportSettings.load()
        except Exception as e:
            print(f"ERROR: Failed to restore export settings, proceeding with defaults due to exception: {e}")
            settings = VectorFileExportSettings()
        
        settings.output_path = Path(f"{cw.cell.name}_export.pdf")

        mw = pya.MainWindow.instance()
        self.dialog = VectorFileExportDialog(settings=settings, parent=mw)

        result = self.dialog.exec_()
        if result == 1:
            FileSystemHelpers.reveal_in_file_manager(settings.output_path)

    def reset_menu(self):
        if Debugging.DEBUG:
            debug("VectorFileExportPluginFactory.reset_menu")
            
        mw = pya.MainWindow.instance()
        menu = mw.menu()
        
        # Locate the place before the 'Print' command
        file_menu_items = menu.items('file_menu')
        idx = file_menu_items.index('file_menu.print')

        action = pya.Action()
        action.title = "Export Vector File…"
        action.on_triggered += lambda a=action: self.open_vector_file_export_dialog(a)
        menu.insert_item(f"file_menu.#{idx}", f"export_vector_file", action)

    def setup(self):
        if Debugging.DEBUG:
            debug(f"VectorFileExportPluginFactory.setup")
        self.reset_menu()
    
    def stop(self):
        self.reset_menu()

