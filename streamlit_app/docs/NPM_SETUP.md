# NPM-Setup für `v1.kubatur.app`

Anleitung zum Veröffentlichen der WTEC-Streamlit-App hinter dem bereits laufenden
`nginx-proxy-manager` (NPM) auf der VM `91.99.188.249`.

Ausgangslage: der App-Container `wtec-app` hängt im Docker-Netzwerk
`docker-apps_proxy` (siehe `docker-compose.prod.yml`, Commit `89dfbaa`) und ist
ausschließlich intern über `http://wtec-app:8501` erreichbar — kein Public-Port
mehr.

---

## 1. DNS (vor allem anderen)

A-Record bei deinem Registrar für `kubatur.app`:

```
v1.kubatur.app   A   91.99.188.249
```

Ohne DNS scheitert die Let's-Encrypt-Challenge weiter unten. Prüfen mit:

```bash
dig v1.kubatur.app +short
# erwartet: 91.99.188.249
```

Erst weiter, wenn das stimmt.

---

## 2. NPM-UI: Proxy Host anlegen

NPM-UI auf `http://91.99.188.249:8080` öffnen.
**Hosts → Proxy Hosts → Add Proxy Host**

| Tab | Feld | Wert |
|---|---|---|
| Details | Domain Names | `v1.kubatur.app` |
| Details | Scheme | `http` |
| Details | Forward Hostname / IP | `wtec-app` |
| Details | Forward Port | `8501` |
| Details | Cache Assets | aus |
| Details | Block Common Exploits | ein |
| Details | **Websockets Support** | **ein** (Pflicht für Streamlit-Reruns) |
| SSL | SSL Certificate | *Request a new SSL Certificate* |
| SSL | Force SSL | ein |
| SSL | HTTP/2 Support | ein |
| SSL | HSTS Enabled | ein |
| SSL | I Agree to LE ToS | ✓ |
| SSL | Email | deine Adresse |

**Save** → NPM zieht in ~10 s ein Let's-Encrypt-Cert.

---

## 3. Tab „Advanced" — Streamlit-spezifische Nginx-Knöpfe

DEM-Download + Cut/Fill-Calc + Profile + Report können je nach BBox 2–5 Minuten
dauern. NPM-Default-Timeouts (60 s) killen die WebSocket-Verbindung mittendrin.
Im **Advanced**-Tab des Proxy-Hosts dieses Snippet reinkippen:

```nginx
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
proxy_connect_timeout 60s;
proxy_buffering off;

# Upload-Größe für DXFs erlauben (Default ist 1 MB)
client_max_body_size 600m;

# Streamlit WebSocket-Frame-Forwarding
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Real-IP $remote_addr;
```

Die ersten beiden Zeilen sind das Wichtigste, damit lange Berechnungen nicht
reißen. `client_max_body_size 600m` matched die Streamlit-Upload-Größe (im base
compose ist `STREAMLIT_SERVER_MAX_UPLOAD_SIZE: 512`).

---

## 4. Hetzner-Cloud-Firewall

Port **8501** kannst du jetzt schließen (oder gar nicht erst öffnen) — der
Public-Port ist weg, der Container ist nur noch intern erreichbar.

Offen bleiben müssen:

- **80** (für die Let's-Encrypt-HTTP-Challenge)
- **443** (NPM-Traffic)

---

## 5. Sanity-Check nach Save

```bash
# Aus jedem Browser:
curl -sI https://v1.kubatur.app | head -3
# erwartet: HTTP/2 200, server: openresty
```

Aufrufbar dann unter <https://v1.kubatur.app>.

### Wenn 502/504

```bash
docker logs nginx-proxy-manager --tail 30
docker logs wtec-app --tail 30
```

Häufige Ursachen:

1. **Websocket-Toggle aus** → Proxy-Host editieren, Websockets-Support einschalten.
2. **LE-Cert noch nicht durch** → DNS prüfen, NPM-Audit-Log anschauen.
3. **wtec-app nicht im Proxy-Netz** → `docker inspect wtec-app --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'` muss `docker-apps_proxy` enthalten.

---

## 6. Was bewusst NICHT konfiguriert ist

- **Authelia** läuft (Stand 2026-06-04) nicht auf der VM. Solange das so ist:
  in NPM eine **Access List** (Basic Auth) am Proxy-Host hinterlegen — reicht
  für Pilot-Kunden. Wenn Authelia nachgezogen wird, kommt eine Forward-Auth-
  Direktive in den Advanced-Tab.
- **Streamlit-Telemetrie, XSRF, CORS** sind im Container abgeschaltet
  (`STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`,
  `STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false`,
  `STREAMLIT_SERVER_ENABLE_CORS=false`), weil XSRF/CORS-Origin-Checks hinter
  einem Reverse Proxy oft falsch schließen. Wenn das wieder eingeschaltet
  werden soll: in `docker-compose.prod.yml` die env-Variablen entfernen.

---

## 7. Kommando-Cheat-Sheet

```bash
# App + DB neu starten (nach Code-Edit reicht oft nur restart wtec-app)
cd /home/claude-dev/projects/Wind-Turbine-Earthwork-Calculator/streamlit_app
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Nur App neu starten (Code ist als ro-Volume gemountet)
docker restart wtec-app

# Logs live mitlesen
docker logs -f wtec-app

# Container in den NPM-Netz-Check
docker exec nginx-proxy-manager curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  http://wtec-app:8501/_stcore/health
# erwartet: HTTP 200

# Stoppen
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```
