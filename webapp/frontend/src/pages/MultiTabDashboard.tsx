/**
 * Multi-Tab Dashboard for Phase 2
 * Supports WKA, Road, Solar, and Terrain calculations
 */

import React, { useState } from 'react';
import MapWithDrawing from '../components/MapWithDrawing';
import WKAForm from '../components/WKAForm';
import RoadForm from '../components/RoadForm';
import SolarForm from '../components/SolarForm';
import TerrainForm from '../components/TerrainForm';
import { WKASite, RoadProject, SolarProject, TerrainProject } from '../types';
import apiClient from '../services/api';

type TabType = 'wka' | 'road' | 'solar' | 'terrain';

const MultiTabDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('wka');
  const [projectName, setProjectName] = useState('Neues Projekt');

  // WKA state (Phase 1)
  const [wkaSites, setWkaSites] = useState<WKASite[]>([]);
  const [selectedWKASite, setSelectedWKASite] = useState<WKASite | null>(null);

  // Road state (Phase 2)
  const [roadProjects, setRoadProjects] = useState<RoadProject[]>([]);
  const [selectedRoad, setSelectedRoad] = useState<RoadProject | null>(null);

  // Solar state (Phase 2)
  const [solarProjects, setSolarProjects] = useState<SolarProject[]>([]);
  const [selectedSolar, setSelectedSolar] = useState<SolarProject | null>(null);

  // Terrain state (Phase 2)
  const [terrainProjects, setTerrainProjects] = useState<TerrainProject[]>([]);
  const [selectedTerrain, setSelectedTerrain] = useState<TerrainProject | null>(null);

  // Map drawing mode
  const [drawingMode, setDrawingMode] = useState<'point' | 'line' | 'polygon' | null>(null);

  const handleLogout = async () => {
    await apiClient.logout();
    window.location.href = '/login';
  };

  const getTabContent = () => {
    switch (activeTab) {
      case 'wka':
        return (
          <WKAForm
            site={selectedWKASite}
            onCalculationComplete={(site) => {
              const updated = wkaSites.map((s) => (s.id === site.id ? site : s));
              setWkaSites(updated);
              setSelectedWKASite(site);
            }}
          />
        );
      case 'road':
        return (
          <RoadForm
            road={selectedRoad}
            onCalculationComplete={(road) => {
              const updated = roadProjects.map((r) => (r.id === road.id ? road : r));
              setRoadProjects(updated);
              setSelectedRoad(road);
            }}
          />
        );
      case 'solar':
        return (
          <SolarForm
            solar={selectedSolar}
            onCalculationComplete={(solar) => {
              const updated = solarProjects.map((s) => (s.id === solar.id ? solar : s));
              setSolarProjects(updated);
              setSelectedSolar(solar);
            }}
          />
        );
      case 'terrain':
        return (
          <TerrainForm
            terrain={selectedTerrain}
            onAnalysisComplete={(terrain) => {
              const updated = terrainProjects.map((t) => (t.id === terrain.id ? terrain : t));
              setTerrainProjects(updated);
              setSelectedTerrain(terrain);
            }}
          />
        );
      default:
        return null;
    }
  };

  const getMapDrawingMode = () => {
    switch (activeTab) {
      case 'wka':
        return 'point';
      case 'road':
        return 'line';
      case 'solar':
      case 'terrain':
        return 'polygon';
      default:
        return null;
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.headerTitle}>Geo-Engineering Platform</h1>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            style={styles.projectName}
          />
        </div>
        <div style={styles.headerRight}>
          <button onClick={handleLogout} style={styles.logoutButton}>
            Abmelden
          </button>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav style={styles.tabNav}>
        <button
          style={{ ...styles.tab, ...(activeTab === 'wka' ? styles.tabActive : {}) }}
          onClick={() => {
            setActiveTab('wka');
            setDrawingMode('point');
          }}
        >
          🏗️ WKA
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'road' ? styles.tabActive : {}) }}
          onClick={() => {
            setActiveTab('road');
            setDrawingMode('line');
          }}
        >
          🛣️ Straße
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'solar' ? styles.tabActive : {}) }}
          onClick={() => {
            setActiveTab('solar');
            setDrawingMode('polygon');
          }}
        >
          ☀️ Solar
        </button>
        <button
          style={{ ...styles.tab, ...(activeTab === 'terrain' ? styles.tabActive : {}) }}
          onClick={() => {
            setActiveTab('terrain');
            setDrawingMode('polygon');
          }}
        >
          🗺️ Gelände
        </button>
      </nav>

      {/* Main Content */}
      <div style={styles.mainContent}>
        {/* Map Section */}
        <div style={styles.mapSection}>
          <MapWithDrawing
            sites={wkaSites}
            onSiteAdded={(site) => {
              setWkaSites([...wkaSites, site]);
              setSelectedWKASite(site);
            }}
            onSiteSelected={setSelectedWKASite}
            selectedSite={selectedWKASite}
            drawingMode={getMapDrawingMode()}
            onLineDrawn={(coords) => {
              if (activeTab === 'road') {
                const newRoad: RoadProject = {
                  id: `road_${Date.now()}`,
                  name: `Straße ${roadProjects.length + 1}`,
                  centerline: coords,
                  utmCenterline: [], // Will be filled by RoadForm
                };
                setRoadProjects([...roadProjects, newRoad]);
                setSelectedRoad(newRoad);
              }
            }}
            onPolygonDrawn={(coords) => {
              if (activeTab === 'solar') {
                const newSolar: SolarProject = {
                  id: `solar_${Date.now()}`,
                  name: `Solarpark ${solarProjects.length + 1}`,
                  boundary: coords,
                  utmBoundary: [], // Will be filled by SolarForm
                };
                setSolarProjects([...solarProjects, newSolar]);
                setSelectedSolar(newSolar);
              } else if (activeTab === 'terrain') {
                const newTerrain: TerrainProject = {
                  id: `terrain_${Date.now()}`,
                  name: `Gelände ${terrainProjects.length + 1}`,
                  polygon: coords,
                  utmPolygon: [], // Will be filled by TerrainForm
                };
                setTerrainProjects([...terrainProjects, newTerrain]);
                setSelectedTerrain(newTerrain);
              }
            }}
          />
        </div>

        {/* Form Section */}
        <div style={styles.formSection}>{getTabContent()}</div>
      </div>

      {/* Status Bar */}
      <footer style={styles.footer}>
        <div style={styles.footerContent}>
          {activeTab === 'wka' && (
            <>
              <span>WKA Standorte: {wkaSites.length}</span>
              <span>Berechnet: {wkaSites.filter((s) => s.calculation).length}</span>
            </>
          )}
          {activeTab === 'road' && (
            <>
              <span>Straßen: {roadProjects.length}</span>
              <span>Berechnet: {roadProjects.filter((r) => r.calculation).length}</span>
            </>
          )}
          {activeTab === 'solar' && (
            <>
              <span>Solarparks: {solarProjects.length}</span>
              <span>Berechnet: {solarProjects.filter((s) => s.calculation).length}</span>
            </>
          )}
          {activeTab === 'terrain' && (
            <>
              <span>Geländeanalysen: {terrainProjects.length}</span>
              <span>Analysiert: {terrainProjects.filter((t) => t.analysis).length}</span>
            </>
          )}
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
  logoutButton: {
    padding: '8px 16px',
    fontSize: '14px',
    color: 'white',
    backgroundColor: '#EF4444',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  tabNav: {
    display: 'flex',
    backgroundColor: '#F3F4F6',
    borderBottom: '2px solid #E5E7EB',
    padding: '0 24px',
  },
  tab: {
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '500',
    color: '#6B7280',
    backgroundColor: 'transparent',
    border: 'none',
    borderBottom: '3px solid transparent',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  tabActive: {
    color: '#3B82F6',
    borderBottomColor: '#3B82F6',
    backgroundColor: 'white',
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

export default MultiTabDashboard;
