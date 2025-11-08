# Shapely Installation for Wind Turbine Earthwork Calculator V2

## Problem

The plugin requires the Shapely library for robust DXF polygon connection. Without Shapely, the plugin falls back to a graph-based approach that may produce incomplete polygons.

## Diagnosis

The log shows:
```
SHAPELY_AVAILABLE: False
Shapely is not available, skipping Shapely method
Shapely method failed, trying graph-based approach...
```

This means Shapely is not installed in the QGIS Python environment.

## Solution

You need to install Shapely in the QGIS Python environment. There are several ways to do this:

### Option 1: QGIS Python Console (Recommended)

1. Open QGIS
2. Go to Plugins > Python Console
3. Run the following command:

```python
import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "shapely"])
```

### Option 2: System Package Manager (Linux)

If you're on Linux, you can install the system package:

```bash
sudo apt-get install python3-shapely
```

### Option 3: Using QGIS's pip

Find the QGIS Python executable and use it to install Shapely:

```bash
# Find QGIS Python (typical locations)
# /usr/bin/python3 (system)
# or check in QGIS settings

# Install Shapely
python3 -m pip install --user shapely
```

### Option 4: OSGeo4W Shell (Windows)

If you're on Windows with OSGeo4W:

1. Open OSGeo4W Shell
2. Run:
```
python-qgis -m pip install shapely
```

## Verify Installation

After installation, verify Shapely is available:

1. Open QGIS Python Console
2. Run:
```python
try:
    from shapely.geometry import LineString
    print("Shapely is installed and working!")
except ImportError:
    print("Shapely is NOT installed")
```

## After Installation

Once Shapely is installed, run the plugin again. You should see in the log:

```
SHAPELY_AVAILABLE: True
Calling _connect_with_shapely with gap_tol=0.5m
Trying Shapely-based connection with gap tolerance 0.5m...
Created 42 Shapely LineStrings
...
Shapely method successful: XX vertices, area = XXX.XX m²
```

This will produce a complete polygon using all 42 lines from the DXF file.
