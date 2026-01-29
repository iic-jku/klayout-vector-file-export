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

import os
from pathlib import Path
import traceback

from klayout_plugin_utils.debugging import debug, Debugging
from klayout_plugin_utils.file_system_helpers import FileSystemHelpers
from klayout_plugin_utils.qt_helpers import qmessagebox_critical

from design_info import DesignInfo
from progress_reporter import ProgressReporter
from vector_file_export_settings import *
from vector_file_exporter import VectorFileExporter, ExportCancelledError

path_containing_this_script = os.path.realpath(os.path.dirname(__file__))


class VectorFileExportDialog(pya.QDialog, ProgressReporter):
    def __init__(self, settings: VectorFileExportSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Vector File Export')
        
        loader = pya.QUiLoader()
        ui_path = os.path.join(path_containing_this_script, "VectorFileExportDialog.ui")
        ui_file = pya.QFile(ui_path)
        try:
            ui_file.open(pya.QFile.ReadOnly)
            self.page = loader.load(ui_file, self)
        finally:
            ui_file.close()

        self.bottom = pya.QHBoxLayout()
        
        self.exportButton = pya.QPushButton('Export')
        self.cancelButton = pya.QPushButton('Cancel')
                
        self.bottom.addStretch(1)
        
        self.bottom.addWidget(self.exportButton)
        self.bottom.addWidget(self.cancelButton)
        
        layout = pya.QVBoxLayout(self)
        layout.addWidget(self.page)
        layout.addLayout(self.bottom)
        
        self.exportButton.clicked.connect(self.on_export)
        self.cancelButton.clicked.connect(self.on_cancel)
        
        self.exportButton.setDefault(True)
        self.exportButton.setAutoDefault(True)
        self.cancelButton.setAutoDefault(False)
        
        self.page.page_format_cob.clear()
        for page_id in range(pya.QPageSize.A4.to_i(), pya.QPageSize.LastPageSize.to_i() + 1):
            if page_id == pya.QPageSize.Custom.to_i():
                continue
            
            format_title = self.format_page_size(page_id)
            self.page.page_format_cob.addItem(format_title, page_id)
        
        self.page.file_format_cob.currentIndexChanged.connect(self.on_file_format_changed)

        self.page.portrait_rb.toggled.connect(self.on_orientation_radio_buttons_changed)
        self.page.landscape_rb.toggled.connect(self.on_orientation_radio_buttons_changed)
        self.page.figure_size_rb.toggled.connect(self.on_scaling_radio_buttons_changed)
        self.page.scaling_rb.toggled.connect(self.on_scaling_radio_buttons_changed)
        self.page.all_visible_layers_rb.toggled.connect(self.on_layer_radio_buttons_changed)
        self.page.custom_layer_selection_rb.toggled.connect(self.on_layer_radio_buttons_changed)

        self.page.browse_save_path_pb.clicked.connect(self.on_browse_save_path)

        self.page.figure_width_le.textEdited.connect(self.on_figure_width_changed)
        self.page.figure_height_le.textEdited.connect(self.on_figure_height_changed)
        self.page.scaling_le.textEdited.connect(self.on_scaling_value_changed)
        self.page.custom_layers_le.textEdited.connect(self.on_custom_layers_changed)

        # self.scene = pya.QGraphicsScene(self)
        # self.page.preview_gv.setScene(self.scene)        
        
        self.update_ui_from_settings(settings)

    @staticmethod
    def format_page_size(page_size_id: int) -> str:
        page_size = pya.QPageSize(pya.QPageSize.PageSizeId(page_size_id))
        size_mm = page_size.size(pya.QPageSize.Millimeter)
        title = f"{page_size.name()} ({size_mm.width:.0f} x {size_mm.height:.0f} mm)"
        return title

    def on_reset(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_reset")
        
        try:
            settings = VectorFileExportSettings()
            self.update_ui_from_settings(settings)    
        except Exception as e:
            print("VectorFileExportDialog.on_reset caught an exception", e)
            traceback.print_exc()

    def begin_progress(self, maximum: int):
        self.progress_dialog = pya.QProgressDialog(
            "Exporting shapes…",
            "Cancel",
            0,
            maximum,
            self
        )
        self.progress_dialog.setWindowTitle("Export")
        self.progress_dialog.setWindowModality(pya.Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)

    def progress(self, data: Dict[str, Any]):
        total_layers = data['total_layers']
        exported_layers = data['exported_layers']
        self.progress_dialog.setValue(exported_layers)
        self.progress_dialog.setLabelText(f"Exported {exported_layers} / {total_layers} layers")
        pya.QApplication.processEvents()
        
    def was_canceled(self) -> bool:
        return self.progress_dialog.wasCanceled
        
    def on_export(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_export")

        self.exportButton.setEnabled(False)
        
        try:
            settings = self.settings_from_ui()
            settings.save()
        
            exporter = VectorFileExporter(layout_view=pya.LayoutView.current(),
                                          settings=settings,
                                          progress_reporter=self)
            exporter.export()
            self.accept()
        except ExportCancelledError as e:
            pass
        except Exception as e:
            print("VectorFileExportDialog.on_ok caught an exception", e)
            traceback.print_exc()
            qmessagebox_critical('Error',
                                 f"Failed to export layout in vector format",
                                 f"Caught exception: <pre>{e}</pre>")
        finally:
            self.progress_dialog.close()
            self.exportButton.setEnabled(False)        

    def on_cancel(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_cancel")
        self.reject()
    
    def settings_from_ui(self) -> VectorFileExportSettings:
        file_format: VectorFileFormat
        layer_output_style: LayerOutputStyle
        
        chosen_format = self.page.file_format_cob.currentText
        if chosen_format == 'SVG':
            file_format = VectorFileFormat.SVG
            layer_output_style = LayerOutputStyle.SINGLE_PAGE
        elif chosen_format == 'PDF (single page)':
            file_format = VectorFileFormat.PDF
            layer_output_style = LayerOutputStyle.SINGLE_PAGE
        elif chosen_format == 'PDF (page per layer)':
            file_format = VectorFileFormat.PDF
            layer_output_style = LayerOutputStyle.PAGE_PER_LAYER
        
        output_path = Path(self.page.save_path_le.text)
        
        page_format = self.page.page_format_cob.currentData()

        page_orientation: PageOrientation
        if self.page.portrait_rb.checked:
            page_orientation = PageOrientation.PORTRAIT
        else:
            page_orientation = PageOrientation.LANDSCAPE
        
        content_scaling_style: ContentScaling
        content_scaling_value: float
        if self.page.figure_size_rb.checked:
            content_scaling_style = ContentScaling.FIGURE_WIDTH_MM
            content_scaling_value = float(self.page.figure_width_le.text)
        else:
            content_scaling_style = ContentScaling.SCALING
            content_scaling_value = float(self.page.scaling_le.text)

        custom_layers: str
        if self.page.all_visible_layers_rb.checked:        
            custom_layers = ''
        elif self.page.custom_layer_selection_rb.checked:
            custom_layers = self.page.custom_layers_le.text
        
        return VectorFileExportSettings(
            file_format=file_format,
            output_path=output_path,
            title=self.page.title_le.text,
            page_format=page_format,
            page_orientation=page_orientation,
            content_scaling_style=content_scaling_style,
            content_scaling_value=content_scaling_value,
            layer_output_style=layer_output_style,
            custom_layers=custom_layers
        )
    
    def update_ui_from_settings(self, settings: VectorFileExportSettings):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.update_ui_from_settings")
        
        format_choice = ''
        match (settings.file_format, settings.layer_output_style):
            case (VectorFileFormat.PDF, LayerOutputStyle.SINGLE_PAGE):
                format_choice='PDF (single page)'
            case (VectorFileFormat.PDF, LayerOutputStyle.PAGE_PER_LAYER):
                format_choice='PDF (page per layer)'
            case (VectorFileFormat.SVG, _):
                format_choice='SVG'
            case _:
                raise NotImplementedError(f"Unhandled enum case {(settings.file_format, settings.layer_output_style)}")
        idx = self.page.file_format_cob.findText(format_choice)
        if idx >= 0:
            self.page.file_format_cob.setCurrentIndex(idx)

        self.page.save_path_le.setText(settings.output_path)
        
        self.page.title_le.setText(settings.title)
        
        page_format = self.format_page_size(settings.page_format)
        idx = self.page.page_format_cob.findText(page_format)
        if idx >= 0:
            self.page.page_format_cob.setCurrentIndex(idx)
        
        match settings.page_orientation:
            case PageOrientation.PORTRAIT:
                self.page.portrait_rb.setChecked(True)
                self.page.landscape_rb.setChecked(False)
            case PageOrientation.LANDSCAPE:
                self.page.portrait_rb.setChecked(False)
                self.page.landscape_rb.setChecked(True)
        
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)
        
        match settings.content_scaling_style:
            case ContentScaling.FIGURE_WIDTH_MM:
                self.page.figure_size_rb.setChecked(True)
                self.page.scaling_rb.setChecked(False)
            case ContentScaling.SCALING:
                self.page.figure_size_rb.setChecked(False)
                self.page.scaling_rb.setChecked(True)
            case _:
                raise NotImplementedError(f"Unhandled enum case {settings.content_scaling_style}")
            
        
        self.page.figure_width_le.setText(f"{design_info.fig_width_mm:.6f}")
        self.page.figure_height_le.setText(f"{design_info.fig_height_mm:.6f}")
        self.page.scaling_le.setText(f"{design_info.scaling:.4f}")

        if settings.custom_layers.strip() == '':
            self.page.all_visible_layers_rb.setChecked(True)
            self.page.custom_layer_selection_rb.setChecked(False)
        else:
            self.page.all_visible_layers_rb.setChecked(False)
            self.page.custom_layer_selection_rb.setChecked(True)
            
        self.page.custom_layers_le.setText(settings.custom_layers)
        
        self.on_orientation_radio_buttons_changed()
        self.on_scaling_radio_buttons_changed()
        self.on_layer_radio_buttons_changed()
        
        self.page.bounding_box_lb.setText(f"{design_info.width_um:.3f} µm x {design_info.height_um:.3f} µm")
        
        # exporter = VectorFileExporter(layout_view=pya.LayoutView.current(),
        #                               settings=settings,
        #                               progress_reporter=None)
        # 
        # try:
        #     img = exporter.render_preview(dpi=300)
        #     pm = pya.QPixmap.fromImage(img)
        #     self.scene.clear()
        #     self.scene.addPixmap(pm)
        #     self.scene.setSceneRect(pya.QRectF(pm.rect()))
        #     self.page.preview_gv.fitInView(self.scene.sceneRect, pya.Qt.KeepAspectRatio)
        # except ExportCancelledError as e:
        #     pass
        
        match settings.content_scaling_style:
            case ContentScaling.FIGURE_WIDTH_MM:
                self.on_figure_width_changed()
            case ContentScaling.SCALING:
                self.on_scaling_changed()
            case _:
                raise NotImplementedError(f"Unhandled enum case {settings.content_scaling_style}")

    def on_file_format_changed(self):
        old_path = self.page.save_path_le.text.strip()
        if old_path != '':
            path = Path(old_path)
            settings = self.settings_from_ui()
            new_suffix = settings.file_format.value
            if path.suffix != new_suffix:
                path = path.with_suffix(new_suffix)
            self.page.save_path_le.setText(str(path))
        
    def on_orientation_radio_buttons_changed(self):
        pass

    def on_scaling_radio_buttons_changed(self):
        pass

    def on_layer_radio_buttons_changed(self):
        pass
    
    def on_figure_width_changed(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_figure_width_changed")
    
        self.page.figure_size_rb.setChecked(True)
        
        settings = self.settings_from_ui()
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)

        self.page.figure_height_le.setText(f"{design_info.fig_height_mm:.6f}")        
        self.page.scaling_le.setText(f"{design_info.scaling:.6f}")
    
    def on_figure_height_changed(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_figure_height_changed")
    
        self.page.figure_size_rb.setChecked(True)

        settings = self.settings_from_ui()
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)
        
        width_mm = design_info.width_um / design_info.height_um * float(self.page.figure_height_le.text)
        self.page.figure_width_le.setText(f"{width_mm:.6f}")

        settings = self.settings_from_ui()
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)

        self.page.scaling_le.setText(f"{design_info.scaling:.6f}")
    
    def on_scaling_value_changed(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_scaling_value_changed")

        self.page.scaling_rb.setChecked(True)
            
        settings = self.settings_from_ui()
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)
        
        self.page.figure_width_le.setText(f"{design_info.fig_width_mm:.6f}")
        self.page.figure_height_le.setText(f"{design_info.fig_height_mm:.6f}")        
    
    def on_custom_layers_changed(self):
        self.page.custom_layer_selection_rb.setChecked(True)
    
    def on_browse_save_path(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_browse_save_path")
        
        try:
            lru_path = FileSystemHelpers.least_recent_directory()
            
            file_filter: str
            suffix: str
            
            settings = self.settings_from_ui()
            match settings.file_format:
                case VectorFileFormat.PDF:
                    file_filter = 'PDF (*.pdf)'
                    suffix = '.pdf'
                case VectorFileFormat.SVG:
                    file_filter = 'SVG (*.svg)'
                    suffix = '.svg'
                case _:
                    raise NotImplementedError(f"Unhandled enum case {settings.file_format}")

            file_path_str = pya.QFileDialog.getSaveFileName(
                self,               
                "Select Export File Path",
                lru_path,                 # starting dir ("" = default to last used / home)
                f"{file_filter};;All Files (*)"
            )
        
            if file_path_str:
                file_path = Path(file_path_str)
                if '.'.join(file_path.suffixes).lower() != suffix:
                    file_path = file_path.with_suffix(suffix)
                self.page.save_path_le.setText(file_path)
                
                FileSystemHelpers.set_least_recent_directory(file_path.parent)
        except Exception as e:
            print("VectorFileExportDialog.on_browse_save_path caught an exception", e)
            traceback.print_exc()

