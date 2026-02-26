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

import traceback

import pya

from klayout_plugin_utils.debugging import debug, Debugging

from vector_file_export_settings import VectorFileExportSettings


CONFIG_KEY__VECTOR_FILE_EXPORT_SETTINGS = 'klayout_vector_file_export_settings'


class PreviousUISettings:
    @staticmethod
    def load() -> VectorFileExportSettings:
        mw = pya.MainWindow.instance()

        settings: VectorFileExportSettings
        try:
            settings_str = mw.get_config(CONFIG_KEY__VECTOR_FILE_EXPORT_SETTINGS)
            settings = VectorFileExportSettings()        
            if settings_str is not None:
                d = pya.AbstractMenu.unpack_key_binding(settings_str)
                settings = VectorFileExportSettings.from_dict(d)
        except Exception as e:
            print(f"ERROR: Failed to restore export settings, proceeding with defaults due to exception: {e}")
            traceback.print_exc()
            settings = VectorFileExportSettings()
        return settings
    
    @staticmethod
    def save(settings: VectorFileExportSettings):
        mw = pya.MainWindow.instance()
        
        settings_str = pya.AbstractMenu.pack_key_binding(settings.dict())
        mw.set_config(CONFIG_KEY__VECTOR_FILE_EXPORT_SETTINGS, settings_str)
    
    
