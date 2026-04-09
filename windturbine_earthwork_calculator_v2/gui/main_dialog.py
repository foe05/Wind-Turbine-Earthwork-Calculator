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
    QCheckBox, QMessageBox, QProgressBar, QTextEdit, QScrollArea, QComboBox
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QUrl
from qgis.PyQt.QtGui import QIcon, QDesktopServices

from ..utils.logging_utils import get_plugin_logger
from ..utils.validation import (
    ValidationError,
    validate_file_exists,
    validate_height_range,
    validate_crs
)
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
    5. Standortvergleich (Multi-Site Report) - Comparison report across multiple sites
    """

    # Signal emitted when user clicks "Start"
    processing_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        """Initialize dialog."""
        super().__init__(parent)
        self.logger = get_plugin_logger()

        self.setWindowTitle("Erdmassenberechnung Windenergieanlagen - Multi-Flächen")
        self.setMinimumSize(900, 700)

        # Store processed sites for multi-site report
        self.processed_sites = []  # List of SiteData objects
        self.site_checkboxes = {}  # Dict mapping site_id -> QCheckBox

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
        self.tab_stabilization = self._create_soil_stabilization_tab()
        self.tab_output = self._create_output_tab()
        self.tab_multisite = self._create_multisite_report_tab()

        self.tabs.addTab(self.tab_input, "📂 Eingabe")
        self.tabs.addTab(self.tab_optimization, "⚙️ Optimierung")
        self.tabs.addTab(self.tab_profiles, "📊 Geländeschnitte")
        self.tabs.addTab(self.tab_stabilization, "🏗️ Bodenstabilisierung")
        self.tabs.addTab(self.tab_output, "💾 Ausgabe")
        self.tabs.addTab(self.tab_multisite, "📈 Standortvergleich")

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

    def _create_soil_stabilization_tab(self):
        """Create soil stabilization tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Bodenkennwerte
        group_soil = QGroupBox("Bodenkennwerte")
        form_soil = QFormLayout()

        # Bodenart
        self.input_soil_type = QComboBox()
        self.input_soil_type.addItems([
            'Ton (weich)',
            'Ton (steif)',
            'Ton (halbfest)',
            'Schluff (weich)',
            'Schluff (mitteldicht)',
            'Lehm (steif)',
            'Lehm (halbfest)',
            'Sand (locker)',
            'Sand (mitteldicht)',
            'Sand (dicht)',
            'Kies (mitteldicht)',
            'Kies (dicht)',
            'Unbekannt - Standardwert verwenden'
        ])
        self.input_soil_type.setCurrentIndex(3)  # Default: Schluff (weich)
        self.input_soil_type.setToolTip("Bodenart für Bodenstabilisierungsberechnung")

        form_soil.addRow("Bodenart:", self.input_soil_type)

        # Ev2-Bestand
        self.input_ev2_bestand = QDoubleSpinBox()
        self.input_ev2_bestand.setRange(0, 200)
        self.input_ev2_bestand.setValue(45.0)
        self.input_ev2_bestand.setDecimals(1)
        self.input_ev2_bestand.setSuffix(" MN/m²")
        self.input_ev2_bestand.setToolTip(
            "Verformungsmodul des anstehenden Bodens (Plattendruckversuch DIN 18134)\n"
            "Typische Bereiche werden basierend auf gewählter Bodenart angezeigt"
        )

        form_soil.addRow("Ev2 Bestand:", self.input_ev2_bestand)

        # Info-Label für typische Ev2-Bereiche (wird dynamisch aktualisiert)
        self.label_ev2_range = QLabel("<i>Typisch für Schluff (weich): 20-35 MN/m²</i>")
        self.label_ev2_range.setWordWrap(True)
        self.label_ev2_range.setStyleSheet("QLabel { color: #666; font-size: 10pt; }")
        form_soil.addRow("", self.label_ev2_range)

        # Wassergehalt (optional)
        self.input_water_content = QDoubleSpinBox()
        self.input_water_content.setRange(0, 50)
        self.input_water_content.setValue(0)
        self.input_water_content.setDecimals(1)
        self.input_water_content.setSuffix(" %")
        self.input_water_content.setSpecialValueText("Unbekannt")
        self.input_water_content.setToolTip(
            "Aktueller Wassergehalt (optional, für genauere Kalkdosierung)"
        )

        form_soil.addRow("Wassergehalt:", self.input_water_content)

        # Optimaler Wassergehalt (optional)
        self.input_optimum_water = QDoubleSpinBox()
        self.input_optimum_water.setRange(0, 50)
        self.input_optimum_water.setValue(18.0)  # Default für Schluff
        self.input_optimum_water.setDecimals(1)
        self.input_optimum_water.setSuffix(" %")
        self.input_optimum_water.setSpecialValueText("Unbekannt")
        self.input_optimum_water.setToolTip(
            "Optimaler Wassergehalt nach Proctor (DIN 18127)\n"
            "Wird automatisch für gewählte Bodenart vorgeschlagen\n"
            "Kann manuell überschrieben werden"
        )

        form_soil.addRow("Optimum Wassergehalt:", self.input_optimum_water)

        group_soil.setLayout(form_soil)
        layout.addWidget(group_soil)

        # Connect signal to auto-fill optimum water content when soil type changes
        self.input_soil_type.currentTextChanged.connect(self._on_soil_type_changed)

        # Berechnungsoptionen
        group_options = QGroupBox("Berechnungsoptionen")
        form_options = QFormLayout()

        self.input_enable_stabilization = QCheckBox("Bodenstabilisierung berechnen")
        self.input_enable_stabilization.setChecked(True)
        self.input_enable_stabilization.setToolTip(
            "Aktiviert die Berechnung von Kalk- und Schottermengen"
        )

        form_options.addRow(self.input_enable_stabilization)

        # Info-Label
        info_label = QLabel(
            "<i><b>Hinweis:</b> Alle Werte sind Richtwerte für Vordimensionierung. "
            "Standortspezifische Eignungsprüfungen nach TP BF-StB Teil B 11.1 "
            "sind vor Bauausführung zwingend erforderlich!</i>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #666; margin-top: 10px; }")

        form_options.addRow("", info_label)

        group_options.setLayout(form_options)
        layout.addWidget(group_options)

        # BGR-Datenabfrage (experimentell)
        group_bgr = QGroupBox("BGR-Datenabfrage (experimentell)")
        form_bgr = QFormLayout()

        bgr_info = QLabel(
            "<i>Fragt Bodendaten von der Bundesanstalt für Geowissenschaften "
            "und Rohstoffe (BGR) ab. Benötigt Internet-Verbindung und "
            "Koordinaten der Kranstellfläche aus DXF-Datei.</i>"
        )
        bgr_info.setWordWrap(True)
        bgr_info.setStyleSheet("QLabel { color: #666; font-size: 10pt; }")

        self.btn_bgr_query = QPushButton("Bodendaten von BGR abrufen")
        self.btn_bgr_query.setEnabled(True)
        self.btn_bgr_query.setToolTip(
            "Fragt Bodenart von BGR BÜK200 WFS-Service ab\n"
            "Hinweis: Benötigt valide Koordinaten aus DXF-Datei"
        )
        self.btn_bgr_query.clicked.connect(self._on_bgr_query)

        # Status-Label für BGR-Abfrage
        self.label_bgr_status = QLabel("")
        self.label_bgr_status.setWordWrap(True)
        self.label_bgr_status.setStyleSheet("QLabel { color: #666; font-size: 10pt; }")

        form_bgr.addRow(bgr_info)
        form_bgr.addRow("", self.btn_bgr_query)
        form_bgr.addRow("Status:", self.label_bgr_status)

        group_bgr.setLayout(form_bgr)
        layout.addWidget(group_bgr)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

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

    def _create_multisite_report_tab(self):
        """Create multi-site comparison report tab."""
        # Create scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        widget = QWidget()
        layout = QVBoxLayout()

        # Info section
        info_group = QGroupBox("Standortvergleich")
        info_layout = QVBoxLayout()

        info_label = QLabel(
            "<b>Multi-Standort-Vergleichsbericht</b><br><br>"
            "<i>Generieren Sie umfassende Vergleichsberichte für mehrere Windenergieanlagen-Standorte.</i><br><br>"
            "Der Bericht enthält:<br>"
            "• Gesamte Erdmassen und Kosten für alle Standorte<br>"
            "• Ranking der Standorte nach Komplexität<br>"
            "• Detaillierte Aufschlüsselung pro Standort<br>"
            "• Export als HTML, PDF oder Excel"
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Site Selection Group
        group_sites = QGroupBox("Standortauswahl")
        sites_layout = QVBoxLayout()

        sites_info = QLabel(
            "<i>Wählen Sie die Standorte aus, die in den Vergleichsbericht aufgenommen werden sollen.</i>"
        )
        sites_info.setWordWrap(True)
        sites_info.setStyleSheet("color: gray; font-size: 10px;")
        sites_layout.addWidget(sites_info)

        # Create scrollable container for site checkboxes
        sites_scroll = QScrollArea()
        sites_scroll.setWidgetResizable(True)
        sites_scroll.setMaximumHeight(200)
        sites_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sites_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Container widget for checkboxes
        self.sites_checkbox_container = QWidget()
        self.sites_checkbox_layout = QVBoxLayout()
        self.sites_checkbox_layout.setContentsMargins(5, 5, 5, 5)

        # Empty state label (shown when no sites processed)
        self.label_no_sites = QLabel("<i>Noch keine Standorte verarbeitet. Führen Sie zunächst Berechnungen durch.</i>")
        self.label_no_sites.setWordWrap(True)
        self.label_no_sites.setStyleSheet("color: gray; font-size: 10px; padding: 10px;")
        self.sites_checkbox_layout.addWidget(self.label_no_sites)

        self.sites_checkbox_layout.addStretch()
        self.sites_checkbox_container.setLayout(self.sites_checkbox_layout)
        sites_scroll.setWidget(self.sites_checkbox_container)
        sites_layout.addWidget(sites_scroll)

        # Select All / Deselect All buttons
        sites_buttons_layout = QHBoxLayout()
        self.btn_select_all_sites = QPushButton("Alle auswählen")
        self.btn_select_all_sites.clicked.connect(self._select_all_sites)
        self.btn_select_all_sites.setEnabled(False)

        self.btn_deselect_all_sites = QPushButton("Alle abwählen")
        self.btn_deselect_all_sites.clicked.connect(self._deselect_all_sites)
        self.btn_deselect_all_sites.setEnabled(False)

        sites_buttons_layout.addWidget(self.btn_select_all_sites)
        sites_buttons_layout.addWidget(self.btn_deselect_all_sites)
        sites_buttons_layout.addStretch()
        sites_layout.addLayout(sites_buttons_layout)

        group_sites.setLayout(sites_layout)
        layout.addWidget(group_sites)

        # Cost Parameters Group
        group_costs = QGroupBox("Kostenparameter")
        form_costs = QFormLayout()

        # Cost per m³ for cut
        self.input_cost_cut = QDoubleSpinBox()
        self.input_cost_cut.setRange(0, 100)
        self.input_cost_cut.setValue(8.0)
        self.input_cost_cut.setDecimals(2)
        self.input_cost_cut.setSuffix(" €/m³")
        self.input_cost_cut.setToolTip("Kosten pro Kubikmeter Abtrag")
        form_costs.addRow("Abtrag-Kosten:", self.input_cost_cut)

        # Cost per m³ for fill
        self.input_cost_fill = QDoubleSpinBox()
        self.input_cost_fill.setRange(0, 100)
        self.input_cost_fill.setValue(12.0)
        self.input_cost_fill.setDecimals(2)
        self.input_cost_fill.setSuffix(" €/m³")
        self.input_cost_fill.setToolTip("Kosten pro Kubikmeter Auftrag")
        form_costs.addRow("Auftrag-Kosten:", self.input_cost_fill)

        # Cost per m³ for gravel
        self.input_cost_gravel = QDoubleSpinBox()
        self.input_cost_gravel.setRange(0, 200)
        self.input_cost_gravel.setValue(45.0)
        self.input_cost_gravel.setDecimals(2)
        self.input_cost_gravel.setSuffix(" €/m³")
        self.input_cost_gravel.setToolTip("Kosten pro Kubikmeter Schotter")
        form_costs.addRow("Schotter-Kosten:", self.input_cost_gravel)

        group_costs.setLayout(form_costs)
        layout.addWidget(group_costs)

        # Export Options Group
        group_export = QGroupBox("Export-Optionen")
        form_export = QFormLayout()

        export_info = QLabel(
            "<i>Wählen Sie das gewünschte Export-Format für den Vergleichsbericht.</i>"
        )
        export_info.setWordWrap(True)
        export_info.setStyleSheet("color: gray; font-size: 10px;")
        form_export.addRow("", export_info)

        # Format selection
        from qgis.PyQt.QtWidgets import QComboBox
        self.input_multisite_report_format = QComboBox()
        self.input_multisite_report_format.addItems([
            "HTML (Webseite)",
            "PDF (Dokument)",
            "Excel (Tabelle)"
        ])
        self.input_multisite_report_format.setCurrentIndex(0)  # Default to HTML
        self.input_multisite_report_format.setToolTip(
            "Wählen Sie das Format für den Standortvergleichsbericht:\n"
            "- HTML: Interaktiver Bericht im Browser\n"
            "- PDF: Druckbares Dokument\n"
            "- Excel: Tabellenkalkulationsdatei mit mehreren Arbeitsblättern"
        )
        form_export.addRow("Format:", self.input_multisite_report_format)

        # Output path
        self.input_multisite_report_output = QLineEdit()
        self.input_multisite_report_output.setPlaceholderText("Pfad wird automatisch generiert...")
        self.input_multisite_report_output.setReadOnly(True)
        self.input_multisite_report_output.setToolTip("Ausgabepfad für den Bericht (wird automatisch basierend auf Workspace erstellt)")

        btn_browse_multisite_output = QPushButton("Durchsuchen...")
        btn_browse_multisite_output.clicked.connect(self._browse_multisite_report_output)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.input_multisite_report_output)
        output_layout.addWidget(btn_browse_multisite_output)
        form_export.addRow("Ausgabepfad:", output_layout)

        # Generate button
        self.btn_generate_multisite_report = QPushButton("Bericht generieren")
        self.btn_generate_multisite_report.setToolTip(
            "Generiert einen Vergleichsbericht für alle ausgewählten Standorte"
        )
        self.btn_generate_multisite_report.setEnabled(False)  # Disabled until sites are selected
        # Signal connection will be added in subtask-4-4

        generate_layout = QHBoxLayout()
        generate_layout.addStretch()
        generate_layout.addWidget(self.btn_generate_multisite_report)

        form_export.addRow("", generate_layout)

        group_export.setLayout(form_export)
        layout.addWidget(group_export)

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
        self.btn_generate_multisite_report.clicked.connect(self._on_generate_multisite_report)

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

    def _browse_multisite_report_output(self):
        """Browse for multi-site report output file."""
        # Get current format selection to determine file extension
        format_index = self.input_multisite_report_format.currentIndex()
        file_filter = ""
        default_ext = ""

        if format_index == 0:  # HTML
            file_filter = "HTML-Dateien (*.html)"
            default_ext = ".html"
        elif format_index == 1:  # PDF
            file_filter = "PDF-Dateien (*.pdf)"
            default_ext = ".pdf"
        elif format_index == 2:  # Excel
            file_filter = "Excel-Dateien (*.xlsx)"
            default_ext = ".xlsx"

        # Get default directory from workspace if set
        default_dir = self.input_workspace.text().strip()
        if default_dir:
            default_dir = os.path.join(default_dir, f"standortvergleich{default_ext}")
        else:
            default_dir = f"standortvergleich{default_ext}"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Ausgabepfad für Standortvergleichsbericht",
            default_dir,
            file_filter
        )
        if filename:
            self.input_multisite_report_output.setText(filename)

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

    def _run_preflight_validation(self) -> bool:
        """
        Run comprehensive pre-flight validation before processing starts.

        This validates all inputs comprehensively:
        - DXF files (existence, readability, CRS consistency)
        - Height parameters (range validation)
        - Workspace
        - Network connectivity for DEM download

        Returns:
            bool: True if all validations pass, False otherwise
        """
        lang = get_language()

        # === PHASE 1: Basic input validation ===
        if not self._validate_inputs():
            return False

        # === PHASE 2: DXF CRS consistency check ===
        try:
            self.logger.info("=" * 60)
            self.logger.info("🔍 PRE-FLIGHT VALIDATION STARTED")
            self.logger.info("=" * 60)

            self.logger.info("Validating DXF coordinate reference systems...")

            dxf_files = []
            dxf_names = []

            # Required files
            if self.input_dxf_crane.text().strip():
                dxf_files.append(self.input_dxf_crane.text().strip())
                dxf_names.append("Kranstellfläche" if lang == 'de' else "Crane pad")

            if self.input_dxf_foundation.text().strip():
                dxf_files.append(self.input_dxf_foundation.text().strip())
                dxf_names.append("Fundamentfläche" if lang == 'de' else "Foundation")

            # Optional files
            if self.input_dxf_boom.text().strip():
                dxf_files.append(self.input_dxf_boom.text().strip())
                dxf_names.append("Auslegerfläche" if lang == 'de' else "Boom surface")

            if self.input_dxf_rotor.text().strip():
                dxf_files.append(self.input_dxf_rotor.text().strip())
                dxf_names.append("Blattlagerfläche" if lang == 'de' else "Blade storage")

            if self.input_dxf_holms.text().strip():
                dxf_files.append(self.input_dxf_holms.text().strip())
                dxf_names.append("Holme" if lang == 'de' else "Holms")

            if self.input_dxf_road.text().strip():
                dxf_files.append(self.input_dxf_road.text().strip())
                dxf_names.append("Zufahrtsstraße" if lang == 'de' else "Road access")

            # Check CRS consistency across all DXF files
            detected_crs_list = []
            for i, dxf_path in enumerate(dxf_files):
                try:
                    importer = DXFImporter(dxf_path, tolerance=self.input_dxf_tolerance.value())
                    crs_info = importer.detect_coordinate_system()

                    if crs_info and crs_info.get('suggested_epsg'):
                        detected_epsg = crs_info['suggested_epsg']
                        confidence = crs_info.get('confidence', 'unknown')
                        detected_crs_list.append((dxf_names[i], detected_epsg, confidence))
                        self.logger.info(
                            f"  ✓ {dxf_names[i]}: EPSG:{detected_epsg} (confidence: {confidence})"
                        )
                    else:
                        self.logger.warning(f"  ⚠ {dxf_names[i]}: Could not detect CRS")

                except Exception as e:
                    error_msg = (
                        f"Fehler beim Lesen von {dxf_names[i]}: {str(e)}"
                        if lang == 'de' else
                        f"Error reading {dxf_names[i]}: {str(e)}"
                    )
                    self._show_validation_error(
                        "DXF-Fehler" if lang == 'de' else "DXF Error",
                        error_msg
                    )
                    return False

            # Check if all detected CRS are consistent
            if len(detected_crs_list) > 1:
                first_epsg = detected_crs_list[0][1]
                inconsistent = [
                    (name, epsg, conf) for name, epsg, conf in detected_crs_list
                    if epsg != first_epsg
                ]

                if inconsistent:
                    error_parts = []
                    if lang == 'de':
                        error_parts.append(
                            "⚠️ Warnung: Inkonsistente Koordinatensysteme erkannt!\n\n"
                            "Die DXF-Dateien verwenden unterschiedliche CRS:"
                        )
                    else:
                        error_parts.append(
                            "⚠️ Warning: Inconsistent coordinate systems detected!\n\n"
                            "The DXF files use different CRS:"
                        )

                    for name, epsg, conf in detected_crs_list:
                        error_parts.append(f"  • {name}: EPSG:{epsg}")

                    if lang == 'de':
                        error_parts.append(
                            "\nLösung: Transformieren Sie alle DXF-Dateien in dasselbe "
                            "Koordinatensystem (z.B. EPSG:25832 für UTM 32N)."
                        )
                    else:
                        error_parts.append(
                            "\nFix: Transform all DXF files to the same coordinate system "
                            "(e.g., EPSG:25832 for UTM 32N)."
                        )

                    self._show_validation_error(
                        "CRS-Inkonsistenz" if lang == 'de' else "CRS Inconsistency",
                        "\n".join(error_parts)
                    )
                    return False

                self.logger.info(f"✓ All DXF files use consistent CRS: EPSG:{first_epsg}")

        except Exception as e:
            self.logger.error(f"Pre-flight validation error: {str(e)}", exc_info=True)
            self._show_validation_error(
                "Validierungsfehler" if lang == 'de' else "Validation Error",
                str(e)
            )
            return False

        # === PHASE 3: Height parameter validation ===
        try:
            self.logger.info("Validating height parameters...")

            fok = self.input_fok.value()
            search_below = self.input_search_below_fok.value()
            search_above = self.input_search_above_fok.value()
            height_step = self.input_height_step.value()

            min_height = fok - search_below
            max_height = fok + search_above

            # Use the validation utility
            validate_height_range(min_height, max_height, height_step)

            num_scenarios = int((max_height - min_height) / height_step) + 1
            self.logger.info(
                f"✓ Height parameters valid: {min_height:.2f} - {max_height:.2f} m "
                f"(step: {height_step:.2f} m, {num_scenarios} scenarios)"
            )

        except ValidationError as e:
            self._show_validation_error(
                "Ungültige Höhenparameter" if lang == 'de' else "Invalid Height Parameters",
                str(e)
            )
            return False

        # === PHASE 4: Network connectivity check (for DEM download) ===
        try:
            import socket

            self.logger.info("Checking network connectivity for DEM download...")

            # Check if we can resolve the DEM API hostname
            try:
                socket.gethostbyname("api.hoehendaten.de")
                self.logger.info("✓ Network connectivity OK")
            except socket.gaierror:
                if lang == 'de':
                    warning_msg = (
                        "⚠️ Warnung: Keine Verbindung zur DEM-API möglich!\n\n"
                        "Die DEM-Daten können nicht heruntergeladen werden. "
                        "Prüfen Sie Ihre Internetverbindung.\n\n"
                        "Möchten Sie trotzdem fortfahren?"
                    )
                    title = "Netzwerkverbindung"
                else:
                    warning_msg = (
                        "⚠️ Warning: Cannot connect to DEM API!\n\n"
                        "DEM data cannot be downloaded. "
                        "Check your internet connection.\n\n"
                        "Do you want to continue anyway?"
                    )
                    title = "Network Connection"

                reply = QMessageBox.question(
                    self,
                    title,
                    warning_msg,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.No:
                    self.logger.info("User cancelled due to network issue")
                    return False

                self.logger.warning("User chose to continue despite network issue")

        except ImportError:
            # socket module not available (unlikely but handle gracefully)
            self.logger.warning("Cannot check network connectivity (socket module unavailable)")

        # === VALIDATION COMPLETE ===
        self.logger.info("=" * 60)
        self.logger.info("✅ PRE-FLIGHT VALIDATION PASSED")
        self.logger.info("=" * 60)

        return True

    def _on_bgr_query(self):
        """
        Führt BGR-Bodendaten-Abfrage aus.

        Benötigt DXF-Datei mit Koordinaten der Kranstellfläche.
        """
        from qgis.core import QgsCoordinateReferenceSystem

        # Prüfe ob DXF-Datei der Kranstellfläche angegeben
        dxf_path = self.input_dxf_crane.text().strip()

        if not dxf_path:
            QMessageBox.warning(
                self,
                "Keine DXF-Datei",
                "Bitte wählen Sie zuerst eine DXF-Datei der Kranstellfläche im Tab 'Eingabe' aus.\n"
                "Die Koordinaten der Kranstellfläche werden aus der DXF-Datei benötigt."
            )
            return

        if not os.path.exists(dxf_path):
            QMessageBox.warning(
                self,
                "DXF-Datei nicht gefunden",
                f"Die DXF-Datei wurde nicht gefunden:\n{dxf_path}"
            )
            return

        # Status: Lade...
        self.label_bgr_status.setText("<i>Lade Bodendaten von BGR...</i>")
        self.label_bgr_status.setStyleSheet("QLabel { color: #0066cc; }")
        self.btn_bgr_query.setEnabled(False)

        try:
            # Importiere DXF und hole Koordinaten
            from ..core.dxf_importer import DXFImporter
            from ..core.soil_stabilization_calculator import SoilStabilizationCalculator
            from ..utils.geometry_utils import get_centroid

            self.logger.info(f"Importiere DXF für BGR-Abfrage: {dxf_path}")

            importer = DXFImporter(dxf_path, tolerance=self.input_dxf_tolerance.value())
            polygon, metadata = importer.import_as_polygon()

            if not polygon or polygon.isEmpty():
                raise Exception("Keine Geometrie in DXF-Datei gefunden")

            # Hole Zentroid als Abfragepunkt
            centroid = get_centroid(polygon)

            # CRS aus DXF oder Default (EPSG:25832 - UTM Zone 32N für Deutschland)
            crs = importer.get_crs() or QgsCoordinateReferenceSystem("EPSG:25832")

            self.logger.info(
                f"Abfragepunkt: {centroid.x():.2f}, {centroid.y():.2f} ({crs.authid()})"
            )

            # BGR-Abfrage
            calc = SoilStabilizationCalculator()
            result = calc.query_soil_data_from_bgr(centroid, crs)

            if result.get('available'):
                # Erfolg!
                soil_type = result.get('soil_type')
                soil_code = result.get('soil_code', '')
                description = result.get('description', '')

                self.label_bgr_status.setText(
                    f"<i>✓ Gefunden: <b>{soil_type}</b> (BGR-Code: {soil_code})<br>"
                    f"{description[:100]}...</i>"
                )
                self.label_bgr_status.setStyleSheet("QLabel { color: #006600; }")

                # Aktualisiere Bodenart-Dropdown
                # Finde passenden Eintrag in Combo Box
                for i in range(self.input_soil_type.count()):
                    item_text = self.input_soil_type.itemText(i)
                    if soil_type and soil_type in item_text:
                        self.input_soil_type.setCurrentIndex(i)
                        break

                QMessageBox.information(
                    self,
                    "BGR-Daten erfolgreich",
                    f"Bodenart gefunden: {soil_type}\n\n"
                    f"BGR-Code: {soil_code}\n"
                    f"Quelle: {result.get('source')}\n\n"
                    f"Beschreibung:\n{description}"
                )

            else:
                # Fehler
                error = result.get('error', 'Unbekannter Fehler')
                self.label_bgr_status.setText(
                    f"<i>✗ Fehler: {error}</i>"
                )
                self.label_bgr_status.setStyleSheet("QLabel { color: #cc0000; }")

                QMessageBox.warning(
                    self,
                    "BGR-Abfrage fehlgeschlagen",
                    f"Bodendaten konnten nicht abgerufen werden.\n\n"
                    f"Fehler: {error}\n\n"
                    f"Mögliche Ursachen:\n"
                    f"- Keine Internet-Verbindung\n"
                    f"- Koordinaten außerhalb des BGR-Datenbereichs\n"
                    f"- BGR-Service vorübergehend nicht verfügbar"
                )

        except Exception as e:
            self.logger.error(f"BGR-Abfrage fehlgeschlagen: {e}", exc_info=True)
            self.label_bgr_status.setText(
                f"<i>✗ Fehler: {str(e)}</i>"
            )
            self.label_bgr_status.setStyleSheet("QLabel { color: #cc0000; }")

            QMessageBox.critical(
                self,
                "Fehler",
                f"BGR-Abfrage fehlgeschlagen:\n\n{str(e)}"
            )

        finally:
            self.btn_bgr_query.setEnabled(True)

    def _on_soil_type_changed(self, soil_type_text):
        """
        Auto-fill optimum water content and update Ev2 range hint when soil type changes.

        Args:
            soil_type_text: Text from combo box (e.g. "Ton (weich)")
        """
        # Import the constants
        from ..core.soil_stabilization_calculator import (
            OPTIMUM_WATER_CONTENT,
            SOIL_EV2_RANGES
        )

        # Extract base soil type and consistency
        if soil_type_text == 'Unbekannt - Standardwert verwenden':
            base_type = 'Schluff'  # Default
            consistency = 'weich'
            full_key = 'Schluff_weich'
        else:
            parts = soil_type_text.replace('(', '').replace(')', '').split()
            base_type = parts[0]  # "Ton", "Schluff", etc.
            consistency = parts[1] if len(parts) > 1 else 'weich'
            full_key = f"{base_type}_{consistency}"

        # Update optimum water content
        if base_type in OPTIMUM_WATER_CONTENT:
            optimum = OPTIMUM_WATER_CONTENT[base_type]

            # Auto-update if current value is a typical value
            current_value = self.input_optimum_water.value()
            typical_values = list(OPTIMUM_WATER_CONTENT.values()) + [0]

            if current_value in typical_values or current_value == 0:
                self.input_optimum_water.setValue(optimum)
                self.logger.info(
                    f"Auto-updated optimum water content: {optimum}% for {base_type}"
                )

        # Update Ev2 range hint
        if full_key in SOIL_EV2_RANGES:
            ev2_min, ev2_max = SOIL_EV2_RANGES[full_key]
            self.label_ev2_range.setText(
                f"<i>Typisch für {soil_type_text}: {ev2_min}-{ev2_max} MN/m²</i>"
            )
        else:
            # Fallback: try to find similar entry
            matching_keys = [k for k in SOIL_EV2_RANGES.keys() if base_type in k]
            if matching_keys:
                # Take first match
                ev2_min, ev2_max = SOIL_EV2_RANGES[matching_keys[0]]
                self.label_ev2_range.setText(
                    f"<i>Typisch für {base_type}: ca. {ev2_min}-{ev2_max} MN/m²</i>"
                )
            else:
                self.label_ev2_range.setText(
                    f"<i>Typische Werte für {base_type} nicht verfügbar</i>"
                )

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
        """Handle start button click with comprehensive pre-flight validation."""
        # Run comprehensive pre-flight validation BEFORE processing starts
        # This validates: DXF files, CRS consistency, height parameters, network connectivity
        if not self._run_preflight_validation():
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
            'slope_angle_std': self.input_slope_angle_std.value(),

            # Bodenstabilisierung
            'enable_stabilization': self.input_enable_stabilization.isChecked(),
            'soil_type': self.input_soil_type.currentText().split(' (')[0]
                         if self.input_soil_type.currentText() != 'Unbekannt - Standardwert verwenden'
                         else 'Schluff',
            'ev2_bestand': self.input_ev2_bestand.value(),
            'water_content': self.input_water_content.value(),
            'optimum_water': self.input_optimum_water.value()
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

    # ========== Multi-Site Report Methods ==========

    def add_processed_site(self, site_data):
        """
        Add a processed site to the multi-site report selection list.

        Args:
            site_data: SiteData object containing site information

        Note:
            If a site with the same site_id already exists, it will be updated.
        """
        from ..core.site_data import SiteData

        # Validate input
        if not isinstance(site_data, SiteData):
            self.logger.warning(f"Invalid site_data type: {type(site_data)}")
            return

        # Check if site already exists (update if so)
        existing_site = None
        for i, site in enumerate(self.processed_sites):
            if site.site_id == site_data.site_id:
                existing_site = i
                break

        if existing_site is not None:
            # Update existing site
            self.processed_sites[existing_site] = site_data
            # Update checkbox label if it exists
            if site_data.site_id in self.site_checkboxes:
                checkbox = self.site_checkboxes[site_data.site_id]
                checkbox.setText(self._format_site_checkbox_label(site_data))
        else:
            # Add new site
            self.processed_sites.append(site_data)
            self._add_site_checkbox(site_data)

        # Update UI state
        self._update_site_selection_ui()

        self.logger.info(f"Added/updated site '{site_data.site_name}' to multi-site report list")

    def _add_site_checkbox(self, site_data):
        """
        Add a checkbox for a site to the UI.

        Args:
            site_data: SiteData object
        """
        # Create checkbox
        checkbox = QCheckBox(self._format_site_checkbox_label(site_data))
        checkbox.setChecked(True)  # Default to checked
        checkbox.setToolTip(
            f"Standort: {site_data.site_name}\n"
            f"Position: {site_data.location.x():.2f}, {site_data.location.y():.2f}\n"
            f"Erdmassen: {site_data.total_volume_moved:.1f} m³\n"
            f"Kosten: {site_data.total_cost:.2f} €"
        )

        # Store reference
        self.site_checkboxes[site_data.site_id] = checkbox

        # Add to layout (before the stretch)
        insert_index = self.sites_checkbox_layout.count() - 1  # Before stretch
        self.sites_checkbox_layout.insertWidget(insert_index, checkbox)

    def _format_site_checkbox_label(self, site_data):
        """
        Format the label for a site checkbox.

        Args:
            site_data: SiteData object

        Returns:
            Formatted label string
        """
        return (
            f"{site_data.site_name} - "
            f"{site_data.total_volume_moved:.1f} m³, "
            f"{site_data.total_cost:.2f} €"
        )

    def _update_site_selection_ui(self):
        """Update the site selection UI based on current state."""
        has_sites = len(self.processed_sites) > 0

        # Show/hide empty state label
        self.label_no_sites.setVisible(not has_sites)

        # Enable/disable select/deselect buttons
        self.btn_select_all_sites.setEnabled(has_sites)
        self.btn_deselect_all_sites.setEnabled(has_sites)

        # Enable/disable generate button
        self.btn_generate_multisite_report.setEnabled(has_sites)

    def _select_all_sites(self):
        """Select all site checkboxes."""
        for checkbox in self.site_checkboxes.values():
            checkbox.setChecked(True)

    def _deselect_all_sites(self):
        """Deselect all site checkboxes."""
        for checkbox in self.site_checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_sites(self):
        """
        Get list of selected sites for multi-site report.

        Returns:
            List of SiteData objects for checked sites
        """
        selected = []
        for site in self.processed_sites:
            if site.site_id in self.site_checkboxes:
                checkbox = self.site_checkboxes[site.site_id]
                if checkbox.isChecked():
                    selected.append(site)
        return selected

    def clear_processed_sites(self):
        """Clear all processed sites from the multi-site report list."""
        # Remove all checkboxes from layout
        for site_id, checkbox in self.site_checkboxes.items():
            self.sites_checkbox_layout.removeWidget(checkbox)
            checkbox.deleteLater()

        # Clear data structures
        self.site_checkboxes.clear()
        self.processed_sites.clear()

        # Update UI state
        self._update_site_selection_ui()

        self.logger.info("Cleared all processed sites from multi-site report list")

    def get_multisite_report_format(self):
        """
        Get the selected export format for the multi-site report.

        Returns:
            str: Format string - 'html', 'pdf', or 'excel'
        """
        format_index = self.input_multisite_report_format.currentIndex()
        format_map = {
            0: 'html',
            1: 'pdf',
            2: 'excel'
        }
        return format_map.get(format_index, 'html')

    def get_multisite_report_output_path(self):
        """
        Get the output path for the multi-site report.

        Returns:
            str: Output file path, or None if not set
        """
        path = self.input_multisite_report_output.text().strip()
        return path if path else None

    def get_multisite_cost_parameters(self):
        """
        Get the cost parameters for multi-site report.

        Returns:
            dict: Cost parameters (cut, fill, gravel costs per m³)
        """
        return {
            'cost_cut': self.input_cost_cut.value(),
            'cost_fill': self.input_cost_fill.value(),
            'cost_gravel': self.input_cost_gravel.value()
        }

    def _on_generate_multisite_report(self):
        """Handle generate multi-site report button click."""
        try:
            # Validate selected sites
            selected_sites = self.get_selected_sites()
            if not selected_sites:
                QMessageBox.warning(
                    self,
                    "Keine Standorte ausgewählt",
                    "Bitte wählen Sie mindestens einen Standort aus der Liste aus."
                )
                return

            # Get report parameters
            report_format = self.get_multisite_report_format()
            cost_params = self.get_multisite_cost_parameters()
            output_path = self.get_multisite_report_output_path()

            # Determine output path with default if not set
            if not output_path:
                workspace = self.input_workspace.text().strip()
                if not workspace:
                    QMessageBox.warning(
                        self,
                        "Kein Workspace",
                        "Bitte wählen Sie zuerst einen Workspace-Ordner auf der 'Ausgabe'-Tab aus."
                    )
                    return

                # Generate default output path based on format
                format_extensions = {
                    'html': '.html',
                    'pdf': '.pdf',
                    'excel': '.xlsx'
                }
                ext = format_extensions.get(report_format, '.html')
                output_path = os.path.join(workspace, f"standortvergleich{ext}")
                self.input_multisite_report_output.setText(output_path)

            # Prepare site results for report generator
            site_results = []
            for site_data in selected_sites:
                site_result = {
                    'site_id': site_data.site_id,
                    'site_name': site_data.site_name,
                    'results': {
                        'total_cut': site_data.total_cut,
                        'total_fill': site_data.total_fill,
                        'net_volume': site_data.net_volume,
                        'gravel_fill_external': site_data.gravel_volume,
                        'crane_height': site_data.crane_height,
                        'platform_height': site_data.crane_height,
                        'terrain_min': site_data.terrain_min,
                        'terrain_max': site_data.terrain_max,
                        'terrain_mean': site_data.terrain_mean,
                        'total_platform_area': site_data.platform_area,
                        'platform_area': site_data.platform_area,
                        'total_area': site_data.total_area,
                        'slope_width': 0.0,  # Will be calculated if needed
                    },
                    'coordinates': (site_data.location.x(), site_data.location.y()),
                    'config': {}
                }
                site_results.append(site_result)

            # Create cost configuration for report generator
            cost_config = {
                'cut_cost_per_m3': cost_params['cost_cut'],
                'fill_cost_per_m3': cost_params['cost_fill'],
                'gravel_cost_per_m3': cost_params['cost_gravel'],
                'transport_cost_per_m3_km': 0.5  # Default transport cost
            }

            # Import report generator
            from ..core.multi_site_report_generator import MultiSiteReportGenerator

            # Create report generator
            self.logger.info(f"Generating multi-site report for {len(selected_sites)} sites...")
            generator = MultiSiteReportGenerator(site_results, cost_config)

            # Generate report based on format
            if report_format == 'html':
                generator.generate_html(output_path, project_name="Windpark-Projekt")
                self.logger.info(f"HTML report generated: {output_path}")

            elif report_format == 'pdf':
                # Generate HTML first, then convert to PDF
                html_path = output_path.replace('.pdf', '.html')
                generator.generate_html(html_path, project_name="Windpark-Projekt")
                generator.generate_pdf(html_path, output_path)
                self.logger.info(f"PDF report generated: {output_path}")

            elif report_format == 'excel':
                generator.generate_excel(output_path, project_name="Windpark-Projekt")
                self.logger.info(f"Excel report generated: {output_path}")

            # Show success message
            QMessageBox.information(
                self,
                "Bericht erfolgreich erstellt",
                f"Multi-Standort-Vergleichsbericht wurde erfolgreich erstellt:\n{output_path}"
            )

            # Open the generated file
            self._open_file(output_path)

        except Exception as e:
            self.logger.error(f"Error generating multi-site report: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Fehler beim Erstellen des Berichts",
                f"Ein Fehler ist beim Erstellen des Berichts aufgetreten:\n\n{str(e)}"
            )

    def _open_file(self, file_path: str):
        """
        Open a file with the system's default application.

        Args:
            file_path (str): Path to the file to open
        """
        try:
            file_url = QUrl.fromLocalFile(file_path)
            if not QDesktopServices.openUrl(file_url):
                self.logger.warning(f"Could not open file with default application: {file_path}")
                QMessageBox.warning(
                    self,
                    "Datei konnte nicht geöffnet werden",
                    f"Die Datei wurde erfolgreich erstellt, konnte aber nicht automatisch geöffnet werden:\n{file_path}"
                )
        except Exception as e:
            self.logger.warning(f"Error opening file: {e}")
            # Don't show error - file was created successfully
