# Quick Start Guide 🚀

**Get up and running in 5 minutes!**

---

## ⚡ Installation (2 minutes)

### 1. Install Dependency

```bash
python3 -m pip install --user --break-system-packages ezdxf
```

### 2. Enable Plugin in QGIS

1. Start **QGIS 3.34 LTR**
2. Go to **Plugins → Manage and Install Plugins**
3. Click **Installed** tab
4. Find and check ☑ **Wind Turbine Earthwork Calculator V2**
5. Close dialog

---

## 🎯 First Run (3 minutes)

### Step 1: Open Processing Toolbox

Press `Ctrl+Alt+T` or go to **View → Panels → Processing Toolbox**

### Step 2: Find Algorithm

- Expand **Wind Turbine Earthwork Calculator V2**
- Double-click **Optimize Platform Height**

### Step 3: Configure Parameters

**Required Parameters:**

| Parameter | Example Value | Description |
|-----------|---------------|-------------|
| Input DXF File | `Kranstellfläche Marsberg V172-7.2-175m.dxf` | Your crane pad outline |
| Min Height | `300.0` | Lowest height to test (m ü.NN) |
| Max Height | `310.0` | Highest height to test (m ü.NN) |
| Output GeoPackage | `/tmp/output.gpkg` | Where to save results |

**Optional (keep defaults for first run):**

- Height Step: `0.1` m
- Slope Angle: `45` degrees
- Num Profiles: `8`

### Step 4: Run

1. Click **Run** button
2. Wait 2-5 minutes (depends on internet speed)
3. Watch progress in log panel

### Step 5: View Results

After completion, you'll have:

```
/tmp/
├── output.gpkg              # Platform polygon, profile lines
├── output.dem.tif          # Elevation data
├── output.html             # Full report (open in browser!)
└── profiles/               # 8 terrain cross-sections
    ├── profile_001.png
    ├── profile_002.png
    └── ...
```

**→ Open `output.html` in your web browser!** 🌐

---

## 📊 Understanding the Results

### HTML Report

The report shows:

1. **Optimal Height** - Highlighted in orange box
   - Example: `305.3 m ü.NN`

2. **Volume Summary**
   - Total Cut: How much to remove (m³)
   - Total Fill: How much to add (m³)
   - Total Earthwork: Sum of both

3. **Terrain Statistics**
   - Min/max/mean elevation
   - Terrain range

4. **Profile Images**
   - 8 cross-sections showing cut (red) and fill (green)

### GeoPackage

Load in QGIS:

1. **Layer → Add Layer → Add Vector Layer**
2. Select `output.gpkg`
3. Choose layer:
   - `platform_polygon` - Optimized crane pad
   - `profile_lines` - Cross-section lines

### DEM Raster

1. **Layer → Add Layer → Add Raster Layer**
2. Select `output.dem.tif`
3. See elevation data

---

## 🔧 Common Adjustments

### Too many scenarios (slow)

**Problem**: Height range too large
**Solution**: Reduce range or increase step

```
Min: 300, Max: 310, Step: 0.1 → 101 scenarios ✓
Min: 300, Max: 400, Step: 0.1 → 1001 scenarios ✗ (too slow!)
```

**Fix**:
- Use smaller range: 300-305
- Or larger step: 0.2m instead of 0.1m

### DEM download fails

**Problem**: No internet or tile unavailable
**Solution**:
- Check internet connection
- Verify DXF is in Germany (EPSG:25832)
- Try different location

### Invalid polygon error

**Problem**: DXF polylines don't connect properly
**Solution**:
- Increase DXF tolerance: `0.01` → `0.1`
- Check DXF file in CAD software
- Ensure polylines form valid shape

---

## 💡 Tips for Best Results

### 1. Height Range Selection

Start with terrain mean ± 5m:

Example:
- Terrain mean: 305m
- Min: 300m (305 - 5)
- Max: 310m (305 + 5)

### 2. Step Size

- **Fast preview**: 0.5m step (20 scenarios)
- **Normal**: 0.1m step (100 scenarios)
- **Precise**: 0.05m step (200 scenarios)

### 3. Cache Usage

First run downloads DEM (~10-30 MB).
Subsequent runs use cache (much faster!).

Clear cache if needed:
```bash
rm -rf ~/.qgis3/windturbine_calculator_v2/dem_cache/
```

---

## 📖 Next Steps

### Learn More

- **Full Documentation**: See [README.md](windturbine_earthwork_calculator_v2/README.md)
- **Installation Details**: See [INSTALLATION.md](windturbine_earthwork_calculator_v2/INSTALLATION.md)
- **Development Info**: See [DEVELOPMENT_SUMMARY.md](DEVELOPMENT_SUMMARY.md)

### Test Different Scenarios

Try varying:
- Slope angle (30°-60°)
- Number of profiles (4-16)
- Vertical exaggeration (1.0-5.0)

### Process Multiple Sites

Run the algorithm once per crane pad location.

---

## ❓ Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Plugin not visible | Restart QGIS, check Plugins menu |
| Import ezdxf error | Run: `pip install --user --break-system-packages ezdxf` |
| DEM download slow | Normal for first run (~30 sec per tile) |
| Process hangs | Check height range (should be < 1000 scenarios) |
| Invalid polygon | Increase DXF tolerance or fix DXF file |

---

## 🎉 You're Ready!

That's it! You now know enough to:

✅ Run the plugin
✅ Interpret results
✅ Adjust parameters
✅ Troubleshoot issues

**Happy optimizing!** 🌬️

---

**Questions?** Check the full [README.md](windturbine_earthwork_calculator_v2/README.md)

**Problems?** See logs: `~/.qgis3/windturbine_calculator_v2/*.log`
