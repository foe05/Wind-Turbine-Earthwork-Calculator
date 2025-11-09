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
    QCheckBox, QMessageBox, QProgressBar, QTextEdit, QComboBox
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
        self.tab_stabilization = self._create_soil_stabilization_tab()
        self.tab_output = self._create_output_tab()

        self.tabs.addTab(self.tab_input, "📂 Eingabe")
        self.tabs.addTab(self.tab_optimization, "⚙️ Optimierung")
        self.tabs.addTab(self.tab_profiles, "📊 Geländeschnitte")
        self.tabs.addTab(self.tab_stabilization, "🏗️ Bodenstabilisierung")
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
        
        # Profile Settings
        group_profiles = QGroupBox("Geländeschnitt-Einstellungen")
        form_profiles = QFormLayout()
        
        self.input_profile_spacing = QDoubleSpinBox()
        self.input_profile_spacing.setRange(1.0, 50.0)
        self.input_profile_spacing.setValue(10.0)
        self.input_profile_spacing.setDecimals(1)
        self.input_profile_spacing.setSuffix(" m")
        self.input_profile_spacing.setToolTip("Abstand zwischen Geländeschnitten")
        
        self.input_profile_overhang = QDoubleSpinBox()
        self.input_profile_overhang.setRange(0.0, 50.0)
        self.input_profile_overhang.setValue(10.0)
        self.input_profile_overhang.setDecimals(1)
        self.input_profile_overhang.setSuffix(" %")
        self.input_profile_overhang.setToolTip("Überhang über Plattform-Rand hinaus")
        
        self.input_vertical_exaggeration = QDoubleSpinBox()
        self.input_vertical_exaggeration.setRange(1.0, 10.0)
        self.input_vertical_exaggeration.setValue(2.0)
        self.input_vertical_exaggeration.setDecimals(1)
        self.input_vertical_exaggeration.setSuffix(" x")
        self.input_vertical_exaggeration.setToolTip("Vertikale Überhöhung in Grafiken")
        
        form_profiles.addRow("Schnitt-Abstand:", self.input_profile_spacing)
        form_profiles.addRow("Überhang:", self.input_profile_overhang)
        form_profiles.addRow("Vert. Überhöhung:", self.input_vertical_exaggeration)
        
        group_profiles.setLayout(form_profiles)
        layout.addWidget(group_profiles)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget

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

        # BGR-Datenabfrage (experimentell) - Platzhalter
        group_bgr = QGroupBox("BGR-Datenabfrage (experimentell)")
        form_bgr = QFormLayout()

        bgr_info = QLabel(
            "<i>BGR-WFS-Abfrage für Bodendaten ist aktuell nicht implementiert. "
            "Diese Funktion wird in einer zukünftigen Version verfügbar sein.</i>"
        )
        bgr_info.setWordWrap(True)
        bgr_info.setStyleSheet("QLabel { color: #999; }")

        self.btn_bgr_query = QPushButton("Bodendaten von BGR abrufen")
        self.btn_bgr_query.setEnabled(False)  # Deaktiviert, da nicht implementiert
        self.btn_bgr_query.setToolTip("Diese Funktion ist noch nicht verfügbar")

        form_bgr.addRow(bgr_info)
        form_bgr.addRow("", self.btn_bgr_query)

        group_bgr.setLayout(form_bgr)
        layout.addWidget(group_bgr)

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
        
        # Helper function to parse soil type from combo box
        def parse_soil_type(combo_text):
            """Extract base soil type from combo box text."""
            # "Ton (weich)" -> "Ton"
            if combo_text == 'Unbekannt - Standardwert verwenden':
                return 'Schluff'  # Default
            return combo_text.split(' (')[0]

        # Collect parameters
        params = {
            'dxf_file': self.input_dxf.text().strip(),
            'dxf_tolerance': self.input_dxf_tolerance.value(),
            'min_height': self.input_min_height.value(),
            'max_height': self.input_max_height.value(),
            'height_step': self.input_height_step.value(),
            'slope_angle': self.input_slope_angle.value(),
            'profile_spacing': self.input_profile_spacing.value(),
            'profile_overhang': self.input_profile_overhang.value(),
            'vertical_exaggeration': self.input_vertical_exaggeration.value(),
            'workspace': self.input_workspace.text().strip(),
            'force_refresh': self.input_force_refresh.isChecked(),
            # Bodenstabilisierung
            'enable_stabilization': self.input_enable_stabilization.isChecked(),
            'soil_type': parse_soil_type(self.input_soil_type.currentText()),
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
