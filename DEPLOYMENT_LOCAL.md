# 🚀 Lokales Deployment auf Ubuntu

Schnellanleitung zum Starten der gesamten Geo-Engineering Platform auf localhost.

## 📋 Voraussetzungen

### 1. Docker & Docker Compose installieren

```bash
# Docker installieren
sudo apt update
sudo apt install -y docker.io

# Docker Compose installieren
sudo apt install -y docker-compose

# Aktuellen Benutzer zur docker Gruppe hinzufügen
sudo usermod -aG docker $USER

# Neu einloggen (oder System neu starten)
# Damit docker ohne sudo funktioniert
newgrp docker

# Installation prüfen
docker --version
docker-compose --version
```

### 2. Repository klonen (bereits erledigt ✓)

```bash
cd ~/
git clone https://github.com/foe05/Wind-Turbine-Earthwork-Calculator.git
cd Wind-Turbine-Earthwork-Calculator
```

---

## 🎯 Quick Start (3 Schritte)

### Schritt 1: Environment-Datei erstellen

```bash
cd webapp
cp .env.example .env
```

**Optional**: Email-Konfiguration anpassen (nur für Magic Link Login)

```bash
nano .env
```

Ändere diese Zeilen falls du Email-Login nutzen willst:
```bash
SMTP_USER=deine-email@gmail.com
SMTP_PASSWORD=dein-app-passwort
SMTP_FROM_EMAIL=deine-email@gmail.com
```

> **Hinweis**: Für lokales Testen kannst du die Standard-Werte beibehalten. Email-Login wird dann nicht funktionieren, aber du kannst die Anwendung trotzdem testen.

### Schritt 2: Alle Services starten

```bash
# Im webapp/ Verzeichnis
docker-compose up -d
```

Das baut und startet automatisch:
- ✅ PostgreSQL + PostGIS (Port 5432)
- ✅ Redis (Port 6379)
- ✅ API Gateway (Port 8000)
- ✅ Auth Service (Port 8001)
- ✅ DEM Service (Port 8002)
- ✅ Calculation Service (Port 8003)
- ✅ Cost Service (Port 8004)
- ✅ Report Service (Port 8005)
- ✅ Celery Worker (Background Jobs)
- ✅ Frontend (Port 3000)

**Beim ersten Start** dauert es ~5-10 Minuten, da Docker alle Images bauen muss.

### Schritt 3: Auf die Anwendung zugreifen

**Öffne im Browser:**
```
Frontend:  http://localhost:3000
API Docs:  http://localhost:8000/docs
```

---

## 📊 Container Status prüfen

```bash
# Alle laufenden Container anzeigen
docker-compose ps

# Logs aller Services anzeigen
docker-compose logs -f

# Logs eines bestimmten Services
docker-compose logs -f frontend
docker-compose logs -f api_gateway
```

**Erwartete Ausgabe:**
```
NAME                     STATUS          PORTS
geo_postgres             Up 2 minutes    0.0.0.0:5432->5432/tcp
geo_redis                Up 2 minutes    0.0.0.0:6379->6379/tcp
geo_api_gateway          Up 2 minutes    0.0.0.0:8000->8000/tcp
geo_auth                 Up 2 minutes    0.0.0.0:8001->8001/tcp
geo_dem                  Up 2 minutes    0.0.0.0:8002->8002/tcp
geo_calculation          Up 2 minutes    0.0.0.0:8003->8003/tcp
geo_cost                 Up 2 minutes    0.0.0.0:8004->8004/tcp
geo_report               Up 2 minutes    0.0.0.0:8005->8005/tcp
geo_celery_worker        Up 2 minutes
geo_frontend             Up 2 minutes    0.0.0.0:3000->3000/tcp
```

---

## 🛠️ Nützliche Befehle

### Services verwalten

```bash
# Services stoppen
docker-compose down

# Services stoppen + Volumes löschen (Datenbank wird gelöscht!)
docker-compose down -v

# Services neu starten
docker-compose restart

# Einzelnen Service neu starten
docker-compose restart frontend

# Services neu bauen
docker-compose build

# Services neu bauen und starten
docker-compose up -d --build
```

### Logs ansehen

```bash
# Alle Logs in Echtzeit
docker-compose logs -f

# Nur die letzten 100 Zeilen
docker-compose logs --tail=100

# Logs eines Services
docker-compose logs -f api_gateway
docker-compose logs -f frontend
docker-compose logs -f celery_worker
```

### In einen Container einsteigen

```bash
# Shell in einem Container öffnen
docker-compose exec api_gateway bash
docker-compose exec postgres psql -U admin -d geo_engineering

# Python Shell im API Gateway
docker-compose exec api_gateway python
```

### Datenbank direkt zugreifen

```bash
# PostgreSQL Shell
docker-compose exec postgres psql -U admin -d geo_engineering

# SQL Befehle
\dt              # Alle Tabellen anzeigen
\d projects      # Schema der projects Tabelle
SELECT COUNT(*) FROM users;
SELECT * FROM projects LIMIT 5;
\q               # Beenden
```

