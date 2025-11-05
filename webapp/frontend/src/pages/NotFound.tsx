/**
 * 404 Not Found Page
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={styles.container}>
      <div style={styles.content}>
        <div style={styles.errorCode}>404</div>
        <h1 style={styles.title}>Seite nicht gefunden</h1>
        <p style={styles.message}>
          Die von Ihnen gesuchte Seite existiert nicht oder wurde verschoben.
        </p>
        <div style={styles.buttonGroup}>
          <button onClick={() => navigate('/projects')} style={styles.primaryButton}>
            Zurück zur Startseite
          </button>
          <button onClick={() => navigate(-1)} style={styles.secondaryButton}>
            Zurück
          </button>
        </div>

        {/* Helpful Links */}
        <div style={styles.links}>
          <h3 style={styles.linksTitle}>Hilfreiche Links:</h3>
          <ul style={styles.linksList}>
            <li>
              <button onClick={() => navigate('/projects')} style={styles.link}>
                📂 Meine Projekte
              </button>
            </li>
            <li>
              <button onClick={() => navigate('/jobs')} style={styles.link}>
                📊 Jobs Historie
              </button>
            </li>
            <li>
              <button onClick={() => navigate('/dashboard')} style={styles.link}>
                🏗️ Rechner
              </button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    backgroundColor: '#F9FAFB',
    padding: '24px',
  },
  content: {
    textAlign: 'center' as const,
    maxWidth: '600px',
  },
  errorCode: {
    fontSize: '120px',
    fontWeight: 'bold',
    color: '#E5E7EB',
    lineHeight: '1',
    marginBottom: '24px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: '16px',
  },
  message: {
    fontSize: '18px',
    color: '#6B7280',
    marginBottom: '32px',
    lineHeight: '1.6',
  },
  buttonGroup: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    marginBottom: '48px',
  },
  primaryButton: {
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    color: 'white',
    backgroundColor: '#3B82F6',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  secondaryButton: {
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    color: '#3B82F6',
    backgroundColor: 'white',
    border: '2px solid #3B82F6',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  links: {
    marginTop: '48px',
    textAlign: 'left' as const,
    backgroundColor: 'white',
    padding: '24px',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  linksTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: '16px',
  },
  linksList: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  link: {
    display: 'block',
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    color: '#3B82F6',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    textAlign: 'left' as const,
    transition: 'background-color 0.2s',
    marginBottom: '8px',
  },
};

export default NotFound;
