/**
 * Batch Upload Component - CSV/GeoJSON Upload with Drag & Drop
 */

import React, { useState, useRef } from 'react';
import apiClient from '../services/api';
import { BatchUploadResponse } from '../types';

interface BatchUploadProps {
  projectId: string;
  onUploadComplete?: (response: BatchUploadResponse) => void;
}

const BatchUpload: React.FC<BatchUploadProps> = ({ projectId, onUploadComplete }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<BatchUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    const fileName = file.name.toLowerCase();
    const isCSV = fileName.endsWith('.csv');
    const isGeoJSON = fileName.endsWith('.json') || fileName.endsWith('.geojson');

    if (!isCSV && !isGeoJSON) {
      setError('Nur CSV oder GeoJSON Dateien erlaubt');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      let response: BatchUploadResponse;

      if (isCSV) {
        response = await apiClient.uploadCSV(projectId, file);
      } else {
        response = await apiClient.uploadGeoJSON(projectId, file);
      }

      setResult(response);
      if (onUploadComplete) {
        onUploadComplete(response);
      }
    } catch (err: any) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'Upload fehlgeschlagen');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Batch Upload</h3>
      <p style={styles.subtitle}>CSV oder GeoJSON mit max. 123 Standorten</p>

      <div
        style={{
          ...styles.dropzone,
          ...(isDragging ? styles.dropzoneDragging : {}),
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json,.geojson"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        {uploading ? (
          <div>
            <div style={styles.spinner}></div>
            <p style={styles.dropzoneText}>Upload läuft...</p>
          </div>
        ) : (
          <>
            <p style={styles.dropzoneIcon}>📁</p>
            <p style={styles.dropzoneText}>
              Datei hier ablegen oder klicken zum Auswählen
            </p>
            <p style={styles.dropzoneHint}>CSV oder GeoJSON (max. 5MB)</p>
          </>
        )}
      </div>

      {error && (
        <div style={styles.error}>
          ⚠️ {error}
        </div>
      )}

      {result && (
        <div style={styles.success}>
          <h4 style={styles.successTitle}>✓ Upload erfolgreich!</h4>
          <div style={styles.resultGrid}>
            <div style={styles.resultItem}>
              <span style={styles.resultLabel}>Sites importiert:</span>
              <span style={styles.resultValue}>{result.sites_imported}</span>
            </div>
            <div style={styles.resultItem}>
              <span style={styles.resultLabel}>Jobs erstellt:</span>
              <span style={styles.resultValue}>{result.jobs_created.length}</span>
            </div>
            {result.errors.length > 0 && (
              <div style={styles.resultItem}>
                <span style={styles.resultLabel}>Fehler:</span>
                <span style={styles.resultValue}>{result.errors.length}</span>
              </div>
            )}
          </div>

          {result.errors.length > 0 && (
            <details style={styles.errorDetails}>
              <summary style={styles.errorSummary}>Fehler anzeigen</summary>
              <ul style={styles.errorList}>
                {result.errors.map((err, idx) => (
                  <li key={idx} style={styles.errorListItem}>{err}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      <div style={styles.help}>
        <p style={styles.helpTitle}>CSV Format:</p>
        <pre style={styles.helpCode}>
          {`name,lat,lng,foundation_diameter,foundation_depth
Site1,52.5,13.4,25.0,4.0
Site2,52.6,13.5,25.0,4.0`}
        </pre>
        <p style={styles.helpTitle}>GeoJSON Format:</p>
        <pre style={styles.helpCode}>
          {`{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [13.4, 52.5]},
    "properties": {"name": "Site1", "foundation_diameter": 25.0}
  }]
}`}
        </pre>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: '24px',
    maxWidth: '800px',
    margin: '0 auto',
  },
  title: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: '4px',
  },
  subtitle: {
    fontSize: '14px',
    color: '#6B7280',
    marginBottom: '20px',
  },
  dropzone: {
    border: '2px dashed #D1D5DB',
    borderRadius: '8px',
    padding: '48px 24px',
    textAlign: 'center' as const,
    cursor: 'pointer',
    backgroundColor: '#F9FAFB',
    transition: 'all 0.2s',
  },
  dropzoneDragging: {
    borderColor: '#3B82F6',
    backgroundColor: '#EFF6FF',
  },
  dropzoneIcon: {
    fontSize: '48px',
    margin: '0 0 12px',
  },
  dropzoneText: {
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: '4px',
  },
  dropzoneHint: {
    fontSize: '14px',
    color: '#6B7280',
  },
  spinner: {
    width: '48px',
    height: '48px',
    border: '4px solid #E5E7EB',
    borderTop: '4px solid #3B82F6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 16px',
  },
  error: {
    marginTop: '16px',
    padding: '12px 16px',
    backgroundColor: '#FEE2E2',
    color: '#991B1B',
    borderRadius: '6px',
    fontSize: '14px',
  },
  success: {
    marginTop: '16px',
    padding: '16px',
    backgroundColor: '#D1FAE5',
    borderRadius: '6px',
  },
  successTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#065F46',
    marginBottom: '12px',
  },
  resultGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: '12px',
    marginBottom: '12px',
  },
  resultItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  },
  resultLabel: {
    fontSize: '12px',
    color: '#065F46',
  },
  resultValue: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#047857',
  },
  errorDetails: {
    marginTop: '12px',
    padding: '12px',
    backgroundColor: 'white',
    borderRadius: '4px',
  },
  errorSummary: {
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#991B1B',
    cursor: 'pointer',
  },
  errorList: {
    marginTop: '8px',
    paddingLeft: '20px',
  },
  errorListItem: {
    fontSize: '13px',
    color: '#991B1B',
    marginBottom: '4px',
  },
  help: {
    marginTop: '32px',
    padding: '16px',
    backgroundColor: '#F9FAFB',
    borderRadius: '8px',
  },
  helpTitle: {
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: '8px',
  },
  helpCode: {
    fontSize: '12px',
    fontFamily: 'monospace',
    backgroundColor: 'white',
    padding: '12px',
    borderRadius: '4px',
    overflowX: 'auto' as const,
    marginBottom: '16px',
  },
};

export default BatchUpload;
