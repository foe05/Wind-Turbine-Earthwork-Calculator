# 🔧 Development Login Guide

Wenn du **lokal ohne Mailserver** entwickelst, kannst du trotzdem Magic Links nutzen!

## 🚀 3 Methoden zum Login (ohne E-Mail)

---

### ✨ Methode 1: Dev-Login Script (Einfachste)

```bash
cd webapp
./dev-login.sh test@example.com
```

Das Script:
1. ✅ Fordert einen Magic Link an
2. 📋 Holt den Link vom Dev-Endpoint
3. 🌐 Zeigt dir den Link zum Öffnen

**Output:**
```
✨ Your Magic Link:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
http://localhost:3000/login?token=eyJhbGc...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 Open this URL in your browser to login!
```

---

### 📱 Methode 2: Manuell mit API-Calls

#### Schritt 1: Login anfordern

```bash
curl -X POST http://localhost:8000/auth/request-login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

#### Schritt 2: Magic Link holen

```bash
curl -X GET http://localhost:8000/auth/dev/magic-links/test@example.com
```

**Response:**
```json
{
  "email": "test@example.com",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "🔧 Development mode: Copy the URL below",
  "links": [
    {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "url": "http://localhost:3000/login?token=eyJhbGc...",
      "created_at": "2025-11-06T10:30:00",
      "expires_at": "2025-11-06T10:45:00",
      "expires_in_minutes": 14
    }
  ]
}
```

#### Schritt 3: URL im Browser öffnen

Kopiere die `url` aus der Response und öffne sie im Browser.

---

### 🗄️ Methode 3: Direkt aus der Datenbank

Wenn die API nicht läuft, kannst du den Token direkt aus der DB holen:

```bash
# PostgreSQL verbinden
docker exec -it webapp-postgres-1 psql -U windturbine -d windturbine_db

# Magic Links anzeigen
SELECT
    u.email,
    ml.token,
    ml.expires_at,
    ml.used,
    CONCAT('http://localhost:3000/login?token=', ml.token) as magic_link_url
FROM magic_links ml
JOIN users u ON ml.user_id = u.id
WHERE ml.used = false
  AND ml.expires_at > NOW()
ORDER BY ml.created_at DESC
LIMIT 5;
```

---

## 🔐 Sicherheitshinweise

⚠️ Der `/auth/dev/magic-links/{email}` Endpoint ist **nur verfügbar**, wenn:
- `DEBUG=True` in der Konfiguration **ODER**
- `SMTP_HOST` nicht konfiguriert ist

In Production wird dieser Endpoint **automatisch deaktiviert**! 🔒

---

## 🧪 Vollständiger Test-Workflow

```bash
# 1. Services starten
cd webapp
docker-compose up -d

# 2. Warte bis alles läuft (ca. 30 Sekunden)
docker-compose ps

# 3. Login mit Dev-Script
./dev-login.sh test@example.com

# 4. Kopiere den Magic Link und öffne ihn im Browser
# → Du wirst automatisch eingeloggt und zu /dashboard weitergeleitet

# 5. Prüfe ob Login funktioniert hat
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

---

## 🐛 Troubleshooting

### Problem: "This endpoint is only available in development mode"

**Lösung:** Prüfe die `.env` Datei:

```bash
# In webapp/services/auth_service/.env
DEBUG=True

# ODER entferne SMTP Konfiguration:
# SMTP_HOST=   # leer lassen
```

### Problem: "No user found with email"

**Lösung:** Fordere zuerst einen Login an:

```bash
curl -X POST http://localhost:8000/auth/request-login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

Dann nochmal den Dev-Endpoint aufrufen.

### Problem: "No active magic links found"

**Lösung:** Der Token ist abgelaufen (15 Minuten Gültigkeit). Fordere einen neuen an:

```bash
./dev-login.sh test@example.com
```

---

## 📚 API-Dokumentation

Alle Endpoints findest du auch in der interaktiven Swagger-Doku:

**http://localhost:8000/docs**

Such dort nach: **GET /auth/dev/magic-links/{email}**

---

## ✅ Schnell-Referenz

| Aktion | Befehl |
|--------|--------|
| Login anfordern | `./dev-login.sh test@example.com` |
| Magic Links anzeigen | `curl http://localhost:8000/auth/dev/magic-links/test@example.com` |
| Alle Nutzer anzeigen | `docker exec -it webapp-postgres-1 psql -U windturbine -d windturbine_db -c "SELECT * FROM users;"` |
| Services neu starten | `docker-compose restart` |
| Logs ansehen | `docker-compose logs -f auth_service` |

---

Viel Erfolg! 🚀