---

## 🧪 Testen der Installation

### 1. Backend API testen

```bash
# Health Check
curl http://localhost:8000/

# Service Info
curl http://localhost:8000/services

# API Dokumentation (im Browser)
firefox http://localhost:8000/docs
```

### 2. Frontend testen

```bash
# Im Browser öffnen
firefox http://localhost:3000

# Oder mit curl
curl http://localhost:3000
```

### 3. Services einzeln testen

```bash
# Auth Service
curl http://localhost:8001/

# DEM Service
curl http://localhost:8002/

# Calculation Service
curl http://localhost:8003/

# Cost Service
curl http://localhost:8004/

# Report Service
curl http://localhost:8005/
```

---

## ⚠️ Troubleshooting

### Problem: "Port already in use"

```bash
# Prüfen welcher Prozess den Port belegt
sudo lsof -i :3000
sudo lsof -i :8000

# Prozess beenden
sudo kill -9 <PID>

# Oder anderen Port in docker-compose.yml nutzen
```

### Problem: "Cannot connect to Docker daemon"

```bash
# Docker Service starten
sudo systemctl start docker

# Docker beim Boot automatisch starten
sudo systemctl enable docker

# Benutzer-Rechte prüfen
groups $USER
# Sollte "docker" enthalten

# Falls nicht:
sudo usermod -aG docker $USER
newgrp docker
```

### Problem: Frontend baut nicht / npm Fehler

```bash
# Container neu bauen
docker-compose build frontend

# Frontend Container logs ansehen
docker-compose logs frontend

# In Frontend Container einsteigen und manuell bauen
docker-compose exec frontend bash
npm install
npm run build
```

### Problem: Datenbank startet nicht

```bash
# Postgres Logs prüfen
docker-compose logs postgres

# Volume löschen und neu starten
docker-compose down -v
docker-compose up -d
```

### Problem: Services können sich nicht verbinden

```bash
# Netzwerk prüfen
docker network ls
docker network inspect geo_engineering_network

# DNS im Container testen
docker-compose exec api_gateway ping postgres
docker-compose exec api_gateway curl http://auth_service:8001/
```

### Problem: ENOSPC (zu wenig Speicher)

```bash
# Docker aufräumen
docker system prune -a --volumes

# Speicherplatz prüfen
df -h
```

---

## 🔄 Updates installieren

```bash
# Code aktualisieren
git pull

# Services neu bauen und starten
cd webapp
docker-compose down
docker-compose build
docker-compose up -d

# Datenbank-Migrations prüfen
docker-compose exec api_gateway alembic upgrade head
```

---

## 🗄️ Datenbank-Backup

### Backup erstellen

```bash
# Backup der gesamten Datenbank
docker-compose exec postgres pg_dump -U admin geo_engineering > backup_$(date +%Y%m%d).sql

# Nur Schema (ohne Daten)
docker-compose exec postgres pg_dump -U admin --schema-only geo_engineering > schema.sql

# Nur Daten
docker-compose exec postgres pg_dump -U admin --data-only geo_engineering > data.sql
```

### Backup wiederherstellen

```bash
# Datenbank leeren und Backup einspielen
docker-compose exec -T postgres psql -U admin -d geo_engineering < backup_20250115.sql
```

---

## 📈 Performance-Tuning

### Für Production

```bash
# In docker-compose.yml ändern:

# 1. --reload entfernen bei allen Services
command: uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Mehr Celery Worker
command: celery -A app.worker worker --loglevel=info --concurrency=8

# 3. Redis Memory Limit anpassen
command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru

# 4. Postgres Tuning
environment:
  POSTGRES_SHARED_BUFFERS: 256MB
  POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
```

---

## 🔐 Sicherheit (für Production)

```bash
# 1. Starke Passwörter in .env setzen
JWT_SECRET=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 24)

# 2. HTTPS mit nginx reverse proxy
# 3. Firewall konfigurieren (ufw)
# 4. Secrets nicht in Git committen
```

---

## 📚 Weitere Ressourcen

- **API Dokumentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **Phase 3 Docs**: [../docs/PHASE3_COMPLETE.md](../docs/PHASE3_COMPLETE.md)
- **Project Structure**: [../PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)

---

## ✅ Checkliste

- [ ] Docker & Docker Compose installiert
- [ ] Repository geklont
- [ ] `.env` Datei erstellt
- [ ] `docker-compose up -d` ausgeführt
- [ ] Alle Container laufen (`docker-compose ps`)
- [ ] Frontend erreichbar (http://localhost:3000)
- [ ] API Docs erreichbar (http://localhost:8000/docs)

**Bei Problemen**: Siehe [Troubleshooting](#️-troubleshooting) Sektion oben!

---

**Viel Erfolg! 🚀**
