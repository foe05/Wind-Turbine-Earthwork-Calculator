# Beitragen zum Wind Turbine Earthwork Calculator

Vielen Dank für dein Interesse, zum **Wind Turbine Earthwork Calculator** beizutragen! 🎉

Dieses Dokument enthält Richtlinien und Informationen für Contributors.

---

## 📋 Inhaltsverzeichnis

- [Code of Conduct](#code-of-conduct)
- [Wie kann ich beitragen?](#wie-kann-ich-beitragen)
- [Entwicklungs-Setup](#entwicklungs-setup)
- [Code-Richtlinien](#code-richtlinien)
- [Commit-Nachrichten](#commit-nachrichten)
- [Pull Request Prozess](#pull-request-prozess)
- [Bug Reports](#bug-reports)
- [Feature Requests](#feature-requests)

---

## Code of Conduct

### Unsere Verpflichtung

Wir verpflichten uns, eine offene und einladende Umgebung zu schaffen. Wir tolerieren keine Form von Belästigung oder diskriminierendem Verhalten.

### Unsere Standards

**Positives Verhalten**:
- ✅ Respektvolle und inklusive Sprache
- ✅ Konstruktives Feedback
- ✅ Fokus auf das Beste für die Community
- ✅ Empathie gegenüber anderen Community-Mitgliedern

**Inakzeptables Verhalten**:
- ❌ Beleidigende Kommentare oder persönliche Angriffe
- ❌ Trolling, absichtlich provokante Kommentare
- ❌ Veröffentlichung privater Informationen ohne Erlaubnis
- ❌ Anderes unprofessionelles Verhalten

---

## Wie kann ich beitragen?

### 🐛 Bug Reports

Bugs werden als [GitHub Issues](https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator/issues) gemeldet.

**Bevor du einen Bug meldest**:
1. **Durchsuche existierende Issues**, um Duplikate zu vermeiden
2. **Prüfe die Dokumentation**, ob das Verhalten erwartet ist
3. **Teste mit der neuesten Version**

**Ein guter Bug Report enthält**:
- **Titel**: Kurze, prägnante Beschreibung
- **Umgebung**: QGIS-Version, Betriebssystem, Python-Version
- **Reproduktionsschritte**: Detaillierte Anleitung, wie der Fehler auftritt
- **Erwartetes Verhalten**: Was sollte passieren?
- **Tatsächliches Verhalten**: Was passiert stattdessen?
- **Screenshots**: Falls visuell relevant
- **Logs**: QGIS-Console-Output oder Fehlermeldungen

**Template**:
```markdown
**Umgebung**:
- QGIS: 3.34.4
- OS: Ubuntu 24.04
- Python: 3.12.2

**Reproduktionsschritte**:
1. Tool öffnen
2. DEM laden: `test_dem.tif`
3. Parameter setzen: Plattformlänge = 45m
4. Run klicken

**Erwartetes Verhalten**: Berechnung läuft ohne Fehler

**Tatsächliches Verhalten**: 
```
AttributeError: 'NoneType' object has no attribute 'get'
```

**Logs**:
[Logs einfügen oder als Datei anhängen]
```

---

### 💡 Feature Requests

Feature Requests sind willkommen! Bitte erstelle ein [GitHub Issue](https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator/issues) mit dem Label `enhancement`.

**Ein guter Feature Request enthält**:
- **Problem**: Welches Problem löst das Feature?
- **Lösung**: Wie könnte das Feature aussehen?
- **Alternativen**: Welche anderen Lösungen hast du in Betracht gezogen?
- **Use Case**: Wer würde davon profitieren und warum?

**Template**:
```markdown
**Problem**:
Als Nutzer möchte ich [Ziel], damit [Nutzen].

**Vorgeschlagene Lösung**:
[Beschreibung der Lösung]

**Alternativen**:
[Andere Ansätze, die du erwogen hast]

**Zusätzlicher Kontext**:
[Screenshots, Mockups, Links zu ähnlichen Features in anderen Tools]
```

---

### 🔧 Code Contributions

#### Entwicklungs-Setup

1. **Repository forken**:
   ```bash
   # Auf GitHub: Fork-Button klicken
   git clone https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator.git
   cd Wind-Turbine-Earthwork-Calculator
   ```

2. **Branch erstellen**:
   ```bash
   git checkout -b feature/mein-neues-feature
   # oder
   git checkout -b bugfix/fehler-beschreibung
   ```

3. **QGIS-Entwicklungsumgebung**:
   ```bash
   # Script nach QGIS kopieren
   cp prototype/prototype.py ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/
   
   # QGIS starten
   qgis
   ```

4. **Änderungen machen**:
   - Siehe [AGENTS.md](AGENTS.md) für Code-Konventionen
   - Tests schreiben (falls vorhanden)
   - Dokumentation aktualisieren

5. **Testen**:
   - Manueller Test in QGIS
   - Mit verschiedenen Parametern testen
   - Edge Cases prüfen (z.B. leere Inputs, extreme Werte)

6. **Commit & Push**:
   ```bash
   git add .
   git commit -m "feat: neue Funktion XYZ hinzugefügt"
   git push origin feature/mein-neues-feature
   ```

7. **Pull Request erstellen**:
   - Auf GitHub zum Fork navigieren
   - "New Pull Request" klicken
   - Template ausfüllen (siehe unten)

---

## Code-Richtlinien

### Python-Stil

Wir folgen **PEP 8** mit QGIS-spezifischen Anpassungen (siehe [AGENTS.md](AGENTS.md)).

**Wichtigste Regeln**:
```python
# ✅ GUT
def _calculate_foundation(self, diameter, depth, foundation_type):
    """Berechnet Fundament-Volumen
    
    Args:
        diameter: Durchmesser in Metern
        depth: Tiefe in Metern
        foundation_type: 0=Flach, 1=Tief, 2=Pfahl
    
    Returns:
        Dict mit 'volume', 'diameter', 'depth', 'type'
    """
    radius = diameter / 2.0
    volume = math.pi * radius**2 * depth
    return {'volume': volume, 'diameter': diameter, 'depth': depth}

# ❌ SCHLECHT
def calc_found(d,dp,t):
    r=d/2
    v=3.14*r*r*dp
    return v
```

**Naming Conventions**:
- Klassen: `CamelCase` (z.B. `WindTurbineEarthworkCalculatorV3`)
- Methoden: `snake_case` (z.B. `_calculate_foundation()`)
- Konstanten: `UPPER_SNAKE_CASE` (z.B. `INPUT_DEM`, `MAX_SLOPE`)
- Private Methoden: `_prefix` (z.B. `_sample_dem_grid()`)

### Docstrings

Alle öffentlichen Methoden brauchen Docstrings:

```python
def _calculate_costs(self, foundation_volume, crane_cut, ...):
    """
    Berechnet detaillierte Kosten für Erdarbeiten
    
    Args:
        foundation_volume: Fundament-Aushubvolumen (m³)
        crane_cut: Kranflächen-Aushub (m³)
        material_balance: Dict mit Material-Bilanz
        ...
    
    Returns:
        Dict mit Kosten-Komponenten:
        - cost_total: Gesamt-Kosten (€)
        - cost_excavation: Aushub-Kosten (€)
        - cost_saving: Einsparung (€)
        ...
        
    Raises:
        ValueError: Wenn foundation_volume < 0
        
    Example:
        >>> result = self._calculate_costs(1000, 500, ...)
        >>> print(result['cost_total'])
        45678.50
    """
```

### HTML-Report

**Wichtig**: Immer F-Strings verwenden!

```python
# ✅ RICHTIG
html += f"""
<td>{variable_name}</td>
<td>{calculation_result:.2f}</td>
"""

# ❌ FALSCH (wird nicht interpoliert)
html += """
<td>{variable_name}</td>
"""
```

### Error Handling

```python
# ✅ Spezifische Exceptions
if dem_layer is None:
    raise QgsProcessingException('DEM konnte nicht geladen werden!')

# ✅ Safe-Konvertierung
def safe_get(key, default=0.0):
    value = result.get(key, default)
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
```

---

## Commit-Nachrichten

Wir verwenden [Conventional Commits](https://www.conventionalcommits.org/):

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: Neue Funktion
- `fix`: Bugfix
- `docs`: Dokumentations-Änderungen
- `style`: Code-Formatierung (keine Logik-Änderung)
- `refactor`: Code-Umstrukturierung
- `test`: Tests hinzufügen/ändern
- `chore`: Build-Prozess, Dependencies, etc.

**Beispiele**:
```bash
# Feature
git commit -m "feat(costs): add gravel layer thickness parameter"

# Bugfix
git commit -m "fix(polygon): safe conversion for cost_total attribute"

# Dokumentation
git commit -m "docs(readme): update installation instructions for QGIS 3.34"

# Refactoring
git commit -m "refactor(dem): extract sampling logic into separate method"

# Mit Body
git commit -m "feat(optimization): add rotation-based platform optimization

Implements auto-rotation algorithm that tests 24 different angles
and selects the one with minimal cut/fill imbalance.

Closes #42"
```

---

## Pull Request Prozess

### 1. Vor dem PR

- [ ] Code folgt den Style-Guidelines
- [ ] Alle Tests laufen durch (manuell in QGIS)
- [ ] Dokumentation aktualisiert (README, AGENTS.md, etc.)
- [ ] CHANGELOG.md aktualisiert (unter `[Unveröffentlicht]`)
- [ ] Keine Debug-Statements oder Kommentare (`print()`, `# TODO`)

### 2. PR erstellen

**Titel**: Kurz und prägnant
```
feat: Add rotation-based platform optimization
fix: Resolve attribute conversion error for polygons
docs: Update installation guide for Windows
```

**Beschreibung** (Template):
```markdown
## Beschreibung
[Was ändert dieser PR?]

## Motivation
[Warum ist diese Änderung nötig?]

## Änderungen
- [Liste der Änderungen]
- [Punkt 2]

## Screenshots
[Falls visuell relevant]

## Tests
- [ ] Manuell in QGIS getestet
- [ ] Mit verschiedenen Parametern getestet
- [ ] Edge Cases geprüft

## Checklist
- [ ] Code folgt Style-Guidelines
- [ ] Dokumentation aktualisiert
- [ ] CHANGELOG.md aktualisiert
- [ ] Keine Breaking Changes (oder dokumentiert)

## Related Issues
Closes #123
```

### 3. Review-Prozess

1. **Automatische Checks**: CI/CD läuft (falls konfiguriert)
2. **Code Review**: Maintainer prüft Code
3. **Feedback**: Änderungen werden diskutiert
4. **Anpassungen**: Du implementierst Feedback
5. **Approval**: Maintainer genehmigt PR
6. **Merge**: PR wird in `main` gemerged

### 4. Nach dem Merge

- Branch kann gelöscht werden
- Release wird vorbereitet (bei größeren Features)
- Danke für deinen Beitrag! 🎉

---

## Bug Reports

### Severity Levels

- **Critical**: Tool ist komplett unbenutzbar
- **High**: Wichtige Funktionalität betroffen, aber Workaround existiert
- **Medium**: Feature funktioniert nicht korrekt, aber nicht kritisch
- **Low**: Kleinere Probleme, UI-Inkonsistenzen

### Labels

- `bug`: Fehler im Code
- `enhancement`: Neue Funktion
- `documentation`: Dokumentations-Problem
- `good first issue`: Gut für Einsteiger
- `help wanted`: Hilfe erwünscht
- `question`: Frage zur Nutzung

---

## Feature Requests

### Prioritäten

**High Priority**:
- Behebt häufig auftretende User-Probleme
- Erhöht Benutzerfreundlichkeit erheblich
- Wird von vielen Nutzern benötigt

**Medium Priority**:
- Nützlich, aber nicht kritisch
- Betrifft spezifische Use Cases
- Nice-to-have Features

**Low Priority**:
- Randfall-Szenarien
- Kosmetische Verbesserungen
- Features mit sehr wenigen Nutzern

---

## Fragen?

- **Issues**: [GitHub Issues](https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator/issues)
- **Diskussionen**: [GitHub Discussions](https://github.com/YOURUSERNAME/Wind-Turbine-Earthwork-Calculator/discussions)
- **E-Mail**: [deine@email.com]

---

**Vielen Dank für deine Contribution! 🌬️⚡**
