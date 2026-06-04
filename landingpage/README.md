# Kubatur Landing Page

Statische Single-Page-Landingpage für **Kubatur** (https://kubatur.app).

## Stack

- Reines HTML + Tailwind CSS via CDN
- Inter via Google Fonts
- Kein Build-Step, keine npm-Dependency
- Dark Mode mit Persistenz via `localStorage`

## Lokale Vorschau

```bash
# Im landingpage/-Ordner
python3 -m http.server 8000
# dann http://localhost:8000 öffnen
```

Oder einfach `index.html` mit dem Browser öffnen — funktioniert auch ohne Server.

## Deployment

Drei einfache Wege auf dieser VM:

### Option A — direkt durch NPM (kein extra Container)

Im NPM-UI einen Proxy Host `kubatur.app` anlegen, Custom-Locations-Tab,
Type `serve`, Pfad zur Datei. Oder einen Nginx-Container hochziehen, der
das `landingpage/`-Verzeichnis served.

### Option B — kleiner statischer nginx-Container

`docker-compose.yml`-Snippet für den proxy-Stack:

```yaml
services:
  kubatur-landing:
    image: nginx:alpine
    container_name: kubatur-landing
    restart: unless-stopped
    networks: [proxy]
    volumes:
      - ./landingpage:/usr/share/nginx/html:ro

networks:
  proxy:
    name: docker-apps_proxy
    external: true
```

In NPM dann Proxy Host für `kubatur.app` → `kubatur-landing:80`.

### Option C — GitHub Pages

Im Repository-Settings GitHub Pages aktivieren, Source = `v3-foundation` Branch,
Pfad `/landingpage`. Custom Domain auf `kubatur.app` setzen. CNAME-Datei
nicht vergessen.

## Tailwind via CDN

In Produktion idealerweise auf einen Build-Tailwind wechseln (Lighthouse-
Score-Impact ist marginal, aber CDN-Risiko vermeiden). Für die Pilot-Phase
reicht der CDN-Stand.

## Anpassen

- **Brand-Name** → Find/Replace "Kubatur" und "kubatur.app"
- **Pilot-Adresse** → Find/Replace `pilot@kubatur.app`
- **Akzentfarbe** → im `<script>` mit `tailwind.config` den `accent` ändern
- **Domain Live-Link** → `https://v1.kubatur.app` in Hero und Footer

## Inhalte

Alle Texte sind hart im HTML — keine CMS-Integration. Bei Änderungen
direkt im `index.html` editieren und neu deployen.
