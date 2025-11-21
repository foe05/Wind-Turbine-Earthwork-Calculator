"""
Main Dialog for Wind Turbine Earthwork Calculator V2 - Multi-Surface Edition

Tab-based UI for user-friendly parameter input with support for 4 surface types:
- Crane pad (Kranstellfläche)
- Foundation (Fundamentfläche)
- Boom surface (Auslegerfläche)
- Blade storage (Blattlagerfläche)

Author: Wind Energy Site Planning
Version: 2.0 - Multi-Surface Extension
"""

import os
from pathlib import Path

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QDoubleSpinBox, QSpinBox, QGroupBox, QFormLayout,
    QCheckBox, QMessageBox, QProgressBar, QTextEdit, QScrollArea
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon

from ..utils.logging_utils import get_plugin_logger


class MainDialog(QDialog):
    """
    Main dialog window with tab-based interface for multi-surface earthwork calculation.

    Tabs:
    1. Eingabe (Input) - DXF files and surface parameters
    2. Optimierung (Optimization) - Height range and slope parameters
    3. Geländeschnitte (Profiles) - Profile generation settings
    4. Ausgabe (Output) - Workspace and export settings
    """

    # Signal emitted when user clicks "Start"
    processing_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.logger = get_plugin_logger()

        self.setWindowTitle("Erdmassenberechnung Windenergieanlagen - Multi-Flächen")
        self.setMinimumSize(900, 700)

        self._init_ui()
        self._connect_signals()
        self._setup_validators()

        # Initialize button visibility for first tab
        self._on_tab_changed(0)

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

        # Buttons (dynamically shown based on current tab)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_next = QPushButton("Weiter →")
        self.btn_next.setDefault(True)
        self.btn_start = QPushButton("Berechnung starten")
        self.btn_start.setDefault(True)
        self.btn_start.setVisible(False)  # Only shown on last tab

        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_next)
        button_layout.addWidget(self.btn_start)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_input_tab(self):
        """Create input tab with DXF file inputs and surface parameters."""
        # Create scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        widget = QWidget()
        layout = QVBoxLayout()

        # ========== DXF Files Group ==========
        group_dxf = QGroupBox("DXF-Dateien")
        form_dxf = QFormLayout()

        # Crane pad DXF
        self.input_dxf_crane = QLineEdit()
        self.input_dxf_crane.setPlaceholderText("Pfad zur DXF-Datei mit Kranstellflächen-Umriss...")
        btn_browse_crane = QPushButton("Durchsuchen...")
        btn_browse_crane.clicked.connect(lambda: self._browse_dxf(self.input_dxf_crane, "Kranstellfläche"))

        crane_layout = QHBoxLayout()
        crane_layout.addWidget(self.input_dxf_crane)
        crane_layout.addWidget(btn_browse_crane)
        form_dxf.addRow("Kranstellfläche:", crane_layout)

        # Foundation DXF
        self.input_dxf_foundation = QLineEdit()
        self.input_dxf_foundation.setPlaceholderText("Pfad zur DXF-Datei mit Fundamentflächen-Umriss...")
        btn_browse_foundation = QPushButton("Durchsuchen...")
        btn_browse_foundation.clicked.connect(lambda: self._browse_dxf(self.input_dxf_foundation, "Fundamentfläche"))

        foundation_layout = QHBoxLayout()
        foundation_layout.addWidget(self.input_dxf_foundation)
        foundation_layout.addWidget(btn_browse_foundation)
        form_dxf.addRow("Fundamentfläche:", foundation_layout)

        # Boom surface DXF (optional)
        self.input_dxf_boom = QLineEdit()
        self.input_dxf_boom.setPlaceholderText("Optional: DXF-Datei mit Auslegerflächen-Umriss...")
        btn_browse_boom = QPushButton("Durchsuchen...")
        btn_browse_boom.clicked.connect(lambda: self._browse_dxf(self.input_dxf_boom, "Auslegerfläche"))

        boom_layout = QHBoxLayout()
        boom_layout.addWidget(self.input_dxf_boom)
        boom_layout.addWidget(btn_browse_boom)
        form_dxf.addRow("Auslegerfläche (optional):", boom_layout)

        # Blade storage DXF (optional)
        self.input_dxf_rotor = QLineEdit()
        self.input_dxf_rotor.setPlaceholderText("Optional: DXF-Datei mit Blattlagerflächen-Umriss...")
        btn_browse_rotor = QPushButton("Durchsuchen...")
        btn_browse_rotor.clicked.connect(lambda: self._browse_dxf(self.input_dxf_rotor, "Blattlagerfläche"))

        rotor_layout = QHBoxLayout()
        rotor_layout.addWidget(self.input_dxf_rotor)
        rotor_layout.addWidget(btn_browse_rotor)
        form_dxf.addRow("Blattlagerfläche (optional):", rotor_layout)

        # Holms DXF (optional)
        self.input_dxf_holms = QLineEdit()
        self.input_dxf_holms.setPlaceholderText("Optional: DXF-Datei mit Holmen (Rotorblatt-Auflagepunkten)...")
        btn_browse_holms = QPushButton("Durchsuchen...")
        btn_browse_holms.clicked.connect(lambda: self._browse_dxf(self.input_dxf_holms, "Holme"))

        holms_layout = QHBoxLayout()
        holms_layout.addWidget(self.input_dxf_holms)
        holms_layout.addWidget(btn_browse_holms)
        form_dxf.addRow("Holme (optional):", holms_layout)

        # DXF tolerance
        self.input_dxf_tolerance = QDoubleSpinBox()
        self.input_dxf_tolerance.setRange(0.001, 10.0)
        self.input_dxf_tolerance.setValue(0.01)
        self.input_dxf_tolerance.setDecimals(3)
        self.input_dxf_tolerance.setSuffix(" m")
        self.input_dxf_tolerance.setToolTip("Toleranz für Punktverbindungen beim DXF-Import")
        form_dxf.addRow("Punkt-Toleranz:", self.input_dxf_tolerance)

        group_dxf.setLayout(form_dxf)
        layout.addWidget(group_dxf)

        # ========== Foundation Parameters Group ==========
        group_foundation = QGroupBox("Fundamentparameter")
        form_foundation = QFormLayout()

        # FOK (Fundamentoberkante)
        self.input_fok = QDoubleSpinBox()
        self.input_fok.setRange(0, 9999)
        self.input_fok.setValue(305.50)
        self.input_fok.setDecimals(2)
        self.input_fok.setSuffix(" m ü.NN")
        self.input_fok.setToolTip("Behördlich vorgegebene Fundamentoberkante")
        form_foundation.addRow("Fundamentoberkante (FOK):", self.input_fok)

        fok_info = QLabel("<i>Behördlich vorgegebene Höhe</i>")
        fok_info.setStyleSheet("color: gray; font-size: 10px;")
        form_foundation.addRow("", fok_info)

        # Foundation depth
        self.input_foundation_depth = QDoubleSpinBox()
        self.input_foundation_depth.setRange(0.5, 10.0)
        self.input_foundation_depth.setValue(3.5)
        self.input_foundation_depth.setDecimals(2)
        self.input_foundation_depth.setSuffix(" m")
        self.input_foundation_depth.setToolTip("Tiefe unter FOK bis Fundamentsohle")
        form_foundation.addRow("Fundamenttiefe:", self.input_foundation_depth)

        # Foundation diameter (optional)
        self.input_foundation_diameter = QDoubleSpinBox()
        self.input_foundation_diameter.setRange(0, 50.0)
        self.input_foundation_diameter.setValue(20.0)
        self.input_foundation_diameter.setDecimals(1)
        self.input_foundation_diameter.setSuffix(" m")
        self.input_foundation_diameter.setToolTip("Optional: Durchmesser falls nicht aus DXF ersichtlich")
        form_foundation.addRow("Fundamentdurchmesser:", self.input_foundation_diameter)

        group_foundation.setLayout(form_foundation)
        layout.addWidget(group_foundation)

        # ========== Crane Pad Parameters Group ==========
        group_crane = QGroupBox("Kranstellflächen-Parameter")
        form_crane = QFormLayout()

        # Search range below FOK
        self.input_search_below_fok = QDoubleSpinBox()
        self.input_search_below_fok.setRange(0, 5.0)
        self.input_search_below_fok.setValue(0.5)
        self.input_search_below_fok.setDecimals(2)
        self.input_search_below_fok.setSuffix(" m")
        self.input_search_below_fok.setToolTip("Minimaler Abstand unter FOK für Optimierungssuche")
        self.input_search_below_fok.valueChanged.connect(self._update_search_range_display)
        form_crane.addRow("Suchbereich unter FOK:", self.input_search_below_fok)

        # Search range above FOK
        self.input_search_above_fok = QDoubleSpinBox()
        self.input_search_above_fok.setRange(0, 5.0)
        self.input_search_above_fok.setValue(0.5)
        self.input_search_above_fok.setDecimals(2)
        self.input_search_above_fok.setSuffix(" m")
        self.input_search_above_fok.setToolTip("Maximaler Abstand über FOK für Optimierungssuche")
        self.input_search_above_fok.valueChanged.connect(self._update_search_range_display)
        form_crane.addRow("Suchbereich über FOK:", self.input_search_above_fok)

        # Display calculated search range
        self.label_search_range = QLabel()
        self._update_search_range_display()
        form_crane.addRow("→ Suchbereich:", self.label_search_range)

        # Gravel thickness
        self.input_gravel_thickness = QDoubleSpinBox()
        self.input_gravel_thickness.setRange(0, 2.0)
        self.input_gravel_thickness.setValue(0.5)
        self.input_gravel_thickness.setDecimals(2)
        self.input_gravel_thickness.setSuffix(" m")
        self.input_gravel_thickness.setToolTip("Dicke der Schotterschicht auf Kranstellfläche")
        form_crane.addRow("Schotterschichtdicke:", self.input_gravel_thickness)

        gravel_info = QLabel("<i>Wird von Kranstellfläche abgezogen</i>")
        gravel_info.setStyleSheet("color: gray; font-size: 10px;")
        form_crane.addRow("", gravel_info)

        group_crane.setLayout(form_crane)
        layout.addWidget(group_crane)

        # ========== Boom Surface Parameters Group ==========
        group_boom = QGroupBox("Auslegerflächen-Parameter")
        form_boom = QFormLayout()

        # Longitudinal slope
        self.input_boom_slope = QDoubleSpinBox()
        self.input_boom_slope.setRange(2.0, 8.0)
        self.input_boom_slope.setValue(5.0)
        self.input_boom_slope.setDecimals(1)
        self.input_boom_slope.setSuffix(" %")
        self.input_boom_slope.setToolTip("Längsneigung der Auslegerfläche (2-8%)")
        form_boom.addRow("Längsneigung:", self.input_boom_slope)

        # Auto-adjust slope
        self.input_boom_auto_slope = QCheckBox("Neigung automatisch an Gelände anpassen")
        self.input_boom_auto_slope.setChecked(True)
        self.input_boom_auto_slope.setToolTip(
            "Passt Neigung innerhalb zulässigem Bereich an Geländeneigung an"
        )
        form_boom.addRow(self.input_boom_auto_slope)

        group_boom.setLayout(form_boom)
        layout.addWidget(group_boom)

        # ========== Blade Storage Parameters Group ==========
        group_rotor = QGroupBox("Blattlagerflächen-Parameter")
        form_rotor = QFormLayout()

        # Height offset from crane pad
        self.input_rotor_height_offset = QDoubleSpinBox()
        self.input_rotor_height_offset.setRange(-5.0, 5.0)
        self.input_rotor_height_offset.setValue(0.0)
        self.input_rotor_height_offset.setDecimals(2)
        self.input_rotor_height_offset.setSuffix(" m")
        self.input_rotor_height_offset.setToolTip(
            "Höhendifferenz zur Kranstellfläche (positiv = höher, negativ = tiefer)"
        )
        form_rotor.addRow("Höhendifferenz zu Kranstellfläche:", self.input_rotor_height_offset)

        rotor_info = QLabel("<i>Positiv = höher, Negativ = tiefer</i>")
        rotor_info.setStyleSheet("color: gray; font-size: 10px;")
        form_rotor.addRow("", rotor_info)

        group_rotor.setLayout(form_rotor)
        layout.addWidget(group_rotor)

        layout.addStretch()
        widget.setLayout(layout)
        scroll.setWidget(widget)
        return scroll

    def _create_optimization_tab(self):
        """Create optimization tab."""
        # Create scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        widget = QWidget()
        layout = QVBoxLayout()

        # Height Optimization
        group_opt = QGroupBox("Optimierungseinstellungen")
        form_opt = QFormLayout()

        self.input_height_step = QDoubleSpinBox()
        self.input_height_step.setRange(0.01, 1.0)
        self.input_height_step.setValue(0.1)
        self.input_height_step.setDecimals(2)
        self.input_height_step.setSuffix(" m")
        self.input_height_step.setToolTip("Schrittweite für Höhenoptimierung")
        form_opt.addRow("Höhen-Schritt:", self.input_height_step)

        group_opt.setLayout(form_opt)
        layout.addWidget(group_opt)

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
        scroll.setWidget(widget)
        return scroll

    def _create_profiles_tab(self):
        """Create profiles tab."""
        # Create scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        widget = QWidget()
        layout = QVBoxLayout()

        # Bounding Box Configuration
        group_bbox = QGroupBox("Bauplatz-Bereich (Bounding Box)")
        form_bbox = QFormLayout()

        info_bbox = QLabel(
            "<i>Die Schnitte werden über den gesamten Bauplatz erstellt.<br>"
            "Die Bounding Box umfasst alle Flächen und ist an der<br>"
            "Hauptachse (längste Kante) der Kranfläche ausgerichtet.</i>"
        )
        info_bbox.setWordWrap(True)
        info_bbox.setStyleSheet("color: gray; font-size: 10px;")
        form_bbox.addRow("", info_bbox)

        self.input_bbox_buffer = QDoubleSpinBox()
        self.input_bbox_buffer.setRange(0.0, 50.0)
        self.input_bbox_buffer.setValue(10.0)
        self.input_bbox_buffer.setDecimals(1)
        self.input_bbox_buffer.setSuffix(" %")
        self.input_bbox_buffer.setToolTip(
            "Zusätzlicher Puffer um alle Flächen herum als Prozent der Bauplatzgröße"
        )
        form_bbox.addRow("Buffer-Zone:", self.input_bbox_buffer)

        group_bbox.setLayout(form_bbox)
        layout.addWidget(group_bbox)

        # Cross-Section Profiles
        group_cross = QGroupBox("Querprofile")
        form_cross = QFormLayout()

        self.input_generate_cross_profiles = QCheckBox("Querprofile generieren")
        self.input_generate_cross_profiles.setChecked(True)
        form_cross.addRow(self.input_generate_cross_profiles)

        self.input_cross_profile_spacing = QDoubleSpinBox()
        self.input_cross_profile_spacing.setRange(1.0, 50.0)
        self.input_cross_profile_spacing.setValue(10.0)
        self.input_cross_profile_spacing.setDecimals(1)
        self.input_cross_profile_spacing.setSuffix(" m")
        form_cross.addRow("Schnitt-Abstand:", self.input_cross_profile_spacing)

        group_cross.setLayout(form_cross)
        layout.addWidget(group_cross)

        # Longitudinal Profiles
        group_long = QGroupBox("Längsprofile")
        form_long = QFormLayout()

        self.input_generate_long_profiles = QCheckBox("Längsprofile generieren")
        self.input_generate_long_profiles.setChecked(True)
        form_long.addRow(self.input_generate_long_profiles)

        self.input_long_profile_spacing = QDoubleSpinBox()
        self.input_long_profile_spacing.setRange(1.0, 50.0)
        self.input_long_profile_spacing.setValue(10.0)
        self.input_long_profile_spacing.setDecimals(1)
        self.input_long_profile_spacing.setSuffix(" m")
        form_long.addRow("Schnitt-Abstand:", self.input_long_profile_spacing)

        group_long.setLayout(form_long)
        layout.addWidget(group_long)

        # Visualization
        group_viz = QGroupBox("Visualisierung")
        form_viz = QFormLayout()

        self.input_vertical_exaggeration = QDoubleSpinBox()
        self.input_vertical_exaggeration.setRange(1.0, 10.0)
        self.input_vertical_exaggeration.setValue(2.0)
        self.input_vertical_exaggeration.setDecimals(1)
        self.input_vertical_exaggeration.setSuffix(" x")
        form_viz.addRow("Vert. Überhöhung:", self.input_vertical_exaggeration)

        group_viz.setLayout(form_viz)
        layout.addWidget(group_viz)

        layout.addStretch()
        widget.setLayout(layout)
        scroll.setWidget(widget)
        return scroll

    def _create_output_tab(self):
        """Create output tab."""
        # Create scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        widget = QWidget()
        layout = QVBoxLayout()

        # Workspace
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
        scroll.setWidget(widget)
        return scroll

    def _on_tab_changed(self, index):
        """Handle tab change - show/hide appropriate buttons."""
        # Last tab (index 3) shows "Start" button, others show "Next" button
        is_last_tab = (index == self.tabs.count() - 1)

        self.btn_next.setVisible(not is_last_tab)
        self.btn_start.setVisible(is_last_tab)

        # Set appropriate button as default
        if is_last_tab:
            self.btn_start.setDefault(True)
        else:
            self.btn_next.setDefault(True)

    def _on_next(self):
        """Move to next tab."""
        current = self.tabs.currentIndex()
        if current < self.tabs.count() - 1:
            self.tabs.setCurrentIndex(current + 1)

    def _connect_signals(self):
        """Connect button signals."""
        self.btn_start.clicked.connect(self._on_start)
        self.btn_next.clicked.connect(self._on_next)
        self.btn_cancel.clicked.connect(self.reject)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _setup_validators(self):
        """Setup value validators and constraints."""
        # Connect FOK change to update search range display
        self.input_fok.valueChanged.connect(self._update_search_range_display)

    def _browse_dxf(self, line_edit: QLineEdit, surface_name: str):
        """Browse for DXF file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"DXF-Datei für {surface_name} auswählen",
            "",
            "DXF-Dateien (*.dxf)"
        )
        if filename:
            line_edit.setText(filename)

    def _browse_workspace(self):
        """Browse for workspace directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Workspace-Ordner auswählen",
            ""
        )
        if directory:
            self.input_workspace.setText(directory)

    def _update_search_range_display(self):
        """Update the search range display label."""
        fok = self.input_fok.value()
        below = self.input_search_below_fok.value()
        above = self.input_search_above_fok.value()

        min_height = fok - below
        max_height = fok + above

        self.label_search_range.setText(
            f"<b>{min_height:.2f} - {max_height:.2f} m ü.NN</b>"
        )

    def _validate_inputs(self):
        """Validate user inputs."""
        errors = []

        # Check required DXF files (Kranstellfläche and Fundament)
        required_dxf_inputs = [
            ("Kranstellfläche", self.input_dxf_crane),
            ("Fundamentfläche", self.input_dxf_foundation),
        ]

        for name, line_edit in required_dxf_inputs:
            path = line_edit.text().strip()
            if not path:
                errors.append(f"Bitte DXF-Datei für {name} auswählen")
            elif not os.path.exists(path):
                errors.append(f"DXF-Datei für {name} nicht gefunden: {path}")

        # Check optional DXF files (only validate if provided)
        optional_dxf_inputs = [
            ("Auslegerfläche", self.input_dxf_boom),
            ("Blattlagerfläche", self.input_dxf_rotor),
            ("Holme", self.input_dxf_holms),
        ]

        for name, line_edit in optional_dxf_inputs:
            path = line_edit.text().strip()
            if path and not os.path.exists(path):
                errors.append(f"DXF-Datei für {name} nicht gefunden: {path}")

        # Check workspace
        workspace = self.input_workspace.text().strip()
        if not workspace:
            errors.append("Bitte Workspace-Ordner auswählen")

        # Check FOK is reasonable
        fok = self.input_fok.value()
        if fok < 0 or fok > 9999:
            errors.append(f"FOK {fok} m ü.NN scheint unrealistisch")

        # Check search ranges
        if self.input_search_below_fok.value() < 0:
            errors.append("Suchbereich unter FOK muss positiv sein")
        if self.input_search_above_fok.value() < 0:
            errors.append("Suchbereich über FOK muss positiv sein")

        # Check boom slope is in range
        boom_slope = self.input_boom_slope.value()
        if boom_slope < 2.0 or boom_slope > 8.0:
            errors.append(f"Auslegerflächen-Neigung {boom_slope}% außerhalb zulässigem Bereich [2%, 8%]")

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

        # Collect all parameters
        params = {
            # DXF files
            'dxf_crane': self.input_dxf_crane.text().strip(),
            'dxf_foundation': self.input_dxf_foundation.text().strip(),
            'dxf_boom': self.input_dxf_boom.text().strip() if self.input_dxf_boom.text().strip() else None,
            'dxf_rotor': self.input_dxf_rotor.text().strip() if self.input_dxf_rotor.text().strip() else None,
            'dxf_tolerance': self.input_dxf_tolerance.value(),

            # Holms DXF (optional)
            'holm_dxf_path': self.input_dxf_holms.text().strip() if self.input_dxf_holms.text().strip() else None,

            # Foundation parameters
            'fok': self.input_fok.value(),
            'foundation_depth': self.input_foundation_depth.value(),
            'foundation_diameter': self.input_foundation_diameter.value(),

            # Crane pad parameters
            'search_range_below_fok': self.input_search_below_fok.value(),
            'search_range_above_fok': self.input_search_above_fok.value(),
            'gravel_thickness': self.input_gravel_thickness.value(),

            # Boom surface parameters
            'boom_slope': self.input_boom_slope.value(),
            'boom_auto_slope': self.input_boom_auto_slope.isChecked(),

            # Rotor storage parameters
            'rotor_height_offset': self.input_rotor_height_offset.value(),

            # Optimization parameters
            'height_step': self.input_height_step.value(),
            'slope_angle': self.input_slope_angle.value(),

            # Profile parameters
            'bbox_buffer': self.input_bbox_buffer.value(),
            'generate_cross_profiles': self.input_generate_cross_profiles.isChecked(),
            'cross_profile_spacing': self.input_cross_profile_spacing.value(),
            'generate_long_profiles': self.input_generate_long_profiles.isChecked(),
            'long_profile_spacing': self.input_long_profile_spacing.value(),
            'vertical_exaggeration': self.input_vertical_exaggeration.value(),

            # Output parameters
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
