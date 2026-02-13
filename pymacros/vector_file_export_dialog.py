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
import shutil
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
        
        self.progress_dialog = None
        
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
        self.page.colors_cob.currentIndexChanged.connect(self.on_color_changed)
        self.page.browse_save_path_pb.clicked.connect(self.on_browse_save_path)
        self.page.figure_width_sb.valueChanged.connect(self.on_figure_width_changed)
        self.page.figure_height_sb.valueChanged.connect(self.on_figure_height_changed)
        self.page.scaling_sb.valueChanged.connect(self.on_scaling_value_changed)
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
        
            exporter = VectorFileExporter(layout_view=pya.LayoutView.current(),
                                          settings=settings,
                                          progress_reporter=self)
            
            if settings.include_stipples:
                notfound = []
                if not shutil.which('potrace'):
                    notfound += ['potrace']
                if not shutil.which('mkbitmap'):
                    notfound += ['mkbitmap']
                if notfound:
                    raise Exception(f"Executable{'s' if len(notfound) >= 2 else ''} {' / '.join(notfound)}"
                                    f" not found in PATH (required for stipple export)")
            
            settings.save()
            
            exporter.export()
            self.accept()
        except ExportCancelledError as e:
            pass
        except Exception as e:
            if self.progress_dialog is not None:
                self.progress_dialog.cancel()
            
            qmessagebox_critical('Error',
                                 f"Failed to export layout in vector format",
                                 f"Caught exception: <pre>{e}</pre>")
        finally:
            if self.progress_dialog is not None:
                self.progress_dialog.close()
            self.exportButton.setEnabled(True)        

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
        title = self.page.title_le.text
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
            content_scaling_value = self.page.figure_width_sb.value
        else:
            content_scaling_style = ContentScaling.SCALING
            content_scaling_value = self.page.scaling_sb.value

        chosen_color_mode = self.page.colors_cob.currentText
        color_mode: ColorMode = ColorMode(chosen_color_mode)
                
        include_background_color = self.page.include_bg_color_cb.checked
        include_stipples = self.page.include_stipples_cb.checked
        
        font_family = self.page.font_family_cob.currentText
        
        font_size_mode: FontSizeMode
        if self.page.font_size_absolute_rb.checked:
            font_size_mode = FontSizeMode.ABSOLUTE
        elif self.page.font_size_relative_rb.checked:
            font_size_mode = FontSizeMode.PERCENT_OF_FIG_WIDTH
        else:
            font_size_mode = FontSizeMode.PERCENT_OF_FIG_WIDTH
        
        font_size_pt = self.page.font_size_pt_sb.value
        font_size_percent_of_fig_width = self.page.font_size_relative_sb.value
        
        text_mode: TextMode
        chosen_text_mode = self.page.texts_cob.currentText
        match chosen_text_mode:
            case 'None': 
                text_mode = TextMode.NONE
            case 'All Visible':
                text_mode = TextMode.ALL_VISIBLE
            case 'Only Of Top Cell':
                 text_mode = TextMode.ONLY_TOP_CELL
            case _:
                raise NotImplementedError(f"Unhandled text mode {chosen_text_mod}")
        
        text_layers_filter_enabled = self.page.text_layers_filter_enabled_cb.checked
        text_layers = self.page.text_layers_filter_le.text

        layer_selection_mode: LayerSelectionMode
        if self.page.all_visible_layers_rb.checked:
            layer_selection_mode = LayerSelectionMode.ALL_VISIBLE_LAYERS
        elif self.page.custom_layer_selection_rb.checked:
            layer_selection_mode = LayerSelectionMode.CUSTOM_LAYER_LIST

        custom_layers = self.page.custom_layers_le.text.strip()
        
        return VectorFileExportSettings(
            file_format=file_format,
            output_path=output_path,
            title=title,
            page_format=page_format,
            page_orientation=page_orientation,
            content_scaling_style=content_scaling_style,
            content_scaling_value=content_scaling_value,
            color_mode=color_mode,
            include_background_color=include_background_color,
            include_stipples=include_stipples,
            font_family=font_family,
            font_size_mode=font_size_mode,
            font_size_pt=font_size_pt,
            font_size_percent_of_fig_width=font_size_percent_of_fig_width,
            text_mode=text_mode,
            text_layers_filter_enabled=text_layers_filter_enabled,
            text_layers=text_layers,
            layer_output_style=layer_output_style,
            layer_selection_mode=layer_selection_mode,
            custom_layers=custom_layers
        )
        
    def update_ui_from_settings(self, settings: VectorFileExportSettings):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.update_ui_from_settings")
            
        def block_signals(blocked: bool):
            self.page.file_format_cob.blockSignals(blocked)
            self.page.browse_save_path_pb.blockSignals(blocked)
            self.page.colors_cob.blockSignals(blocked)
            self.page.figure_width_sb.blockSignals(blocked)
            self.page.figure_height_sb.blockSignals(blocked)
            self.page.scaling_sb.blockSignals(blocked)
            self.page.custom_layers_le.blockSignals(blocked)
            
        block_signals(True)
        self._update_ui_from_settings(settings)
        block_signals(False)
    
    # NOTE: this method is guarded (all signals should be blocked)
    def _update_ui_from_settings(self, settings: VectorFileExportSettings):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog._update_ui_from_settings")
        
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
        
        self.page.figure_width_sb.setValue(design_info.fig_width_mm)
        self.page.figure_height_sb.setValue(design_info.fig_height_mm)
        self.page.scaling_sb.setValue(design_info.scaling)
        
        self.page.colors_cob.setCurrentText(settings.color_mode.value)
        self.page.include_bg_color_cb.setChecked(settings.include_background_color)
        self.page.include_stipples_cb.setChecked(settings.include_stipples)
        
        self.page.font_family_cob.setCurrentText(settings.font_family)

        match settings.font_size_mode:
            case FontSizeMode.ABSOLUTE:
                self.page.font_size_absolute_rb.setChecked(True)
            case FontSizeMode.PERCENT_OF_FIG_WIDTH:
                self.page.font_size_relative_rb.setChecked(True)
            case _:
                raise NotImplementedError(f"Unhandled enum case {settings.font_size_mode}")
        
        self.page.font_size_pt_sb.setValue(settings.font_size_pt)
        
        self.page.font_size_relative_sb.setValue(settings.font_size_percent_of_fig_width)

        text_mode_index: int
        match settings.text_mode:
            case TextMode.NONE:
                text_mode_index = 0
            case TextMode.ALL_VISIBLE:
                text_mode_index = 1
            case TextMode.ONLY_TOP_CELL:
                text_mode_index = 2
            case _:
                raise NotImplementedError(f"Unhandled enum case {settings.text_mode}")
        self.page.texts_cob.setCurrentIndex(text_mode_index)
        
        self.page.text_layers_filter_enabled_cb.setChecked(settings.text_layers_filter_enabled)
        
        self.page.text_layers_filter_le.setText(settings.text_layers)
        
        match settings.layer_selection_mode:
            case LayerSelectionMode.ALL_VISIBLE_LAYERS:
                self.page.all_visible_layers_rb.setChecked(True)
                self.page.custom_layer_selection_rb.setChecked(False)
            case LayerSelectionMode.CUSTOM_LAYER_LIST:
                self.page.all_visible_layers_rb.setChecked(False)
                self.page.custom_layer_selection_rb.setChecked(True)
            case _:
                raise NotImplementedError(f"Unhandled enum case {settings.layer_selection_mode}")            
        
        self.page.custom_layers_le.setText(settings.custom_layers)
        
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

        self.on_color_changed()

    def on_file_format_changed(self):
        old_path = self.page.save_path_le.text.strip()
        if old_path != '':
            path = Path(old_path)
            settings = self.settings_from_ui()
            new_suffix = settings.file_format.value
            if path.suffix != new_suffix:
                path = path.with_suffix(new_suffix)
            self.page.save_path_le.setText(str(path))
        
    def on_figure_width_changed(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_figure_width_changed")
    
        self.page.figure_size_rb.setChecked(True)
        
        settings = self.settings_from_ui()
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)

        self.page.figure_height_sb.blockSignals(True)
        self.page.scaling_sb.blockSignals(True)

        self.page.figure_height_sb.setValue(design_info.fig_height_mm)
        self.page.scaling_sb.setValue(design_info.scaling)
        
        self.page.figure_height_sb.blockSignals(False)
        self.page.scaling_sb.blockSignals(False)
    
    def on_figure_height_changed(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_figure_height_changed")
    
        self.page.figure_size_rb.setChecked(True)

        settings = self.settings_from_ui()
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)
        
        width_mm = design_info.width_um / design_info.height_um * self.page.figure_height_sb.value


        settings = self.settings_from_ui()
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)

        self.page.figure_width_sb.blockSignals(True)
        self.page.scaling_sb.blockSignals(True)

        self.page.figure_width_sb.setValue(width_mm)
        self.page.scaling_sb.setValue(design_info.scaling)

        self.page.figure_width_sb.blockSignals(False)
        self.page.scaling_sb.blockSignals(False)

    def on_scaling_value_changed(self):
        if Debugging.DEBUG:
            debug("VectorFileExportDialog.on_scaling_value_changed")

        self.page.scaling_rb.setChecked(True)
            
        settings = self.settings_from_ui()
        design_info = DesignInfo.for_layout_view(pya.LayoutView.current(), settings)
        
        self.page.figure_width_sb.blockSignals(True)
        self.page.figure_height_sb.blockSignals(True)
        
        self.page.figure_width_sb.setValue(design_info.fig_width_mm)
        self.page.figure_height_sb.setValue(design_info.fig_height_mm)
    
        self.page.figure_width_sb.blockSignals(False)
        self.page.figure_height_sb.blockSignals(False)
    
    def on_color_changed(self):
        self.include_bg_color_cb.setEnabled(self.colors_cob.currentText == 'Color')
    
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

