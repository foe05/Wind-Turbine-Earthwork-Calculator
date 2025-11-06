/**
 * Jobs History - View all calculation jobs
 */

import React, { useState, useEffect } from 'react';
import { JobHistory } from '../types';
import apiClient from '../services/api';
import { useSearchParams, useNavigate } from 'react-router-dom';

const JobsHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectIdFilter = searchParams.get('project');

  const [jobs, setJobs] = useState<JobHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    loadJobs();
  }, [projectIdFilter, statusFilter]);

  const loadJobs = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getJobsHistory(
        projectIdFilter || undefined,
        statusFilter || undefined
      );
      setJobs(data);
    } catch (err) {
      console.error('Error loading jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, React.CSSProperties> = {
      completed: { background: '#10B981', color: 'white' },
      failed: { background: '#EF4444', color: 'white' },
      pending: { background: '#F59E0B', color: 'white' },
      calculating: { background: '#3B82F6', color: 'white' },
    };
    return styles[status] || { background: '#6B7280', color: 'white' };
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('de-DE');
  };

  const handleDelete = async (jobId: string) => {
    if (!window.confirm('Job wirklich löschen?')) return;
    try {
      await apiClient.deleteJob(jobId);
      setJobs(jobs.filter((j) => j.id !== jobId));
    } catch (err) {
      console.error('Error deleting job:', err);
      alert('Fehler beim Löschen');
    }
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
            <button onClick={() => navigate('/projects')} style={styles.navButton}>
              📂 Projekte
            </button>
            <button onClick={() => navigate('/jobs')} style={styles.navButtonActive}>
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

      {/* Page Content */}
      <div style={styles.content}>
        <div style={styles.header}>
          <h1 style={styles.title}>Jobs Historie</h1>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={styles.filterSelect}
          >
            <option value="">Alle Status</option>
            <option value="completed">Abgeschlossen</option>
            <option value="failed">Fehlgeschlagen</option>
            <option value="pending">Ausstehend</option>
            <option value="calculating">In Bearbeitung</option>
          </select>
        </div>

      {loading && <div style={{ textAlign: 'center', padding: '48px' }}>Lade Jobs...</div>}

      {!loading && jobs.length === 0 && (
        <div style={{ textAlign: 'center', padding: '48px', color: '#6B7280' }}>
          Keine Jobs gefunden
        </div>
      )}

      {!loading && jobs.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {jobs.map((job) => (
            <div
              key={job.id}
              style={{
                backgroundColor: 'white',
                padding: '20px',
                borderRadius: '8px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <span
                    style={{
                      ...getStatusBadge(job.status),
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: 'bold',
                    }}
                  >
                    {job.status}
                  </span>
                  <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#1F2937' }}>
                    {job.project_name}
                  </span>
                  {job.site_count && (
                    <span style={{ fontSize: '14px', color: '#6B7280' }}>
                      ({job.site_count} Sites)
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '14px', color: '#6B7280' }}>
                  Erstellt: {formatDate(job.created_at)}
                  {job.completed_at && ` • Abgeschlossen: ${formatDate(job.completed_at)}`}
                </div>
                {job.error_message && (
                  <div style={{ fontSize: '13px', color: '#EF4444', marginTop: '4px' }}>
                    ⚠️ {job.error_message}
                  </div>
                )}
                {job.status !== 'completed' && job.status !== 'failed' && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ width: '100%', height: '8px', backgroundColor: '#E5E7EB', borderRadius: '4px' }}>
                      <div
                        style={{
                          width: `${job.progress}%`,
                          height: '100%',
                          backgroundColor: '#3B82F6',
                          borderRadius: '4px',
                          transition: 'width 0.3s',
                        }}
                      />
                    </div>
                    <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '4px' }}>
                      {job.progress}%
                    </div>
                  </div>
                )}
              </div>
              <button
                onClick={() => handleDelete(job.id)}
                style={{
                  padding: '8px 16px',
                  fontSize: '14px',
                  color: '#EF4444',
                  backgroundColor: 'white',
                  border: '1px solid #EF4444',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                Löschen
              </button>
            </div>
          ))}
        </div>
      )}
      </div>
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
  content: {
    padding: '24px',
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#1F2937',
    margin: 0,
  },
  filterSelect: {
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid #D1D5DB',
    borderRadius: '6px',
    backgroundColor: 'white',
    cursor: 'pointer',
  },
};

export default JobsHistoryPage;
