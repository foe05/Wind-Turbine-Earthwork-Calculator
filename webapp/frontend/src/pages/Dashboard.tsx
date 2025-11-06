/**
 * Dashboard Page - Main WKA calculation interface
 */

import React, { useState } from 'react';
import Map from '../components/Map';
import WKAForm from '../components/WKAForm';
import { WKASite, Project, ReportRequest } from '../types';
import apiClient from '../services/api';

const Dashboard: React.FC = () => {
  const [project, setProject] = useState<Project>({
    id: 'project_1',
    name: 'Neues Projekt',
    description: 'WKA Erdarbeiten Berechnung',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    sites: [],
  });

  const [selectedSite, setSelectedSite] = useState<WKASite | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  const handleSiteAdded = (site: WKASite) => {
    const updatedProject = {
      ...project,
      sites: [...project.sites, site],
    };
    setProject(updatedProject);
    setSelectedSite(site);
  };

  const handleSiteSelected = (site: WKASite | null) => {
    setSelectedSite(site);
  };

  const handleCalculationComplete = (updatedSite: WKASite) => {
    const updatedSites = project.sites.map((s) =>
      s.id === updatedSite.id ? updatedSite : s
    );
    setProject({
      ...project,
      sites: updatedSites,
    });
    setSelectedSite(updatedSite);
  };

  const handleDeleteSite = () => {
    if (!selectedSite) return;
    if (!window.confirm(`Möchten Sie ${selectedSite.name} wirklich löschen?`)) return;

    const updatedSites = project.sites.filter((s) => s.id !== selectedSite.id);
    setProject({
      ...project,
      sites: updatedSites,
    });
    setSelectedSite(null);
  };

  const handleGenerateReport = async () => {
    // Check if we have calculated sites
    const calculatedSites = project.sites.filter((s) => s.calculation);
    if (calculatedSites.length === 0) {
      alert('Bitte berechnen Sie mindestens einen Standort vor der Report-Generierung.');
      return;
    }

    setIsGeneratingReport(true);

    try {
      const reportRequest: ReportRequest = {
        project_name: project.name,
        sites: calculatedSites.map((site) => ({
          id: site.id,
          coord_x: site.utmPosition.easting,
          coord_y: site.utmPosition.northing,
          foundation_volume: site.calculation!.foundation_volume,
          platform_height: site.calculation!.platform_height,
          platform_cut: site.calculation!.platform_cut,
          platform_fill: site.calculation!.platform_fill,
          slope_cut: site.calculation!.slope_cut,
          slope_fill: site.calculation!.slope_fill,
          total_cut: site.calculation!.total_cut,
          total_fill: site.calculation!.total_fill,
          platform_area: site.calculation!.platform_area,
        })),
        format: 'pdf',
      };

      const response = await apiClient.generateReport(reportRequest);

      // Download the report
      const filename = response.download_url.split('/').pop() || 'report.pdf';
      const reportId = response.report_id;
      const blob = await apiClient.downloadReport(reportId, filename);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      alert('Report erfolgreich generiert und heruntergeladen!');
    } catch (err: any) {
      console.error('Report generation error:', err);
      alert(`Report-Generierung fehlgeschlagen: ${err.message}`);
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const handleLogout = async () => {
    await apiClient.logout();
    window.location.href = '/login';
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.headerTitle}>Geo-Engineering Platform</h1>
          <input
            type="text"
            value={project.name}
            onChange={(e) => setProject({ ...project, name: e.target.value })}
            style={styles.projectName}
          />
        </div>
        <div style={styles.headerRight}>
          <button onClick={handleGenerateReport} style={styles.reportButton} disabled={isGeneratingReport}>
            {isGeneratingReport ? 'Generiere...' : 'PDF Report'}
          </button>
          <button onClick={handleLogout} style={styles.logoutButton}>
            Abmelden
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div style={styles.mainContent}>
        {/* Map Section */}
        <div style={styles.mapSection}>
          <Map
            sites={project.sites}
            onSiteAdded={handleSiteAdded}
            onSiteSelected={handleSiteSelected}
            selectedSite={selectedSite}
          />
        </div>

        {/* Form Section */}
        <div style={styles.formSection}>
          <WKAForm site={selectedSite} onCalculationComplete={handleCalculationComplete} />
          {selectedSite && (
            <button onClick={handleDeleteSite} style={styles.deleteButton}>
              Standort löschen
            </button>
          )}
        </div>
      </div>

      {/* Status Bar */}
      <footer style={styles.footer}>
        <div style={styles.footerContent}>
          <span>Standorte: {project.sites.length}</span>
          <span>Berechnet: {project.sites.filter((s) => s.calculation).length}</span>
          <span>
            Gesamt Aushub:{' '}
            {project.sites
              .filter((s) => s.calculation)
              .reduce((sum, s) => sum + s.calculation!.total_cut, 0)
              .toFixed(1)}{' '}
            m³
          </span>
          <span>
            Gesamt Auffüllung:{' '}
            {project.sites
              .filter((s) => s.calculation)
              .reduce((sum, s) => sum + s.calculation!.total_fill, 0)
              .toFixed(1)}{' '}
            m³
          </span>
        </div>
      </footer>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100vh',
    width: '100vw',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    backgroundColor: '#1F2937',
    color: 'white',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
  },
  headerTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 'bold',
  },
  projectName: {
    padding: '8px 12px',
    fontSize: '16px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: '#374151',
    color: 'white',
  },
  headerRight: {
    display: 'flex',
    gap: '12px',
  },
  reportButton: {
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: '#10B981',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  logoutButton: {
    padding: '8px 16px',
    fontSize: '14px',
    color: 'white',
    backgroundColor: '#EF4444',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  mapSection: {
    flex: '1 1 60%',
    height: '100%',
  },
  formSection: {
    flex: '1 1 40%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: '#F9FAFB',
    borderLeft: '1px solid #E5E7EB',
    overflow: 'hidden',
  },
  deleteButton: {
    margin: '0 20px 20px 20px',
    padding: '10px',
    fontSize: '14px',
    color: 'white',
    backgroundColor: '#EF4444',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  footer: {
    padding: '12px 24px',
    backgroundColor: '#F3F4F6',
    borderTop: '1px solid #E5E7EB',
  },
  footerContent: {
    display: 'flex',
    gap: '24px',
    fontSize: '14px',
    color: '#6B7280',
  },
};

export default Dashboard;
