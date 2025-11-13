"""
Main Dialog for Wind Turbine Earthwork Calculator V2

Tab-based UI for user-friendly parameter input.

Author: Wind Energy Site Planning
Version: 2.0
"""

import os
from pathlib import Path

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QDoubleSpinBox, QSpinBox, QGroupBox, QFormLayout,
    QCheckBox, QMessageBox, QProgressBar, QTextEdit
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon

from ..utils.logging_utils import get_plugin_logger


class MainDialog(QDialog):
    """
    Main dialog window with tab-based interface.
    
    Tabs:
    1. Eingabe (Input)
    2. Optimierung (Optimization)
    3. Geländeschnitte (Profiles)
    4. Ausgabe (Output)
    """
    
    # Signal emitted when user clicks "Start"
    processing_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.logger = get_plugin_logger()
        
        self.setWindowTitle("Erdmassenberechnung Windenergieanlagen")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout()
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.tab_input = self._create_input_tab()
        self.tab_optimization = self._create_optimization_tab()
        self.tab_profiles = self._create_profiles_tab()
        self.tab_output = self._create_output_tab()
        
        self.tabs.addTab(self.tab_input, "📂 Eingabe")
        self.tabs.addTab(self.tab_optimization, "⚙️ Optimierung")
        self.tabs.addTab(self.tab_profiles, "📊 Geländeschnitte")
        self.tabs.addTab(self.tab_output, "💾 Ausgabe")
        
        layout.addWidget(self.tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.setVisible(False)
        layout.addWidget(self.status_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_start = QPushButton("Berechnung starten")
        self.btn_start.setDefault(True)
        
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_start)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_input_tab(self):
        """Create input tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # DXF File Input
        group_dxf = QGroupBox("DXF-Datei")
        form_dxf = QFormLayout()
        
        self.input_dxf = QLineEdit()
        self.input_dxf.setPlaceholderText("Pfad zur DXF-Datei mit Kranstellflächen-Umriss...")
        
        btn_browse_dxf = QPushButton("Durchsuchen...")
        btn_browse_dxf.clicked.connect(self._browse_dxf)
        
        dxf_layout = QHBoxLayout()
        dxf_layout.addWidget(self.input_dxf)
        dxf_layout.addWidget(btn_browse_dxf)
        
        form_dxf.addRow("DXF-Datei:", dxf_layout)
        
        self.input_dxf_tolerance = QDoubleSpinBox()
        self.input_dxf_tolerance.setRange(0.001, 10.0)
        self.input_dxf_tolerance.setValue(0.01)
        self.input_dxf_tolerance.setDecimals(3)
        self.input_dxf_tolerance.setSuffix(" m")
        self.input_dxf_tolerance.setToolTip("Toleranz für Punktverbindungen beim DXF-Import")
        
        form_dxf.addRow("Punkt-Toleranz:", self.input_dxf_tolerance)
        
        group_dxf.setLayout(form_dxf)
        layout.addWidget(group_dxf)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_optimization_tab(self):
        """Create optimization tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Height Range
        group_height = QGroupBox("Höhenbereich")
        form_height = QFormLayout()
        
        self.input_min_height = QDoubleSpinBox()
        self.input_min_height.setRange(0, 9999)
        self.input_min_height.setValue(300.0)
        self.input_min_height.setDecimals(2)
        self.input_min_height.setSuffix(" m ü.NN")
        self.input_min_height.setToolTip("Minimale Plattformhöhe zum Testen")
        
        self.input_max_height = QDoubleSpinBox()
        self.input_max_height.setRange(0, 9999)
        self.input_max_height.setValue(310.0)
        self.input_max_height.setDecimals(2)
        self.input_max_height.setSuffix(" m ü.NN")
        self.input_max_height.setToolTip("Maximale Plattformhöhe zum Testen")
        
        self.input_height_step = QDoubleSpinBox()
        self.input_height_step.setRange(0.01, 10.0)
        self.input_height_step.setValue(0.1)
        self.input_height_step.setDecimals(2)
        self.input_height_step.setSuffix(" m")
        self.input_height_step.setToolTip("Schrittweite zwischen Höhen-Tests")
        
        form_height.addRow("Minimale Höhe:", self.input_min_height)
        form_height.addRow("Maximale Höhe:", self.input_max_height)
        form_height.addRow("Höhen-Schritt:", self.input_height_step)
        
        group_height.setLayout(form_height)
        layout.addWidget(group_height)
        
        # Slope Parameters
        group_slope = QGroupBox("Böschung")
        form_slope = QFormLayout()
        
        self.input_slope_angle = QDoubleSpinBox()
        self.input_slope_angle.setRange(15.0, 60.0)
        self.input_slope_angle.setValue(45.0)
        self.input_slope_angle.setDecimals(1)
        self.input_slope_angle.setSuffix(" °")
        self.input_slope_angle.setToolTip("Böschungswinkel (45° = 1:1)")
        
        form_slope.addRow("Böschungswinkel:", self.input_slope_angle)
        
        group_slope.setLayout(form_slope)
        layout.addWidget(group_slope)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_profiles_tab(self):
        """Create profiles tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Cross-Section Profiles (Querprofile)
        group_cross_profiles = QGroupBox("Querprofile")
        form_cross_profiles = QFormLayout()

        self.input_generate_cross_profiles = QCheckBox("Querprofile generieren")
        self.input_generate_cross_profiles.setChecked(True)
        self.input_generate_cross_profiles.setToolTip("Querprofile perpendikular zur Hauptorientierung")
        form_cross_profiles.addRow(self.input_generate_cross_profiles)

        self.input_cross_profile_spacing = QDoubleSpinBox()
        self.input_cross_profile_spacing.setRange(1.0, 50.0)
        self.input_cross_profile_spacing.setValue(10.0)
        self.input_cross_profile_spacing.setDecimals(1)
        self.input_cross_profile_spacing.setSuffix(" m")
        self.input_cross_profile_spacing.setToolTip("Abstand zwischen Querprofilen")

        self.input_cross_profile_overhang = QDoubleSpinBox()
        self.input_cross_profile_overhang.setRange(0.0, 50.0)
        self.input_cross_profile_overhang.setValue(10.0)
        self.input_cross_profile_overhang.setDecimals(1)
        self.input_cross_profile_overhang.setSuffix(" %")
        self.input_cross_profile_overhang.setToolTip("Überhang über Plattform-Rand hinaus")

        form_cross_profiles.addRow("Schnitt-Abstand:", self.input_cross_profile_spacing)
        form_cross_profiles.addRow("Überhang:", self.input_cross_profile_overhang)

        group_cross_profiles.setLayout(form_cross_profiles)
        layout.addWidget(group_cross_profiles)

        # Longitudinal Profiles (Längsprofile)
        group_long_profiles = QGroupBox("Längsprofile")
        form_long_profiles = QFormLayout()

        self.input_generate_long_profiles = QCheckBox("Längsprofile generieren")
        self.input_generate_long_profiles.setChecked(True)
        self.input_generate_long_profiles.setToolTip("Längsprofile parallel zur Hauptorientierung")
        form_long_profiles.addRow(self.input_generate_long_profiles)

        self.input_long_profile_spacing = QDoubleSpinBox()
        self.input_long_profile_spacing.setRange(1.0, 50.0)
        self.input_long_profile_spacing.setValue(10.0)
        self.input_long_profile_spacing.setDecimals(1)
        self.input_long_profile_spacing.setSuffix(" m")
        self.input_long_profile_spacing.setToolTip("Abstand zwischen Längsprofilen")

        self.input_long_profile_overhang = QDoubleSpinBox()
        self.input_long_profile_overhang.setRange(0.0, 50.0)
        self.input_long_profile_overhang.setValue(10.0)
        self.input_long_profile_overhang.setDecimals(1)
        self.input_long_profile_overhang.setSuffix(" %")
        self.input_long_profile_overhang.setToolTip("Überhang über Plattform-Rand hinaus")

        form_long_profiles.addRow("Schnitt-Abstand:", self.input_long_profile_spacing)
        form_long_profiles.addRow("Überhang:", self.input_long_profile_overhang)

        group_long_profiles.setLayout(form_long_profiles)
        layout.addWidget(group_long_profiles)

        # Visualization Settings
        group_visualization = QGroupBox("Visualisierung")
        form_visualization = QFormLayout()

        self.input_vertical_exaggeration = QDoubleSpinBox()
        self.input_vertical_exaggeration.setRange(1.0, 10.0)
        self.input_vertical_exaggeration.setValue(2.0)
        self.input_vertical_exaggeration.setDecimals(1)
        self.input_vertical_exaggeration.setSuffix(" x")
        self.input_vertical_exaggeration.setToolTip("Vertikale Überhöhung in Grafiken")

        form_visualization.addRow("Vert. Überhöhung:", self.input_vertical_exaggeration)

        group_visualization.setLayout(form_visualization)
        layout.addWidget(group_visualization)

        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_output_tab(self):
        """Create output tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Workspace Directory
        group_workspace = QGroupBox("Workspace")
        form_workspace = QFormLayout()
        
        self.input_workspace = QLineEdit()
        self.input_workspace.setPlaceholderText("Ordner für alle Ausgabedateien...")
        
        btn_browse_workspace = QPushButton("Durchsuchen...")
        btn_browse_workspace.clicked.connect(self._browse_workspace)
        
        workspace_layout = QHBoxLayout()
        workspace_layout.addWidget(self.input_workspace)
        workspace_layout.addWidget(btn_browse_workspace)
        
        form_workspace.addRow("Workspace-Ordner:", workspace_layout)
        
        # Info about structure
        info_label = QLabel(
            "<i>Struktur wird automatisch erstellt:</i><br>"
            "• ergebnisse/ - GeoPackage & HTML-Bericht<br>"
            "• gelaendeschnitte/ - PNG-Bilder<br>"
            "• cache/ - DEM-Kacheln"
        )
        info_label.setWordWrap(True)
        form_workspace.addRow("", info_label)
        
        group_workspace.setLayout(form_workspace)
        layout.addWidget(group_workspace)
        
        # Options
        group_options = QGroupBox("Optionen")
        form_options = QFormLayout()
        
        self.input_force_refresh = QCheckBox("DEM-Cache ignorieren (erneut herunterladen)")
        self.input_force_refresh.setChecked(False)
        
        form_options.addRow(self.input_force_refresh)
        
        group_options.setLayout(form_options)
        layout.addWidget(group_options)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _connect_signals(self):
        """Connect button signals."""
        self.btn_start.clicked.connect(self._on_start)
        self.btn_cancel.clicked.connect(self.reject)
    
    def _browse_dxf(self):
        """Browse for DXF file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "DXF-Datei auswählen",
            "",
            "DXF-Dateien (*.dxf)"
        )
        if filename:
            self.input_dxf.setText(filename)
    
    def _browse_workspace(self):
        """Browse for workspace directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Workspace-Ordner auswählen",
            ""
        )
        if directory:
            self.input_workspace.setText(directory)
    
    def _validate_inputs(self):
        """Validate user inputs."""
        errors = []
        
        # Check DXF file
        dxf_path = self.input_dxf.text().strip()
        if not dxf_path:
            errors.append("Bitte DXF-Datei auswählen")
        elif not os.path.exists(dxf_path):
            errors.append(f"DXF-Datei nicht gefunden: {dxf_path}")
        
        # Check workspace
        workspace = self.input_workspace.text().strip()
        if not workspace:
            errors.append("Bitte Workspace-Ordner auswählen")
        
        # Check height range
        min_h = self.input_min_height.value()
        max_h = self.input_max_height.value()
        if min_h >= max_h:
            errors.append("Minimale Höhe muss kleiner als maximale Höhe sein")
        
        if errors:
            QMessageBox.warning(
                self,
                "Ungültige Eingaben",
                "\n".join(errors)
            )
            return False
        
        return True
    
    def _on_start(self):
        """Handle start button click."""
        if not self._validate_inputs():
            return
        
        # Collect parameters
        params = {
            'dxf_file': self.input_dxf.text().strip(),
            'dxf_tolerance': self.input_dxf_tolerance.value(),
            'min_height': self.input_min_height.value(),
            'max_height': self.input_max_height.value(),
            'height_step': self.input_height_step.value(),
            'slope_angle': self.input_slope_angle.value(),
            'generate_cross_profiles': self.input_generate_cross_profiles.isChecked(),
            'cross_profile_spacing': self.input_cross_profile_spacing.value(),
            'cross_profile_overhang': self.input_cross_profile_overhang.value(),
            'generate_long_profiles': self.input_generate_long_profiles.isChecked(),
            'long_profile_spacing': self.input_long_profile_spacing.value(),
            'long_profile_overhang': self.input_long_profile_overhang.value(),
            'vertical_exaggeration': self.input_vertical_exaggeration.value(),
            'workspace': self.input_workspace.text().strip(),
            'force_refresh': self.input_force_refresh.isChecked()
        }
        
        # Emit signal
        self.processing_requested.emit(params)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_text.setVisible(True)
        self.status_text.clear()
        
        # Disable start button
        self.btn_start.setEnabled(False)
    
    def update_progress(self, value, message=""):
        """Update progress bar and status."""
        self.progress_bar.setValue(value)
        if message:
            self.status_text.append(message)
    
    def processing_finished(self, success=True, message=""):
        """Called when processing finishes."""
        self.progress_bar.setVisible(False)
        self.btn_start.setEnabled(True)
        
        if success:
            QMessageBox.information(
                self,
                "Fertig",
                message or "Berechnung erfolgreich abgeschlossen!"
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Fehler",
                message or "Ein Fehler ist aufgetreten."
            )
