"""
Main Dialog for Wind Turbine Earthwork Calculator V2 - Multi-Surface Edition

Tab-based UI for user-friendly parameter input with support for 4 surface types:
- Crane pad (Kranstellfläche)
- Foundation (Fundamentfläche)
- Boom surface (Auslegerfläche)
- Blade storage (Blattlagerfläche)

Author: Wind Energy Site Planning
Version: 2.0.0 - Multi-Surface Extension
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
from ..utils.validation import ValidationError, validate_file_exists
from ..utils.i18n import get_message, get_language
from ..utils.error_messages import ERROR_MESSAGES
from ..core.dxf_importer import DXFImporter


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

        # Road access DXF (optional)
        self.input_dxf_road = QLineEdit()
        self.input_dxf_road.setPlaceholderText("Optional: DXF-Datei mit Zufahrtsstraßen-Umriss...")
        btn_browse_road = QPushButton("Durchsuchen...")
        btn_browse_road.clicked.connect(lambda: self._browse_dxf(self.input_dxf_road, "Zufahrtsstraße"))

        road_layout = QHBoxLayout()
        road_layout.addWidget(self.input_dxf_road)
        road_layout.addWidget(btn_browse_road)
        form_dxf.addRow("Zufahrtsstraße (optional):", road_layout)

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

        # ========== Road Access Parameters Group ==========
        group_road = QGroupBox("Zufahrtsstraßen-Parameter")
        form_road = QFormLayout()

        # Longitudinal slope
        self.input_road_slope = QDoubleSpinBox()
        self.input_road_slope.setRange(1.0, 15.0)
        self.input_road_slope.setValue(8.0)
        self.input_road_slope.setDecimals(1)
        self.input_road_slope.setSuffix(" %")
        self.input_road_slope.setToolTip("Maximale Längsneigung der Zufahrtsstraße (Richtung wird automatisch erkannt)")
        form_road.addRow("Maximale Längsneigung:", self.input_road_slope)

        road_slope_info = QLabel("<i>Richtung (ansteigend/abfallend) wird automatisch vom Gelände erkannt</i>")
        road_slope_info.setStyleSheet("color: gray; font-size: 10px;")
        form_road.addRow("", road_slope_info)

        # Enable gravel
        self.input_road_gravel_enabled = QCheckBox("Zufahrt schottern")
        self.input_road_gravel_enabled.setChecked(True)
        self.input_road_gravel_enabled.setToolTip("Aktivieren um Schotterschicht auf Zufahrt aufzubringen")
        self.input_road_gravel_enabled.stateChanged.connect(self._toggle_road_gravel)
        form_road.addRow(self.input_road_gravel_enabled)

        # Gravel thickness
        self.input_road_gravel_thickness = QDoubleSpinBox()
        self.input_road_gravel_thickness.setRange(0.1, 1.0)
        self.input_road_gravel_thickness.setValue(0.3)
        self.input_road_gravel_thickness.setDecimals(2)
        self.input_road_gravel_thickness.setSuffix(" m")
        self.input_road_gravel_thickness.setToolTip("Dicke der Schotterschicht auf Zufahrtsstraße")
        form_road.addRow("Schotterdicke Zufahrt:", self.input_road_gravel_thickness)

        road_gravel_info = QLabel("<i>Wird von Oberkante Zufahrt abgezogen für Planum</i>")
        road_gravel_info.setStyleSheet("color: gray; font-size: 10px;")
        form_road.addRow("", road_gravel_info)

        # Connection info
        road_connection_info = QLabel("<i>Zufahrt schließt an Kranstellfläche auf gleicher Höhe an</i>")
        road_connection_info.setStyleSheet("color: #0066cc; font-size: 10px;")
        form_road.addRow("", road_connection_info)

        group_road.setLayout(form_road)
        layout.addWidget(group_road)

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

        # Uncertainty Analysis
        group_uncertainty = QGroupBox("Unsicherheitsanalyse (Monte Carlo)")
        form_uncertainty = QFormLayout()

        # Enable uncertainty analysis
        self.input_uncertainty_enabled = QCheckBox("Unsicherheitsanalyse aktivieren")
        self.input_uncertainty_enabled.setChecked(False)
        self.input_uncertainty_enabled.setToolTip(
            "Führt Monte-Carlo-Simulation durch, um Unsicherheiten in den Ergebnissen zu quantifizieren"
        )
        self.input_uncertainty_enabled.stateChanged.connect(self._on_uncertainty_toggled)
        form_uncertainty.addRow(self.input_uncertainty_enabled)

        # Monte Carlo samples
        self.input_mc_samples = QSpinBox()
        self.input_mc_samples.setRange(100, 10000)
        self.input_mc_samples.setValue(1000)
        self.input_mc_samples.setSingleStep(100)
        self.input_mc_samples.setToolTip("Anzahl der Monte-Carlo-Samples (mehr = genauer, aber langsamer)")
        self.input_mc_samples.setEnabled(False)
        form_uncertainty.addRow("Monte Carlo Samples:", self.input_mc_samples)

        # Terrain type for DEM uncertainty
        from qgis.PyQt.QtWidgets import QComboBox
        self.input_terrain_type = QComboBox()
        self.input_terrain_type.addItems([
            "Flach (σ = 7.5 cm)",
            "Moderat (σ = 10 cm)",
            "Steil/Bewaldet (σ = 15 cm)"
        ])
        self.input_terrain_type.setCurrentIndex(0)
        self.input_terrain_type.setToolTip(
            "DEM-Unsicherheit basierend auf Geländetyp (nach deutschen Standards)"
        )
        self.input_terrain_type.setEnabled(False)
        form_uncertainty.addRow("Geländetyp (DEM-Unsicherheit):", self.input_terrain_type)

        # DEM uncertainty info
        dem_info = QLabel(
            "<i>DEM-Unsicherheit basiert auf offiziellen deutschen Spezifikationen<br>"
            "(hoehendaten.de: ±15-30cm bei 95% Konfidenz)</i>"
        )
        dem_info.setWordWrap(True)
        dem_info.setStyleSheet("color: gray; font-size: 10px;")
        form_uncertainty.addRow("", dem_info)

        # Foundation depth uncertainty
        self.input_foundation_depth_std = QDoubleSpinBox()
        self.input_foundation_depth_std.setRange(0, 0.5)
        self.input_foundation_depth_std.setValue(0.1)
        self.input_foundation_depth_std.setDecimals(2)
        self.input_foundation_depth_std.setSuffix(" m (σ)")
        self.input_foundation_depth_std.setToolTip("Standardabweichung der Fundamenttiefe")
        self.input_foundation_depth_std.setEnabled(False)
        form_uncertainty.addRow("Fundamenttiefe-Unsicherheit:", self.input_foundation_depth_std)

        # Slope angle uncertainty
        self.input_slope_angle_std = QDoubleSpinBox()
        self.input_slope_angle_std.setRange(0, 10.0)
        self.input_slope_angle_std.setValue(3.0)
        self.input_slope_angle_std.setDecimals(1)
        self.input_slope_angle_std.setSuffix(" ° (σ)")
        self.input_slope_angle_std.setToolTip("Standardabweichung des Böschungswinkels")
        self.input_slope_angle_std.setEnabled(False)
        form_uncertainty.addRow("Böschungswinkel-Unsicherheit:", self.input_slope_angle_std)

        group_uncertainty.setLayout(form_uncertainty)
        layout.addWidget(group_uncertainty)

        layout.addStretch()
        widget.setLayout(layout)
        scroll.setWidget(widget)
        return scroll

    def _on_uncertainty_toggled(self, state):
        """Enable/disable uncertainty input fields based on checkbox state."""
        enabled = state == Qt.Checked
        self.input_mc_samples.setEnabled(enabled)
        self.input_terrain_type.setEnabled(enabled)
        self.input_foundation_depth_std.setEnabled(enabled)
        self.input_slope_angle_std.setEnabled(enabled)

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

    def _show_validation_error(self, title: str, error: str):
        """
        Display validation error with bilingual message and fix suggestions.

        Args:
            title (str): Error dialog title
            error (str): Error message (already formatted with fix suggestions)
        """
        # Format message with line breaks for better readability
        formatted_error = error.replace('\n', '\n\n')

        QMessageBox.critical(
            self,
            title,
            formatted_error
        )

    def _validate_dxf_file(self, file_path: str, surface_name: str) -> bool:
        """
        Validate a DXF file with enhanced validation.

        Args:
            file_path (str): Path to DXF file
            surface_name (str): Name of surface for error messages

        Returns:
            bool: True if validation passed, False otherwise
        """
        try:
            # Validate file exists and has correct extension
            validate_file_exists(file_path, extension='.dxf')

            # Try to open DXF file and perform basic validation
            try:
                importer = DXFImporter(file_path, tolerance=0.01)

                # Get available layers
                layers = importer.get_available_layers()
                if not layers:
                    lang = get_language()
                    error_msg = get_message('dxf_no_entities', ERROR_MESSAGES)
                    fix_msg = ERROR_MESSAGES['dxf_no_entities']['fix'][lang]
                    raise ValidationError(f"{error_msg}\n{fix_msg}")

                # Detect coordinate system and provide feedback
                crs_info = importer.detect_coordinate_system()
                if crs_info and crs_info.get('suggested_epsg'):
                    suggested_epsg = crs_info['suggested_epsg']
                    confidence = crs_info.get('confidence', 'unknown')
                    self.logger.info(
                        f"DXF {surface_name}: Detected CRS EPSG:{suggested_epsg} "
                        f"(confidence: {confidence})"
                    )

                # Validate entity types
                entity_stats = importer.validate_entity_types()
                if entity_stats['unsupported_entities'] > 0:
                    self.logger.warning(
                        f"DXF {surface_name}: Found {entity_stats['unsupported_entities']} "
                        f"unsupported entities. Supported entities: {entity_stats['supported_entities']}"
                    )

                return True

            except ImportError as e:
                # Handle ezdxf not installed
                lang = get_language()
                error_msg = get_message('ezdxf_not_installed', ERROR_MESSAGES)
                fix_msg = ERROR_MESSAGES['ezdxf_not_installed']['fix'][lang]
                self._show_validation_error(
                    "Import Error" if lang == 'en' else "Import-Fehler",
                    f"{error_msg}\n\n{fix_msg}"
                )
                return False

            except Exception as e:
                # Handle DXF reading errors
                lang = get_language()
                error_msg = get_message('dxf_read_error', ERROR_MESSAGES, error=str(e))
                fix_msg = ERROR_MESSAGES['dxf_read_error']['fix'][lang]
                self._show_validation_error(
                    "DXF Error" if lang == 'en' else "DXF-Fehler",
                    f"{error_msg}\n\n{fix_msg}"
                )
                return False

        except ValidationError as e:
            lang = get_language()
            self._show_validation_error(
                "Validation Error" if lang == 'en' else "Validierungsfehler",
                str(e)
            )
            return False

        except Exception as e:
            # Catch-all for unexpected errors
            lang = get_language()
            self._show_validation_error(
                "Unexpected Error" if lang == 'en' else "Unerwarteter Fehler",
                str(e)
            )
            return False

    def _browse_dxf(self, line_edit: QLineEdit, surface_name: str):
        """Browse for DXF file with validation."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"DXF-Datei für {surface_name} auswählen",
            "",
            "DXF-Dateien (*.dxf)"
        )
        if filename:
            # Validate the selected DXF file
            if self._validate_dxf_file(filename, surface_name):
                line_edit.setText(filename)
                self.logger.info(f"DXF file validated successfully: {filename}")

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

    def _toggle_road_gravel(self, state):
        """Toggle road gravel thickness input based on checkbox state."""
        self.input_road_gravel_thickness.setEnabled(state == Qt.Checked)

    def _validate_inputs(self):
        """Validate user inputs with enhanced bilingual validation."""
        errors = []
        lang = get_language()

        # Check required DXF files (Kranstellfläche and Fundament)
        required_dxf_inputs = [
            ("Kranstellfläche", self.input_dxf_crane, "Crane pad" if lang == 'en' else "Kranstellfläche"),
            ("Fundamentfläche", self.input_dxf_foundation, "Foundation" if lang == 'en' else "Fundamentfläche"),
        ]

        for de_name, line_edit, display_name in required_dxf_inputs:
            path = line_edit.text().strip()
            if not path:
                if lang == 'en':
                    errors.append(f"Please select DXF file for {display_name}")
                else:
                    errors.append(f"Bitte DXF-Datei für {display_name} auswählen")
            else:
                try:
                    validate_file_exists(path, extension='.dxf')
                except ValidationError as e:
                    errors.append(f"{display_name}: {str(e)}")

        # Check optional DXF files (only validate if provided)
        optional_dxf_inputs = [
            ("Auslegerfläche", self.input_dxf_boom, "Boom surface" if lang == 'en' else "Auslegerfläche"),
            ("Blattlagerfläche", self.input_dxf_rotor, "Blade storage" if lang == 'en' else "Blattlagerfläche"),
            ("Holme", self.input_dxf_holms, "Holms" if lang == 'en' else "Holme"),
            ("Zufahrtsstraße", self.input_dxf_road, "Road access" if lang == 'en' else "Zufahrtsstraße"),
        ]

        for de_name, line_edit, display_name in optional_dxf_inputs:
            path = line_edit.text().strip()
            if path:
                try:
                    validate_file_exists(path, extension='.dxf')
                except ValidationError as e:
                    errors.append(f"{display_name}: {str(e)}")

        # Check workspace
        workspace = self.input_workspace.text().strip()
        if not workspace:
            if lang == 'en':
                errors.append("Please select workspace folder")
            else:
                errors.append("Bitte Workspace-Ordner auswählen")
        else:
            # Create workspace if it doesn't exist (this is okay)
            workspace_path = Path(workspace)
            if workspace_path.exists() and not workspace_path.is_dir():
                if lang == 'en':
                    errors.append(f"Workspace path exists but is not a directory: {workspace}")
                else:
                    errors.append(f"Workspace-Pfad existiert, ist aber kein Ordner: {workspace}")

        # Check FOK is reasonable
        fok = self.input_fok.value()
        if fok < 0 or fok > 9999:
            if lang == 'en':
                errors.append(f"Foundation elevation (FOK) {fok} m seems unrealistic")
            else:
                errors.append(f"FOK {fok} m ü.NN scheint unrealistisch")

        # Check search ranges are positive
        if self.input_search_below_fok.value() < 0:
            if lang == 'en':
                errors.append("Search range below FOK must be positive")
            else:
                errors.append("Suchbereich unter FOK muss positiv sein")
        if self.input_search_above_fok.value() < 0:
            if lang == 'en':
                errors.append("Search range above FOK must be positive")
            else:
                errors.append("Suchbereich über FOK muss positiv sein")

        # Check search range is reasonable
        total_range = self.input_search_below_fok.value() + self.input_search_above_fok.value()
        if total_range > 10.0:
            if lang == 'en':
                errors.append(f"Total search range {total_range:.1f} m is very large. Consider reducing it.")
            else:
                errors.append(f"Gesamter Suchbereich {total_range:.1f} m ist sehr groß. Erwägen Sie eine Reduzierung.")

        # Check boom slope is in range
        boom_slope = self.input_boom_slope.value()
        if boom_slope < 2.0 or boom_slope > 8.0:
            if lang == 'en':
                errors.append(f"Boom surface slope {boom_slope}% outside valid range [2%, 8%]")
            else:
                errors.append(f"Auslegerflächen-Neigung {boom_slope}% außerhalb zulässigem Bereich [2%, 8%]")

        # Check height step is reasonable
        height_step = self.input_height_step.value()
        if height_step < 0.01:
            if lang == 'en':
                errors.append(f"Height step {height_step} m is too small (minimum 0.01 m)")
            else:
                errors.append(f"Höhenschritt {height_step} m ist zu klein (minimum 0.01 m)")

        # Check slope angle is reasonable
        slope_angle = self.input_slope_angle.value()
        if slope_angle < 15.0 or slope_angle > 60.0:
            if lang == 'en':
                errors.append(f"Slope angle {slope_angle}° outside valid range [15°, 60°]")
            else:
                errors.append(f"Böschungswinkel {slope_angle}° außerhalb zulässigem Bereich [15°, 60°]")

        if errors:
            title = "Invalid Inputs" if lang == 'en' else "Ungültige Eingaben"
            error_message = "\n\n".join(errors)
            QMessageBox.warning(
                self,
                title,
                error_message
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

            # Road access parameters
            'dxf_road': self.input_dxf_road.text().strip() if self.input_dxf_road.text().strip() else None,
            'road_slope_percent': self.input_road_slope.value(),
            'road_gravel_enabled': self.input_road_gravel_enabled.isChecked(),
            'road_gravel_thickness': self.input_road_gravel_thickness.value(),

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
            'force_refresh': self.input_force_refresh.isChecked(),

            # Uncertainty analysis parameters
            'uncertainty_enabled': self.input_uncertainty_enabled.isChecked(),
            'mc_samples': self.input_mc_samples.value(),
            'terrain_type_index': self.input_terrain_type.currentIndex(),
            'foundation_depth_std': self.input_foundation_depth_std.value(),
            'slope_angle_std': self.input_slope_angle_std.value()
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
        """Called when processing finishes with bilingual messages."""
        self.progress_bar.setVisible(False)
        self.btn_start.setEnabled(True)

        lang = get_language()

        if success:
            title = "Completed" if lang == 'en' else "Fertig"
            default_msg = "Calculation completed successfully!" if lang == 'en' else "Berechnung erfolgreich abgeschlossen!"
            QMessageBox.information(
                self,
                title,
                message or default_msg
            )
            self.accept()
        else:
            title = "Error" if lang == 'en' else "Fehler"
            default_msg = "An error occurred during processing." if lang == 'en' else "Ein Fehler ist aufgetreten."

            # Format error message with better line breaks
            error_message = message or default_msg
            if '\n' in error_message:
                error_message = error_message.replace('\n', '\n\n')

            QMessageBox.critical(
                self,
                title,
                error_message
            )
