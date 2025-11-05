/**
 * Projects Overview - Dashboard for all user projects
 */

import React, { useState, useEffect } from 'react';
import { Project } from '../types';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';

const ProjectsOverview: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterUseCase, setFilterUseCase] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    loadProjects();
  }, [filterUseCase]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const data = await apiClient.listProjects(filterUseCase || undefined);
      setProjects(data);
      setError(null);
    } catch (err: any) {
      console.error('Error loading projects:', err);
      setError(err.response?.data?.detail || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProject = async (projectId: string, projectName: string) => {
    if (!window.confirm(`Möchten Sie das Projekt "${projectName}" wirklich löschen?\n\nAlle zugehörigen Jobs werden ebenfalls gelöscht.`)) {
      return;
    }

    try {
      await apiClient.deleteProject(projectId);
      setProjects(projects.filter((p) => p.id !== projectId));
    } catch (err: any) {
      console.error('Error deleting project:', err);
      alert(`Fehler beim Löschen: ${err.response?.data?.detail || err.message}`);
    }
  };

  const getUseCaseLabel = (useCase: string) => {
    const labels: Record<string, string> = {
      wka: '🌬️ WKA',
      road: '🛣️ Straße',
      solar: '☀️ Solar',
      terrain: '🗺️ Gelände',
    };
    return labels[useCase] || useCase;
  };

  const getUseCaseColor = (useCase: string) => {
    const colors: Record<string, string> = {
      wka: '#E74C3C',
      road: '#E67E22',
      solar: '#F39C12',
      terrain: '#16A085',
    };
    return colors[useCase] || '#95A5A6';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  const handleLogout = async () => {
    await apiClient.logout();
    window.location.href = '/login';
  };

  return (
    <div style={styles.container}>
      {/* Top Navigation Bar */}
      <header style={styles.topNav}>
        <div style={styles.topNavLeft}>
          <h1 style={styles.topNavTitle}>Geo-Engineering Platform</h1>
        </div>
        <div style={styles.topNavRight}>
          <nav style={styles.navButtons}>
            <button onClick={() => navigate('/projects')} style={styles.navButtonActive}>
              📂 Projekte
            </button>
            <button onClick={() => navigate('/jobs')} style={styles.navButton}>
              📊 Jobs
            </button>
            <button onClick={() => navigate('/dashboard')} style={styles.navButton}>
              🏗️ Rechner
            </button>
          </nav>
          <button onClick={handleLogout} style={styles.logoutButton}>
            Abmelden
          </button>
        </div>
      </header>

      {/* Page Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Meine Projekte</h1>
          <p style={styles.subtitle}>{projects.length} Projekt{projects.length !== 1 ? 'e' : ''}</p>
        </div>
        <div style={styles.headerActions}>
          <select
            value={filterUseCase}
            onChange={(e) => setFilterUseCase(e.target.value)}
            style={styles.filterSelect}
          >
            <option value="">Alle Use Cases</option>
            <option value="wka">WKA</option>
            <option value="road">Straße</option>
            <option value="solar">Solar</option>
            <option value="terrain">Gelände</option>
          </select>
          <button onClick={() => navigate('/dashboard')} style={styles.createButton}>
            + Neues Projekt
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={styles.error}>
          ⚠️ {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p>Lade Projekte...</p>
        </div>
      )}

      {/* Projects Grid */}
      {!loading && projects.length === 0 && (
        <div style={styles.empty}>
          <p style={styles.emptyIcon}>📂</p>
          <p style={styles.emptyText}>
            {filterUseCase ? 'Keine Projekte für diesen Use Case gefunden' : 'Keine Projekte vorhanden'}
          </p>
          <button onClick={() => navigate('/dashboard')} style={styles.emptyButton}>
            Erstes Projekt erstellen
          </button>
        </div>
      )}

      {!loading && projects.length > 0 && (
        <div style={styles.grid}>
          {projects.map((project) => (
            <div key={project.id} style={styles.card}>
              <div style={styles.cardHeader}>
                <div style={{ ...styles.useCaseBadge, background: getUseCaseColor(project.use_case) }}>
                  {getUseCaseLabel(project.use_case)}
                </div>
                <button
                  onClick={() => handleDeleteProject(project.id, project.name)}
                  style={styles.deleteButton}
                  title="Projekt löschen"
                >
                  🗑️
                </button>
              </div>

              <div style={styles.cardBody}>
                <h3 style={styles.projectName}>{project.name}</h3>
                {project.description && (
                  <p style={styles.projectDescription}>{project.description}</p>
                )}

                <div style={styles.stats}>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Jobs:</span>
                    <span style={styles.statValue}>{project.job_count || 0}</span>
                  </div>
                  <div style={styles.statItem}>
                    <span style={styles.statLabel}>Abgeschlossen:</span>
                    <span style={styles.statValue}>{project.completed_jobs || 0}</span>
                  </div>
                </div>

                <div style={styles.meta}>
                  <div style={styles.metaItem}>
                    <span style={styles.metaLabel}>CRS:</span>
                    <span style={styles.metaValue}>{project.crs}</span>
                  </div>
                  <div style={styles.metaItem}>
                    <span style={styles.metaLabel}>Erstellt:</span>
                    <span style={styles.metaValue}>{formatDate(project.created_at)}</span>
                  </div>
                  {project.last_calculation && (
                    <div style={styles.metaItem}>
                      <span style={styles.metaLabel}>Letzte Berechnung:</span>
                      <span style={styles.metaValue}>{formatDate(project.last_calculation)}</span>
                    </div>
                  )}
                </div>
              </div>

              <div style={styles.cardFooter}>
                <button
                  onClick={() => navigate(`/dashboard?project=${project.id}`)}
                  style={styles.openButton}
                >
                  Öffnen →
                </button>
                <button
                  onClick={() => navigate(`/jobs?project=${project.id}`)}
                  style={styles.jobsButton}
                >
                  Jobs anzeigen
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    minHeight: '100vh',
    backgroundColor: '#F9FAFB',
  },
  topNav: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    backgroundColor: '#1F2937',
    color: 'white',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  topNavLeft: {
    display: 'flex',
    alignItems: 'center',
  },
  topNavTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 'bold',
  },
  topNavRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  navButtons: {
    display: 'flex',
    gap: '8px',
  },
  navButton: {
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: '500',
    color: 'white',
    backgroundColor: '#374151',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  navButtonActive: {
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: '500',
    color: 'white',
    backgroundColor: '#3B82F6',
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
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '24px',
    maxWidth: '1400px',
    margin: '0 auto',
    width: '100%',
    marginBottom: '8px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#1F2937',
    margin: 0,
  },
  subtitle: {
    fontSize: '16px',
    color: '#6B7280',
    marginTop: '4px',
  },
  headerActions: {
    display: 'flex',
    gap: '12px',
  },
  filterSelect: {
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid #D1D5DB',
    borderRadius: '6px',
    backgroundColor: 'white',
    cursor: 'pointer',
  },
  createButton: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: '#10B981',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  error: {
    padding: '16px',
    backgroundColor: '#FEE2E2',
    color: '#991B1B',
    borderRadius: '6px',
    margin: '0 24px 24px',
    maxWidth: '1400px',
    alignSelf: 'center',
    width: '100%',
  },
  loading: {
    textAlign: 'center' as const,
    padding: '64px 24px',
    color: '#6B7280',
    maxWidth: '1400px',
    margin: '0 auto',
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
  empty: {
    textAlign: 'center' as const,
    padding: '64px 24px',
  },
  emptyIcon: {
    fontSize: '64px',
    margin: '0 0 16px',
  },
  emptyText: {
    fontSize: '18px',
    color: '#6B7280',
    marginBottom: '24px',
  },
  emptyButton: {
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: '#10B981',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
    gap: '24px',
    padding: '0 24px 24px',
    maxWidth: '1400px',
    margin: '0 auto',
    width: '100%',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '10px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    overflow: 'hidden',
    transition: 'transform 0.2s, box-shadow 0.2s',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px',
    backgroundColor: '#F9FAFB',
    borderBottom: '1px solid #E5E7EB',
  },
  useCaseBadge: {
    padding: '4px 12px',
    fontSize: '14px',
    fontWeight: 'bold',
    color: 'white',
    borderRadius: '12px',
  },
  deleteButton: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    cursor: 'pointer',
    opacity: 0.6,
  },
  cardBody: {
    padding: '20px',
  },
  projectName: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#1F2937',
    margin: '0 0 8px',
  },
  projectDescription: {
    fontSize: '14px',
    color: '#6B7280',
    marginBottom: '16px',
  },
  stats: {
    display: 'flex',
    gap: '20px',
    marginBottom: '16px',
    paddingBottom: '16px',
    borderBottom: '1px solid #E5E7EB',
  },
  statItem: {
    flex: 1,
  },
  statLabel: {
    fontSize: '12px',
    color: '#6B7280',
    display: 'block',
    marginBottom: '4px',
  },
  statValue: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#1F2937',
  },
  meta: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  },
  metaItem: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '13px',
  },
  metaLabel: {
    color: '#6B7280',
  },
  metaValue: {
    color: '#1F2937',
    fontWeight: '500',
  },
  cardFooter: {
    display: 'flex',
    gap: '8px',
    padding: '16px',
    backgroundColor: '#F9FAFB',
    borderTop: '1px solid #E5E7EB',
  },
  openButton: {
    flex: 1,
    padding: '10px',
    fontSize: '14px',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: '#3B82F6',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  jobsButton: {
    flex: 1,
    padding: '10px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#3B82F6',
    backgroundColor: 'white',
    border: '1px solid #3B82F6',
    borderRadius: '6px',
    cursor: 'pointer',
  },
};

export default ProjectsOverview;
