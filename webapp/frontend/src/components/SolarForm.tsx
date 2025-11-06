/**
 * Solar Park Calculation Form Component
 * Form for configuring solar park parameters and triggering calculations
 */

import React, { useState, useEffect } from 'react';
import { SolarProject } from '../types';
import { latLngToUTM } from '../utils/coordinates';
import apiClient from '../services/api';

interface SolarFormProps {
  solar: SolarProject | null;
  onCalculationComplete: (solar: SolarProject) => void;
}

const SolarForm: React.FC<SolarFormProps> = ({ solar, onCalculationComplete }) => {
  // Form state
  const [panelLength, setPanelLength] = useState<number>(2.0);
  const [panelWidth, setPanelWidth] = useState<number>(1.0);
  const [rowSpacing, setRowSpacing] = useState<number>(5.0);
  const [panelTilt, setPanelTilt] = useState<number>(20);
  const [foundationType, setFoundationType] = useState<string>('driven_piles');
  const [gradingStrategy, setGradingStrategy] = useState<string>('minimal');
  const [orientation, setOrientation] = useState<number>(180);

  // UI state
  const [isCalculating, setIsCalculating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [foundationTypes, setFoundationTypes] = useState<any[]>([]);
  const [gradingStrategies, setGradingStrategies] = useState<any[]>([]);

  // Load options
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [foundations, strategies] = await Promise.all([
          apiClient.getSolarFoundationTypes(),
          apiClient.getSolarGradingStrategies(),
        ]);
        setFoundationTypes(foundations.foundation_types || []);
        setGradingStrategies(strategies.grading_strategies || []);
      } catch (err) {
        console.error('Failed to load options:', err);
      }
    };
    loadOptions();
  }, []);

  const handleCalculate = async () => {
    if (!solar || !solar.boundary || solar.boundary.length < 3) {
      setError('Bitte zeichnen Sie zuerst ein Polygon auf der Karte');
      return;
    }

    setIsCalculating(true);
    setError(null);

    try {
      // Convert boundary to UTM
      const utmBoundary = solar.boundary.map((coord) => {
        const utm = latLngToUTM(coord);
        return [utm.easting, utm.northing];
      });

      // Get center point for DEM
      const firstUTM = latLngToUTM(solar.boundary[0]);

      // Step 1: Fetch DEM
      const demResponse = await apiClient.fetchDEM({
        crs: firstUTM.epsg,
        center_x: firstUTM.easting,
        center_y: firstUTM.northing,
        buffer_meters: 250,
      });

      // Step 2: Calculate solar park
      const calculationResult = await apiClient.calculateSolar({
        dem_id: demResponse.dem_id,
        boundary: utmBoundary,
        panel_length: panelLength,
        panel_width: panelWidth,
        row_spacing: rowSpacing,
        panel_tilt: panelTilt,
        foundation_type: foundationType,
        grading_strategy: gradingStrategy,
        orientation,
      });

      // Update solar with results
      const updatedSolar: SolarProject = {
        ...solar,
        utmBoundary,
        calculation: calculationResult,
      };

      onCalculationComplete(updatedSolar);
    } catch (err: any) {
      console.error('Calculation error:', err);
      setError(err.response?.data?.detail || err.message || 'Berechnung fehlgeschlagen');
    } finally {
      setIsCalculating(false);
    }
  };

  if (!solar) {
    return (
      <div style={styles.container}>
        <p style={styles.emptyState}>
          Zeichnen Sie ein Polygon auf der Karte für den Solarpark.
          <br />
          <small>Klicken Sie, um Punkte hinzuzufügen. Doppelklick zum Abschließen.</small>
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>{solar.name}</h2>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Park-Fläche</h3>
        <p style={styles.info}>
          Polygon-Punkte: {solar.boundary?.length || 0}
          <br />
          {solar.calculation && `Fläche: ${solar.calculation.site_area.toFixed(0)} m²`}
        </p>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Panel-Konfiguration</h3>

        <div style={styles.formGroup}>
          <label style={styles.label}>Panel-Länge (m):</label>
          <input
            type="number"
            value={panelLength}
            onChange={(e) => setPanelLength(parseFloat(e.target.value))}
            style={styles.input}
            min="0.5"
            max="3"
            step="0.1"
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Panel-Breite (m):</label>
          <input
            type="number"
            value={panelWidth}
            onChange={(e) => setPanelWidth(parseFloat(e.target.value))}
            style={styles.input}
            min="0.5"
            max="2.5"
            step="0.1"
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Reihenabstand (m):</label>
          <input
            type="number"
            value={rowSpacing}
            onChange={(e) => setRowSpacing(parseFloat(e.target.value))}
            style={styles.input}
            min="2"
            max="20"
            step="0.5"
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Neigungswinkel (°):</label>
          <input
            type="number"
            value={panelTilt}
            onChange={(e) => setPanelTilt(parseFloat(e.target.value))}
            style={styles.input}
            min="0"
            max="60"
            step="5"
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Ausrichtung (°):</label>
          <input
            type="number"
            value={orientation}
            onChange={(e) => setOrientation(parseFloat(e.target.value))}
            style={styles.input}
            min="0"
            max="360"
            step="15"
          />
          <small style={styles.hint}>180° = Süden</small>
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Fundament</h3>

        <div style={styles.formGroup}>
          <label style={styles.label}>Fundamenttyp:</label>
          <select value={foundationType} onChange={(e) => setFoundationType(e.target.value)} style={styles.select}>
            {foundationTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          {foundationTypes.find((t) => t.value === foundationType) && (
            <small style={styles.hint}>{foundationTypes.find((t) => t.value === foundationType).description}</small>
          )}
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Geländemodellierung</h3>

        <div style={styles.formGroup}>
          <label style={styles.label}>Strategie:</label>
          <select value={gradingStrategy} onChange={(e) => setGradingStrategy(e.target.value)} style={styles.select}>
            {gradingStrategies.map((strategy) => (
              <option key={strategy.value} value={strategy.value}>
                {strategy.label}
              </option>
            ))}
          </select>
          {gradingStrategies.find((s) => s.value === gradingStrategy) && (
            <small style={styles.hint}>{gradingStrategies.find((s) => s.value === gradingStrategy).description}</small>
          )}
        </div>
      </div>

      {error && (
        <div style={styles.error}>
          <strong>Fehler:</strong> {error}
        </div>
      )}

      <button onClick={handleCalculate} disabled={isCalculating} style={{ ...styles.button, ...(isCalculating ? styles.buttonDisabled : {}) }}>
        {isCalculating ? 'Berechnung läuft...' : 'Berechnen'}
      </button>

      {solar.calculation && (
        <div style={styles.results}>
          <h3 style={styles.sectionTitle}>Ergebnisse</h3>
          <div style={styles.resultsGrid}>
            <div style={styles.resultItem}>
              <label>Panel-Anzahl:</label>
              <strong>{solar.calculation.num_panels.toLocaleString()}</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Panel-Fläche:</label>
              <strong>{solar.calculation.panel_area.toFixed(0)} m²</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Fundament-Volumen:</label>
              <strong>{solar.calculation.foundation_volume.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Planierung Aushub:</label>
              <strong style={{ color: '#EF4444' }}>{solar.calculation.grading_cut.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Planierung Auffüllung:</label>
              <strong style={{ color: '#10B981' }}>{solar.calculation.grading_fill.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Gesamt Aushub:</label>
              <strong style={{ color: '#EF4444' }}>{solar.calculation.total_cut.toFixed(1)} m³</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: { padding: '20px', height: '100%', overflowY: 'auto', backgroundColor: '#F9FAFB' },
  title: { margin: '0 0 20px 0', fontSize: '24px', fontWeight: 'bold', color: '#1F2937' },
  section: { backgroundColor: 'white', padding: '16px', marginBottom: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' },
  sectionTitle: { margin: '0 0 12px 0', fontSize: '16px', fontWeight: 'bold', color: '#374151' },
  formGroup: { marginBottom: '12px' },
  label: { display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500', color: '#374151' },
  input: { width: '100%', padding: '8px', fontSize: '14px', border: '1px solid #D1D5DB', borderRadius: '4px', boxSizing: 'border-box' as const },
  select: { width: '100%', padding: '8px', fontSize: '14px', border: '1px solid #D1D5DB', borderRadius: '4px', boxSizing: 'border-box' as const },
  hint: { display: 'block', marginTop: '4px', fontSize: '12px', color: '#6B7280' },
  info: { margin: 0, fontSize: '14px', color: '#6B7280' },
  button: { width: '100%', padding: '12px', fontSize: '16px', fontWeight: 'bold', color: 'white', backgroundColor: '#3B82F6', border: 'none', borderRadius: '8px', cursor: 'pointer', marginTop: '16px' },
  buttonDisabled: { backgroundColor: '#9CA3AF', cursor: 'not-allowed' },
  error: { marginTop: '16px', padding: '12px', backgroundColor: '#FEE2E2', border: '1px solid #EF4444', borderRadius: '8px', color: '#991B1B', fontSize: '14px' },
  results: { marginTop: '20px' },
  resultsGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' },
  resultItem: { padding: '12px', backgroundColor: '#F3F4F6', borderRadius: '6px' },
  emptyState: { padding: '40px 20px', textAlign: 'center' as const, color: '#6B7280', fontSize: '14px' },
};

export default SolarForm;
