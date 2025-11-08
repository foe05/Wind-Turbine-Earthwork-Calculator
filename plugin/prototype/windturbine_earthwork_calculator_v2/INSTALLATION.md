# Installation Guide - Wind Turbine Earthwork Calculator V2

Quick installation guide for QGIS 3.34 LTR

---

## ✅ Prerequisites Checklist

Before installation, ensure you have:

- [x] **QGIS 3.34 LTR** installed (or higher)
- [x] **Python 3.9+** (comes with QGIS)
- [x] **Internet connection** (for DEM downloads)
- [x] **~100 MB free disk space** (for cache and outputs)

---

## 📦 Step-by-Step Installation

### Step 1: Copy Plugin Files

Copy the entire plugin folder to your QGIS plugins directory:

```bash
# Navigate to the project directory
cd /home/foe/9_sideprojects/GITHUB/Wind-Turbine-Earthwork-Calculator/Wind-Turbine-Earthwork-Calculator/plugin/prototype

# Copy to QGIS plugins directory
cp -r windturbine_earthwork_calculator_v2 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

**Alternative**: Use symlink for development:
```bash
ln -s "$(pwd)/windturbine_earthwork_calculator_v2" ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

### Step 2: Install Python Dependencies

The plugin requires two additional packages:

#### Option A: Using pip (recommended)

```bash
# Install ezdxf (for DXF import)
python3 -m pip install --user --break-system-packages ezdxf

# Install requests (for API calls) - usually already installed
python3 -m pip install --user --break-system-packages requests
```

#### Option B: Using the installation script

```bash
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/windturbine_earthwork_calculator_v2

# Modify install_dependencies.py to use --break-system-packages flag
python3 install_dependencies.py
```

#### Verify Installation

Test that dependencies are installed:

```bash
python3 -c "import ezdxf; import requests; print('✓ All dependencies installed')"
```

### Step 3: Enable Plugin in QGIS

1. **Start QGIS**

2. **Open Plugin Manager**
   - Menu: `Plugins → Manage and Install Plugins`
   - Or press `Ctrl+Shift+P`

3. **Find Plugin**
   - Click `Installed` tab
   - Search for "Wind Turbine"
   - Find **Wind Turbine Earthwork Calculator V2**

4. **Enable**
   - Check the checkbox next to the plugin name
   - Click `Close`

5. **Verify**
   - Open `Processing Toolbox` (Ctrl+Alt+T)
   - Expand `Wind Turbine Earthwork Calculator V2`
   - You should see: **Optimize Platform Height**

---

## 🧪 Testing the Installation

### Test 1: Check Plugin Appears

```bash
# List QGIS plugins
ls -la ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/ | grep windturbine
```

You should see the `windturbine_earthwork_calculator_v2` directory.

### Test 2: Test DXF Import (Standalone)

```bash
cd /home/foe/9_sideprojects/GITHUB/Wind-Turbine-Earthwork-Calculator/Wind-Turbine-Earthwork-Calculator/plugin/prototype

python3 test_dxf_simple.py "Kranstellfläche Marsberg V172-7.2-175m.dxf"
```

Expected output:
```
✓ TEST PASSED
DXF file structure is valid and ready for import!
Found 42 polylines with 681 total points.
```

### Test 3: Run in QGIS

1. Open QGIS
2. Open `Processing Toolbox`
3. Find `Wind Turbine → Optimize Platform Height`
4. Double-click to open the algorithm
5. Fill in parameters:
   - **Input DXF**: `Kranstellfläche Marsberg V172-7.2-175m.dxf`
   - **Min Height**: 300.0
   - **Max Height**: 310.0
   - **Output GeoPackage**: `/tmp/test_output.gpkg`
6. Click `Run`

---

## 🔧 Troubleshooting

### Plugin doesn't appear in QGIS

**Check 1**: Verify files exist
```bash
ls -la ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/windturbine_earthwork_calculator_v2/
```

**Check 2**: Verify metadata.txt exists
```bash
cat ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/windturbine_earthwork_calculator_v2/metadata.txt
```

**Check 3**: Check QGIS logs
- In QGIS: `View → Panels → Log Messages`
- Look for errors related to "windturbine"

**Fix**: Restart QGIS

### ImportError: No module named 'ezdxf'

**Solution**:
```bash
python3 -m pip install --user --break-system-packages ezdxf
```

Then restart QGIS.

### ImportError: No module named 'qgis.core'

**Reason**: You're trying to run the plugin outside of QGIS.

**Solution**: The plugin modules can only be imported within QGIS. Use the standalone test scripts for testing outside QGIS.

### Processing algorithm doesn't start

**Check**: QGIS Python console for errors
- `Plugins → Python Console`
- Try importing the plugin:
  ```python
  from windturbine_earthwork_calculator_v2.plugin import WindTurbineEarthworkCalculatorPlugin
  ```

### DEM Download fails

**Possible reasons**:
1. No internet connection
2. Tile not available on hoehendaten.de
3. Coordinates not in Germany/EPSG:25832 range

**Solution**:
- Check internet connection
- Verify DXF coordinates are in EPSG:25832
- Check hoehendaten.de is accessible

---

## 📁 File Structure (After Installation)

```
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
└── windturbine_earthwork_calculator_v2/
    ├── __init__.py
    ├── plugin.py
    ├── metadata.txt
    ├── requirements.txt
    ├── install_dependencies.py
    ├── README.md
    ├── INSTALLATION.md
    ├── processing_provider/
    │   ├── __init__.py
    │   ├── provider.py
    │   └── optimize_algorithm.py
    ├── core/
    │   ├── __init__.py
    │   ├── dxf_importer.py
    │   ├── dem_downloader.py
    │   ├── earthwork_calculator.py
    │   ├── profile_generator.py
    │   └── report_generator.py
    ├── utils/
    │   ├── __init__.py
    │   ├── validation.py
    │   ├── geometry_utils.py
    │   └── logging_utils.py
    └── tests/
        ├── __init__.py
        └── test_dxf_import.py
```

---

## 🎯 Quick Reference

### Commands Summary

```bash
# Install dependencies
python3 -m pip install --user --break-system-packages ezdxf requests

# Copy plugin
cp -r windturbine_earthwork_calculator_v2 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

# Test DXF import
python3 test_dxf_simple.py "path/to/file.dxf"

# Check logs
tail -f ~/.qgis3/windturbine_calculator_v2/*.log
```

### Cache Locations

- **DEM Tiles**: `~/.qgis3/windturbine_calculator_v2/dem_cache/`
- **Logs**: `~/.qgis3/windturbine_calculator_v2/*.log`
- **Temp Files**: `/tmp/dem_mosaic_*.tif`

### Default Parameters

| Parameter | Default Value |
|-----------|---------------|
| Height Step | 0.1 m |
| DXF Tolerance | 0.01 m |
| Slope Angle | 45° |
| Num Profiles | 8 |
| Vertical Exaggeration | 2.0x |

---

## ✅ Installation Complete!

You're all set! Open QGIS and find the plugin in:

**Processing Toolbox → Wind Turbine Earthwork Calculator V2 → Optimize Platform Height**

For detailed usage instructions, see [README.md](README.md).

**Happy Optimizing! 🌬️**
