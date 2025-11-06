/**
 * Login Page - Magic Link Authentication
 */

import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import apiClient from '../services/api';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Prevent double verification (React 18 StrictMode calls useEffect twice)
  const verificationAttempted = useRef(false);

  // Check for verification token in URL
  useEffect(() => {
    const token = searchParams.get('token');
    if (token && !verificationAttempted.current) {
      verificationAttempted.current = true;
      verifyToken(token);
    }
  }, [searchParams]);

  const verifyToken = async (token: string) => {
    setIsLoading(true);
    try {
      await apiClient.verifyToken(token);
      setMessage({ type: 'success', text: 'Anmeldung erfolgreich! Weiterleitung...' });
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Token ungültig oder abgelaufen',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      setMessage({ type: 'error', text: 'Bitte geben Sie eine E-Mail-Adresse ein' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      await apiClient.requestLogin(email);
      setMessage({
        type: 'success',
        text: 'Magic Link wurde an Ihre E-Mail-Adresse gesendet. Bitte überprüfen Sie Ihr Postfach.',
      });
      setEmail('');
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Anmeldung fehlgeschlagen',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Geo-Engineering Platform</h1>
        <p style={styles.subtitle}>Windkraftanlagen Erdarbeiten Berechnung</p>
        <p style={styles.welcomeText}>
          🌟 <strong>Neu hier?</strong> Geben Sie einfach Ihre E-Mail ein - Ihr Account wird automatisch erstellt!
        </p>

        {message && (
          <div
            style={{
              ...styles.message,
              ...(message.type === 'error' ? styles.messageError : styles.messageSuccess),
            }}
          >
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formGroup}>
            <label htmlFor="email" style={styles.label}>
              E-Mail-Adresse
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ihre@email.de"
              style={styles.input}
              disabled={isLoading}
            />
          </div>

          <button type="submit" style={styles.button} disabled={isLoading}>
            {isLoading ? 'Wird gesendet...' : 'Magic Link senden'}
          </button>
        </form>

        <div style={styles.info}>
          <h3 style={styles.infoTitle}>Wie funktioniert es?</h3>
          <ol style={styles.infoList}>
            <li>Geben Sie Ihre E-Mail-Adresse ein (neu oder bestehend)</li>
            <li>Klicken Sie auf "Magic Link senden"</li>
            <li>Überprüfen Sie Ihr Postfach auf den Anmelde-Link</li>
            <li>Klicken Sie auf den Link, um sich anzumelden</li>
          </ol>
          <p style={styles.infoNote}>
            ℹ️ Bei neuen E-Mail-Adressen wird automatisch ein Account erstellt - kein separates Registrierungsformular notwendig!
          </p>
        </div>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#F3F4F6',
    padding: '20px',
  },
  card: {
    width: '100%',
    maxWidth: '480px',
    padding: '40px',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#1F2937',
    textAlign: 'center' as const,
  },
  subtitle: {
    margin: '0 0 12px 0',
    fontSize: '14px',
    color: '#6B7280',
    textAlign: 'center' as const,
  },
  welcomeText: {
    margin: '0 0 24px 0',
    padding: '12px 16px',
    fontSize: '14px',
    color: '#1F2937',
    textAlign: 'center' as const,
    backgroundColor: '#EFF6FF',
    border: '1px solid #BFDBFE',
    borderRadius: '8px',
    lineHeight: '1.5',
  },
  message: {
    padding: '12px',
    marginBottom: '20px',
    borderRadius: '6px',
    fontSize: '14px',
  },
  messageSuccess: {
    backgroundColor: '#D1FAE5',
    color: '#065F46',
    border: '1px solid #10B981',
  },
  messageError: {
    backgroundColor: '#FEE2E2',
    color: '#991B1B',
    border: '1px solid #EF4444',
  },
  form: {
    marginBottom: '32px',
  },
  formGroup: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#374151',
  },
  input: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    border: '1px solid #D1D5DB',
    borderRadius: '6px',
    boxSizing: 'border-box' as const,
  },
  button: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: '#3B82F6',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  info: {
    padding: '20px',
    backgroundColor: '#F9FAFB',
    borderRadius: '6px',
  },
  infoTitle: {
    margin: '0 0 12px 0',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#374151',
  },
  infoList: {
    margin: '0 0 12px 0',
    paddingLeft: '20px',
    fontSize: '14px',
    color: '#6B7280',
    lineHeight: '1.6',
  },
  infoNote: {
    margin: '0',
    fontSize: '13px',
    color: '#059669',
    fontWeight: '500',
    lineHeight: '1.5',
  },
};

export default Login;
