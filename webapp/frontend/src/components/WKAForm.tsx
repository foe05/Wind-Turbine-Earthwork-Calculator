/**
 * WKA Calculation Form Component
 * Form for configuring WKA site parameters and triggering calculations
 */

import React, { useState, useEffect } from 'react';
import { WKASite, WKACalculationRequest, CostRatesPreset } from '../types';
import apiClient from '../services/api';

interface WKAFormProps {
  site: WKASite | null;
  onCalculationComplete: (site: WKASite) => void;
}

const WKAForm: React.FC<WKAFormProps> = ({ site, onCalculationComplete }) => {
  // Form state
  const [foundationDiameter, setFoundationDiameter] = useState<number>(25);
  const [foundationDepth, setFoundationDepth] = useState<number>(3);
  const [foundationType, setFoundationType] = useState<number>(0);
  const [platformLength, setPlatformLength] = useState<number>(50);
  const [platformWidth, setPlatformWidth] = useState<number>(40);
  const [slopeWidth, setSlopeWidth] = useState<number>(10);
  const [slopeAngle, setSlopeAngle] = useState<number>(45);
  const [optimizationMethod, setOptimizationMethod] = useState<'mean' | 'min_cut' | 'balanced'>('balanced');

  // Cost calculation state
  const [calculateCosts, setCalculateCosts] = useState<boolean>(true);
  const [costPreset, setCostPreset] = useState<string>('standard');
  const [costPresets, setCostPresets] = useState<CostRatesPreset[]>([]);
  const [materialReuse, setMaterialReuse] = useState<boolean>(true);

  // UI state
  const [isCalculating, setIsCalculating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load cost presets
  useEffect(() => {
    const loadPresets = async () => {
      try {
        const presets = await apiClient.getCostPresets();
        setCostPresets(presets);
      } catch (err) {
        console.error('Failed to load cost presets:', err);
      }
    };
    loadPresets();
  }, []);

  const handleCalculate = async () => {
    if (!site) return;

    setIsCalculating(true);
    setError(null);

    try {
      // Step 1: Fetch DEM data
      const demResponse = await apiClient.fetchDEM({
        crs: site.utmPosition.epsg,
        center_x: site.utmPosition.easting,
        center_y: site.utmPosition.northing,
        buffer_meters: 250, // CRITICAL: 250m buffer requirement
      });

      // Step 2: Calculate WKA site
      const calculationRequest: WKACalculationRequest = {
        dem_id: demResponse.dem_id,
        center_x: site.utmPosition.easting,
        center_y: site.utmPosition.northing,
        foundation_diameter: foundationDiameter,
        foundation_depth: foundationDepth,
        foundation_type: foundationType,
        platform_length: platformLength,
        platform_width: platformWidth,
        slope_width: slopeWidth,
        slope_angle: slopeAngle,
        optimization_method: optimizationMethod,
      };

      const calculationResult = await apiClient.calculateWKASite(calculationRequest);

      // Step 3: Calculate costs (if enabled)
      let costResult = undefined;
      if (calculateCosts) {
        const selectedPreset = costPresets.find((p) => p.name === costPreset);
        if (selectedPreset) {
          costResult = await apiClient.calculateCosts({
            foundation_volume: calculationResult.foundation_volume,
            crane_cut: calculationResult.total_cut,
            crane_fill: calculationResult.total_fill,
            platform_area: calculationResult.platform_area,
            cost_excavation: selectedPreset.cost_excavation,
            cost_transport: selectedPreset.cost_transport,
            cost_fill_import: selectedPreset.cost_fill_import,
            cost_gravel: selectedPreset.cost_gravel,
            cost_compaction: selectedPreset.cost_compaction,
            gravel_thickness: selectedPreset.gravel_thickness,
            material_reuse: materialReuse,
            swell_factor: 1.25,
            compaction_factor: 0.85,
          });
        }
      }

      // Update site with results
      const updatedSite: WKASite = {
        ...site,
        calculation: calculationResult,
        cost: costResult,
      };

      onCalculationComplete(updatedSite);
    } catch (err: any) {
      console.error('Calculation error:', err);

      // Handle FastAPI validation errors
      let errorMessage = 'Berechnung fehlgeschlagen';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        // Check if it's an array of validation errors
        if (Array.isArray(detail)) {
          errorMessage = detail.map((e: any) =>
            `${e.loc?.join?.(' -> ') || 'Fehler'}: ${e.msg}`
          ).join(', ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        } else {
          errorMessage = JSON.stringify(detail);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
    } finally {
      setIsCalculating(false);
    }
  };

  if (!site) {
    return (
      <div style={styles.container}>
        <p style={styles.emptyState}>
          Wählen Sie einen Standort auf der Karte aus oder klicken Sie auf die Karte, um einen neuen Standort hinzuzufügen.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>{site.name}</h2>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Koordinaten</h3>
        <div style={styles.infoGrid}>
          <div>
            <label style={styles.label}>Lat/Lng:</label>
            <div style={styles.value}>
              {site.position.lat.toFixed(6)}°, {site.position.lng.toFixed(6)}°
            </div>
          </div>
          <div>
            <label style={styles.label}>UTM ({site.utmPosition.epsg}):</label>
            <div style={styles.value}>
              {site.utmPosition.easting.toFixed(2)} E, {site.utmPosition.northing.toFixed(2)} N
            </div>
          </div>
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Fundament</h3>
        <div style={styles.formGroup}>
          <label style={styles.label}>Durchmesser (m):</label>
          <input
            type="number"
            value={foundationDiameter}
            onChange={(e) => setFoundationDiameter(parseFloat(e.target.value))}
            style={styles.input}
            min="10"
            max="50"
            step="1"
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Tiefe (m):</label>
          <input
            type="number"
            value={foundationDepth}
            onChange={(e) => setFoundationDepth(parseFloat(e.target.value))}
            style={styles.input}
            min="1"
            max="10"
            step="0.5"
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Typ:</label>
          <select
            value={foundationType}
            onChange={(e) => setFoundationType(parseInt(e.target.value))}
            style={styles.select}
          >
            <option value="0">Flachgründung</option>
            <option value="1">Tiefgründung mit Konus</option>
            <option value="2">Pfahlgründung</option>
          </select>
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Kranstellfläche</h3>
        <div style={styles.formGroup}>
          <label style={styles.label}>Länge (m):</label>
          <input
            type="number"
            value={platformLength}
            onChange={(e) => setPlatformLength(parseFloat(e.target.value))}
            style={styles.input}
            min="20"
            max="100"
            step="5"
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Breite (m):</label>
          <input
            type="number"
            value={platformWidth}
            onChange={(e) => setPlatformWidth(parseFloat(e.target.value))}
            style={styles.input}
            min="20"
            max="80"
            step="5"
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Böschungsbreite (m):</label>
          <input
            type="number"
            value={slopeWidth}
            onChange={(e) => setSlopeWidth(parseFloat(e.target.value))}
            style={styles.input}
            min="5"
            max="30"
            step="1"
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Böschungswinkel (°):</label>
          <input
            type="number"
            value={slopeAngle}
            onChange={(e) => setSlopeAngle(parseFloat(e.target.value))}
            style={styles.input}
            min="30"
            max="60"
            step="5"
          />
        </div>
        <div style={styles.formGroup}>
          <label style={styles.label}>Optimierungsmethode:</label>
          <select
            value={optimizationMethod}
            onChange={(e) => setOptimizationMethod(e.target.value as 'mean' | 'min_cut' | 'balanced')}
            style={styles.select}
          >
            <option value="mean">Mittelwert</option>
            <option value="min_cut">Minimaler Aushub (40. Perzentil)</option>
            <option value="balanced">Ausgleich (Cut = Fill)</option>
          </select>
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Kostenberechnung</h3>
        <div style={styles.formGroup}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={calculateCosts}
              onChange={(e) => setCalculateCosts(e.target.checked)}
            />
            <span style={{ marginLeft: '8px' }}>Kosten berechnen</span>
          </label>
        </div>
        {calculateCosts && (
          <>
            <div style={styles.formGroup}>
              <label style={styles.label}>Kostensätze:</label>
              <select
                value={costPreset}
                onChange={(e) => setCostPreset(e.target.value)}
                style={styles.select}
              >
                {costPresets.map((preset) => (
                  <option key={preset.name} value={preset.name} title={preset.description}>
                    {preset.description}
                  </option>
                ))}
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={materialReuse}
                  onChange={(e) => setMaterialReuse(e.target.checked)}
                />
                <span style={{ marginLeft: '8px' }}>Material wiederverwenden</span>
              </label>
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

      {site.calculation && (
        <div style={styles.results}>
          <h3 style={styles.sectionTitle}>Ergebnisse</h3>
          <div style={styles.resultsGrid}>
            <div style={styles.resultItem}>
              <label>Fundament-Volumen:</label>
              <strong>{site.calculation.foundation_volume.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Planiehöhe:</label>
              <strong>{site.calculation.platform_height.toFixed(2)} m</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Kranstellfläche Aushub:</label>
              <strong>{site.calculation.platform_cut.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Kranstellfläche Auffüllung:</label>
              <strong>{site.calculation.platform_fill.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Gesamt Aushub:</label>
              <strong style={{ color: '#EF4444' }}>{site.calculation.total_cut.toFixed(1)} m³</strong>
            </div>
            <div style={styles.resultItem}>
              <label>Gesamt Auffüllung:</label>
              <strong style={{ color: '#10B981' }}>{site.calculation.total_fill.toFixed(1)} m³</strong>
            </div>
          </div>

          {site.cost && (
            <>
              <h3 style={styles.sectionTitle}>Kosten</h3>
              <div style={styles.resultsGrid}>
                <div style={styles.resultItem}>
                  <label>Aushub:</label>
                  <strong>{site.cost.cost_excavation.toFixed(2)} €</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Transport:</label>
                  <strong>{site.cost.cost_transport.toFixed(2)} €</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Auffüllung:</label>
                  <strong>{site.cost.cost_fill.toFixed(2)} €</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Schotter:</label>
                  <strong>{site.cost.cost_gravel.toFixed(2)} €</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Verdichtung:</label>
                  <strong>{site.cost.cost_compaction.toFixed(2)} €</strong>
                </div>
                <div style={styles.resultItem}>
                  <label>Gesamt:</label>
                  <strong style={{ fontSize: '18px', color: '#1F2937' }}>
                    {site.cost.cost_total.toFixed(2)} €
                  </strong>
                </div>
                {materialReuse && site.cost.cost_saving > 0 && (
                  <div style={styles.resultItem}>
                    <label>Einsparung:</label>
                    <strong style={{ color: '#10B981' }}>
                      {site.cost.cost_saving.toFixed(2)} € ({site.cost.saving_pct.toFixed(1)}%)
                    </strong>
                  </div>
                )}
              </div>
              {materialReuse && (
                <div style={styles.materialBalance}>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>Materialwiederverwertung</h4>
                  <p style={{ margin: '4px 0', fontSize: '12px' }}>
                    Verfügbar: {site.cost.material_balance.available.toFixed(1)} m³
                  </p>
                  <p style={{ margin: '4px 0', fontSize: '12px' }}>
                    Benötigt: {site.cost.material_balance.required.toFixed(1)} m³
                  </p>
                  <p style={{ margin: '4px 0', fontSize: '12px' }}>
                    Wiederverwendet: {site.cost.material_balance.reused.toFixed(1)} m³
                  </p>
                  {site.cost.material_balance.surplus > 0 && (
                    <p style={{ margin: '4px 0', fontSize: '12px', color: '#EF4444' }}>
                      Überschuss: {site.cost.material_balance.surplus.toFixed(1)} m³
                    </p>
                  )}
                  {site.cost.material_balance.deficit > 0 && (
                    <p style={{ margin: '4px 0', fontSize: '12px', color: '#10B981' }}>
                      Defizit: {site.cost.material_balance.deficit.toFixed(1)} m³
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

// Styles
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
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
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
  value: {
    fontSize: '14px',
    color: '#6B7280',
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
  materialBalance: {
    marginTop: '12px',
    padding: '12px',
    backgroundColor: '#F0FDF4',
    border: '1px solid #10B981',
    borderRadius: '6px',
  },
  emptyState: {
    padding: '40px 20px',
    textAlign: 'center' as const,
    color: '#6B7280',
    fontSize: '14px',
  },
};

export default WKAForm;
