/**
 * Terrain Analysis Form Component
 * Form for configuring terrain analysis parameters
 */

import React, { useState, useEffect } from 'react';
import { TerrainProject } from '../types';
import { latLngToUTM } from '../utils/coordinates';
import apiClient from '../services/api';

interface TerrainFormProps {
  terrain: TerrainProject | null;
  onAnalysisComplete: (terrain: TerrainProject) => void;
}

const TerrainForm: React.FC<TerrainFormProps> = ({ terrain, onAnalysisComplete }) => {
  // Form state
  const [analysisType, setAnalysisType] = useState<string>('cut_fill_balance');
  const [resolution, setResolution] = useState<number>(1.0);
  const [targetElevation, setTargetElevation] = useState<number | ''>('');
  const [optimizationMethod, setOptimizationMethod] = useState<string>('balanced');
  const [contourInterval, setContourInterval] = useState<number>(1.0);

  // UI state
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisTypes, setAnalysisTypes] = useState<any[]>([]);
  const [optimizationMethods, setOptimizationMethods] = useState<any[]>([]);

  // Load options
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [types, methods] = await Promise.all([
          apiClient.getTerrainAnalysisTypes(),
          apiClient.getTerrainOptimizationMethods(),
        ]);
        setAnalysisTypes(types.analysis_types || []);
        setOptimizationMethods(methods.optimization_methods || []);
      } catch (err) {
        console.error('Failed to load options:', err);
      }
    };
    loadOptions();
  }, []);

  const handleAnalyze = async () => {
    if (!terrain || !terrain.polygon || terrain.polygon.length < 3) {
      setError('Bitte zeichnen Sie zuerst ein Polygon auf der Karte');
      return;
    }

    // Validate target elevation for volume_calculation
    if (analysisType === 'volume_calculation' && targetElevation === '') {
      setError('Bitte geben Sie eine Zielhöhe an');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      // Convert polygon to UTM
      const utmPolygon = terrain.polygon.map((coord) => {
        const utm = latLngToUTM(coord);
        return [utm.easting, utm.northing];
      });

      // Get center point for DEM
      const firstUTM = latLngToUTM(terrain.polygon[0]);

      // Step 1: Fetch DEM
      const demResponse = await apiClient.fetchDEM({
        crs: firstUTM.epsg,
        center_x: firstUTM.easting,
        center_y: firstUTM.northing,
        buffer_meters: 250,
      });

      // Step 2: Analyze terrain
      const analysisResult = await apiClient.analyzeTerrain({
        dem_id: demResponse.dem_id,
        polygon: utmPolygon,
        analysis_type: analysisType,
        resolution,
        target_elevation: targetElevation !== '' ? Number(targetElevation) : undefined,
        optimization_method: optimizationMethod,
        contour_interval: contourInterval,
      });

      // Update terrain with results
      const updatedTerrain: TerrainProject = {
        ...terrain,
        utmPolygon,
        analysis: analysisResult,
      };

      onAnalysisComplete(updatedTerrain);
    } catch (err: any) {
      console.error('Analysis error:', err);
      setError(err.response?.data?.detail || err.message || 'Analyse fehlgeschlagen');
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (!terrain) {
    return (
      <div style={styles.container}>
        <p style={styles.emptyState}>
          Zeichnen Sie ein Polygon auf der Karte für die Geländeanalyse.
          <br />
          <small>Klicken Sie, um Punkte hinzuzufügen. Doppelklick zum Abschließen.</small>
        </p>
      </div>
    );
  }

  const selectedAnalysisType = analysisTypes.find((t) => t.value === analysisType);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>{terrain.name}</h2>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Analysefläche</h3>
        <p style={styles.info}>
          Polygon-Punkte: {terrain.polygon?.length || 0}
          <br />
          {terrain.analysis && `Fläche: ${terrain.analysis.polygon_area.toFixed(0)} m²`}
        </p>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Analysemethode</h3>

        <div style={styles.formGroup}>
          <label style={styles.label}>Analyse-Typ:</label>
          <select value={analysisType} onChange={(e) => setAnalysisType(e.target.value)} style={styles.select}>
            {analysisTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          {selectedAnalysisType && <small style={styles.hint}>{selectedAnalysisType.description}</small>}
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Auflösung (m):</label>
          <input type="number" value={resolution} onChange={(e) => setResolution(parseFloat(e.target.value))} style={styles.input} min="0.1" max="10" step="0.5" />
          <small style={styles.hint}>Kleinere Werte = höhere Genauigkeit, längere Berechnungszeit</small>
        </div>

        {analysisType === 'cut_fill_balance' && (
          <div style={styles.formGroup}>
            <label style={styles.label}>Optimierungsmethode:</label>
            <select value={optimizationMethod} onChange={(e) => setOptimizationMethod(e.target.value)} style={styles.select}>
              {optimizationMethods.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
            {optimizationMethods.find((m) => m.value === optimizationMethod) && (
              <small style={styles.hint}>{optimizationMethods.find((m) => m.value === optimizationMethod)?.description}</small>
            )}
          </div>
        )}

        {analysisType === 'volume_calculation' && (
          <div style={styles.formGroup}>
            <label style={styles.label}>Zielhöhe (m):</label>
            <input type="number" value={targetElevation} onChange={(e) => setTargetElevation(e.target.value === '' ? '' : parseFloat(e.target.value))} style={styles.input} step="0.1" />
            <small style={styles.hint}>Höhe für Cut/Fill-Berechnung</small>
          </div>
        )}

        {analysisType === 'contour_generation' && (
          <div style={styles.formGroup}>
            <label style={styles.label}>Höhenlinien-Intervall (m):</label>
            <input type="number" value={contourInterval} onChange={(e) => setContourInterval(parseFloat(e.target.value))} style={styles.input} min="0.1" max="50" step="0.5" />
          </div>
        )}
      </div>

      {error && (
        <div style={styles.error}>
          <strong>Fehler:</strong> {error}
        </div>
      )}

      <button onClick={handleAnalyze} disabled={isAnalyzing} style={{ ...styles.button, ...(isAnalyzing ? styles.buttonDisabled : {}) }}>
        {isAnalyzing ? 'Analyse läuft...' : 'Analysieren'}
      </button>

      {terrain.analysis && (
        <div style={styles.results}>
          <h3 style={styles.sectionTitle}>Ergebnisse - {terrain.analysis.analysis_type}</h3>

          <div style={styles.resultsGrid}>
            <div style={styles.resultItem}>
              <label>Fläche:</label>
              <strong>{terrain.analysis.polygon_area.toFixed(0)} m²</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Messpunkte:</label>
              <strong>{terrain.analysis.num_sample_points}</strong>
            </div>

            {terrain.analysis.optimal_elevation !== undefined && (
              <div style={styles.resultItem}>
                <label>Optimale Höhe:</label>
                <strong>{terrain.analysis.optimal_elevation.toFixed(2)} m</strong>
              </div>
            )}

            {terrain.analysis.cut_volume !== undefined && (
              <>
                <div style={styles.resultItem}>
                  <label>Aushub-Volumen:</label>
                  <strong style={{ color: '#EF4444' }}>{terrain.analysis.cut_volume.toFixed(1)} m³</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Auffüll-Volumen:</label>
                  <strong style={{ color: '#10B981' }}>{terrain.analysis.fill_volume.toFixed(1)} m³</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Netto-Volumen:</label>
                  <strong>{terrain.analysis.net_volume?.toFixed(1)} m³</strong>
                </div>
              </>
            )}

            {terrain.analysis.min_elevation !== undefined && (
              <>
                <div style={styles.resultItem}>
                  <label>Min. Höhe:</label>
                  <strong>{terrain.analysis.min_elevation.toFixed(2)} m</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Max. Höhe:</label>
                  <strong>{terrain.analysis.max_elevation.toFixed(2)} m</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Ø Höhe:</label>
                  <strong>{terrain.analysis.avg_elevation.toFixed(2)} m</strong>
                </div>
              </>
            )}
          </div>

          {terrain.analysis.slope_analysis && (
            <div style={styles.slopeSection}>
              <h4 style={styles.subsectionTitle}>Neigungsanalyse</h4>
              <div style={styles.resultsGrid}>
                <div style={styles.resultItem}>
                  <label>Ø Neigung:</label>
                  <strong>{terrain.analysis.slope_analysis.avg_slope?.toFixed(2)}%</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Max. Neigung:</label>
                  <strong>{terrain.analysis.slope_analysis.max_slope?.toFixed(2)}%</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Median Neigung:</label>
                  <strong>{terrain.analysis.slope_analysis.median_slope?.toFixed(2)}%</strong>
                </div>
              </div>
            </div>
          )}

          {terrain.analysis.contour_data && (
            <div style={styles.contourSection}>
              <h4 style={styles.subsectionTitle}>Höhenlinien</h4>
              <p style={styles.info}>
                Anzahl Höhenlinien: {terrain.analysis.contour_data.num_contours}
                <br />
                Intervall: {terrain.analysis.contour_data.contour_interval} m<br />
                Bereich: {terrain.analysis.contour_data.min_elevation?.toFixed(1)} - {terrain.analysis.contour_data.max_elevation?.toFixed(1)} m
              </p>
            </div>
          )}
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
  subsectionTitle: { margin: '0 0 8px 0', fontSize: '14px', fontWeight: 'bold', color: '#374151' },
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
  slopeSection: { marginTop: '16px', padding: '12px', backgroundColor: '#F0FDF4', borderRadius: '6px' },
  contourSection: { marginTop: '16px', padding: '12px', backgroundColor: '#EFF6FF', borderRadius: '6px' },
  emptyState: { padding: '40px 20px', textAlign: 'center' as const, color: '#6B7280', fontSize: '14px' },
};

export default TerrainForm;
