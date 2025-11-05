/**
 * Road Calculation Form Component
 * Form for configuring road parameters and triggering calculations
 */

import React, { useState, useEffect } from 'react';
import { RoadProject } from '../types';
import { latLngToUTM } from '../utils/coordinates';
import apiClient from '../services/api';

interface RoadFormProps {
  road: RoadProject | null;
  onCalculationComplete: (road: RoadProject) => void;
}

const RoadForm: React.FC<RoadFormProps> = ({ road, onCalculationComplete }) => {
  // Form state
  const [roadWidth, setRoadWidth] = useState<number>(6.0);
  const [designGrade, setDesignGrade] = useState<number>(2.5);
  const [cutSlope, setCutSlope] = useState<number>(1.5);
  const [fillSlope, setFillSlope] = useState<number>(2.0);
  const [profileType, setProfileType] = useState<string>('flat');
  const [stationInterval, setStationInterval] = useState<number>(10.0);
  const [includeDitches, setIncludeDitches] = useState<boolean>(false);
  const [ditchWidth, setDitchWidth] = useState<number>(1.0);
  const [ditchDepth, setDitchDepth] = useState<number>(0.5);

  // UI state
  const [isCalculating, setIsCalculating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [profileTypes, setProfileTypes] = useState<any[]>([]);

  // Load profile types
  useEffect(() => {
    const loadProfileTypes = async () => {
      try {
        const response = await apiClient.getRoadProfileTypes();
        setProfileTypes(response.profile_types || []);
      } catch (err) {
        console.error('Failed to load profile types:', err);
      }
    };
    loadProfileTypes();
  }, []);

  const handleCalculate = async () => {
    if (!road || !road.centerline || road.centerline.length < 2) {
      setError('Bitte zeichnen Sie zuerst eine Straßenlinie auf der Karte');
      return;
    }

    setIsCalculating(true);
    setError(null);

    try {
      // Convert centerline to UTM
      const utmCenterline = road.centerline.map((coord) => {
        const utm = latLngToUTM(coord);
        return [utm.easting, utm.northing];
      });

      // Get first point for DEM center
      const firstUTM = latLngToUTM(road.centerline[0]);

      // Step 1: Fetch DEM data
      const demResponse = await apiClient.fetchDEM({
        crs: firstUTM.epsg,
        center_x: firstUTM.easting,
        center_y: firstUTM.northing,
        buffer_meters: 250,
      });

      // Step 2: Calculate road earthwork
      const calculationResult = await apiClient.calculateRoad({
        dem_id: demResponse.dem_id,
        centerline: utmCenterline,
        road_width: roadWidth,
        design_grade: designGrade,
        cut_slope: cutSlope,
        fill_slope: fillSlope,
        profile_type: profileType,
        station_interval: stationInterval,
        include_ditches: includeDitches,
        ditch_width: includeDitches ? ditchWidth : undefined,
        ditch_depth: includeDitches ? ditchDepth : undefined,
      });

      // Update road with results
      const updatedRoad: RoadProject = {
        ...road,
        utmCenterline,
        calculation: calculationResult,
      };

      onCalculationComplete(updatedRoad);
    } catch (err: any) {
      console.error('Calculation error:', err);
      setError(err.response?.data?.detail || err.message || 'Berechnung fehlgeschlagen');
    } finally {
      setIsCalculating(false);
    }
  };

  if (!road) {
    return (
      <div style={styles.container}>
        <p style={styles.emptyState}>
          Zeichnen Sie eine Straßenlinie auf der Karte, um zu beginnen.
          <br />
          <small>Klicken Sie, um Punkte hinzuzufügen. Doppelklick zum Abschließen.</small>
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>{road.name}</h2>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Straßenlinie</h3>
        <p style={styles.info}>
          Punkte: {road.centerline?.length || 0}
          <br />
          {road.calculation && `Länge: ${road.calculation.road_length.toFixed(1)} m`}
        </p>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Straßenparameter</h3>

        <div style={styles.formGroup}>
          <label style={styles.label}>Breite (m):</label>
          <input
            type="number"
            value={roadWidth}
            onChange={(e) => setRoadWidth(parseFloat(e.target.value))}
            style={styles.input}
            min="2"
            max="20"
            step="0.5"
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Längsneigung (%):</label>
          <input
            type="number"
            value={designGrade}
            onChange={(e) => setDesignGrade(parseFloat(e.target.value))}
            style={styles.input}
            min="-15"
            max="15"
            step="0.5"
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Querprofil:</label>
          <select value={profileType} onChange={(e) => setProfileType(e.target.value)} style={styles.select}>
            {profileTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Böschungen</h3>

        <div style={styles.formGroup}>
          <label style={styles.label}>Aushub-Böschung (H:V):</label>
          <input
            type="number"
            value={cutSlope}
            onChange={(e) => setCutSlope(parseFloat(e.target.value))}
            style={styles.input}
            min="0.5"
            max="3"
            step="0.5"
          />
          <small style={styles.hint}>1:{cutSlope} (1 vertikal : {cutSlope} horizontal)</small>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Aufschüttungs-Böschung (H:V):</label>
          <input
            type="number"
            value={fillSlope}
            onChange={(e) => setFillSlope(parseFloat(e.target.value))}
            style={styles.input}
            min="1"
            max="4"
            step="0.5"
          />
          <small style={styles.hint}>1:{fillSlope}</small>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Stationsabstand (m):</label>
          <input
            type="number"
            value={stationInterval}
            onChange={(e) => setStationInterval(parseFloat(e.target.value))}
            style={styles.input}
            min="1"
            max="50"
            step="5"
          />
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Entwässerung</h3>

        <div style={styles.formGroup}>
          <label style={styles.checkboxLabel}>
            <input type="checkbox" checked={includeDitches} onChange={(e) => setIncludeDitches(e.target.checked)} />
            <span style={{ marginLeft: '8px' }}>Seitengräben einbeziehen</span>
          </label>
        </div>

        {includeDitches && (
          <>
            <div style={styles.formGroup}>
              <label style={styles.label}>Grabenbreite (m):</label>
              <input
                type="number"
                value={ditchWidth}
                onChange={(e) => setDitchWidth(parseFloat(e.target.value))}
                style={styles.input}
                min="0.5"
                max="3"
                step="0.1"
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Grabentiefe (m):</label>
              <input
                type="number"
                value={ditchDepth}
                onChange={(e) => setDitchDepth(parseFloat(e.target.value))}
                style={styles.input}
                min="0.2"
                max="2"
                step="0.1"
              />
            </div>
          </>
        )}
      </div>

      {error && (
        <div style={styles.error}>
          <strong>Fehler:</strong> {error}
        </div>
      )}

      <button
        onClick={handleCalculate}
        disabled={isCalculating}
        style={{
          ...styles.button,
          ...(isCalculating ? styles.buttonDisabled : {}),
        }}
      >
        {isCalculating ? 'Berechnung läuft...' : 'Berechnen'}
      </button>

      {road.calculation && (
        <div style={styles.results}>
          <h3 style={styles.sectionTitle}>Ergebnisse</h3>
          <div style={styles.resultsGrid}>
            <div style={styles.resultItem}>
              <label>Straßenlänge:</label>
              <strong>{road.calculation.road_length.toFixed(1)} m</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Stationen:</label>
              <strong>{road.calculation.num_stations}</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Gesamt Aushub:</label>
              <strong style={{ color: '#EF4444' }}>{road.calculation.total_cut.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Gesamt Auffüllung:</label>
              <strong style={{ color: '#10B981' }}>{road.calculation.total_fill.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Netto-Volumen:</label>
              <strong>{road.calculation.net_volume.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Ø Aushubtiefe:</label>
              <strong>{road.calculation.avg_cut_depth.toFixed(2)} m</strong>
            </div>
            {road.calculation.ditch_cut && (
              <div style={styles.resultItem}>
                <label>Graben-Aushub:</label>
                <strong>{road.calculation.ditch_cut.toFixed(1)} m³</strong>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Styles (reused from WKAForm with minor adaptations)
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: '20px',
    height: '100%',
    overflowY: 'auto',
    backgroundColor: '#F9FAFB',
  },
  title: {
    margin: '0 0 20px 0',
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#1F2937',
  },
  section: {
    backgroundColor: 'white',
    padding: '16px',
    marginBottom: '16px',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  sectionTitle: {
    margin: '0 0 12px 0',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#374151',
  },
  formGroup: {
    marginBottom: '12px',
  },
  label: {
    display: 'block',
    marginBottom: '4px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#374151',
  },
  input: {
    width: '100%',
    padding: '8px',
    fontSize: '14px',
    border: '1px solid #D1D5DB',
    borderRadius: '4px',
    boxSizing: 'border-box' as const,
  },
  select: {
    width: '100%',
    padding: '8px',
    fontSize: '14px',
    border: '1px solid #D1D5DB',
    borderRadius: '4px',
    boxSizing: 'border-box' as const,
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
    color: '#374151',
  },
  hint: {
    display: 'block',
    marginTop: '4px',
    fontSize: '12px',
    color: '#6B7280',
  },
  info: {
    margin: 0,
    fontSize: '14px',
    color: '#6B7280',
  },
  button: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: '#3B82F6',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    marginTop: '16px',
  },
  buttonDisabled: {
    backgroundColor: '#9CA3AF',
    cursor: 'not-allowed',
  },
  error: {
    marginTop: '16px',
    padding: '12px',
    backgroundColor: '#FEE2E2',
    border: '1px solid #EF4444',
    borderRadius: '8px',
    color: '#991B1B',
    fontSize: '14px',
  },
  results: {
    marginTop: '20px',
  },
  resultsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    marginBottom: '16px',
  },
  resultItem: {
    padding: '12px',
    backgroundColor: '#F3F4F6',
    borderRadius: '6px',
  },
  emptyState: {
    padding: '40px 20px',
    textAlign: 'center' as const,
    color: '#6B7280',
    fontSize: '14px',
  },
};

export default RoadForm;
