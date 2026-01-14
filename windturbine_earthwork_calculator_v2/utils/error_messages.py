"""
Error Message Catalog for Wind Turbine Earthwork Calculator V2

Provides bilingual (German/English) error messages with actionable fix suggestions.
All error messages follow the structure:
    {'de': 'German message', 'en': 'English message', 'fix': 'How to fix (bilingual)'}

Author: Wind Energy Site Planning
Version: 2.0.0
"""

# Dictionary of error messages with German and English translations
# Each message includes:
#   - 'de': German error message
#   - 'en': English error message
#   - 'fix': Suggested fix (bilingual if applicable)
ERROR_MESSAGES = {
    # ========================================================================
    # DXF File Errors
    # ========================================================================
    'dxf_file_not_found': {
        'de': 'DXF-Datei nicht gefunden: {file_path}',
        'en': 'DXF file not found: {file_path}',
        'fix': {
            'de': 'Prüfen Sie, ob der Dateipfad korrekt ist und die Datei existiert.',
            'en': 'Check that the file path is correct and the file exists.'
        }
    },
    'dxf_read_error': {
        'de': 'Fehler beim Lesen der DXF-Datei: {error}',
        'en': 'Error reading DXF file: {error}',
        'fix': {
            'de': 'Stellen Sie sicher, dass die Datei eine gültige DXF-Datei ist und nicht beschädigt ist.',
            'en': 'Ensure the file is a valid DXF file and not corrupted.'
        }
    },
    'dxf_no_entities': {
        'de': 'Keine Geometrien in DXF-Datei gefunden',
        'en': 'No entities found in DXF file',
        'fix': {
            'de': 'Die DXF-Datei muss LWPOLYLINE-Objekte enthalten.',
            'en': 'The DXF file must contain LWPOLYLINE entities.'
        }
    },
    'dxf_layer_not_found': {
        'de': 'Layer "{layer_name}" nicht in DXF-Datei gefunden',
        'en': 'Layer "{layer_name}" not found in DXF file',
        'fix': {
            'de': 'Verfügbare Layer: {available_layers}',
            'en': 'Available layers: {available_layers}'
        }
    },
    'dxf_wrong_entity_type': {
        'de': 'Falsche Geometrie-Typen gefunden: {entity_types}',
        'en': 'Wrong entity types found: {entity_types}',
        'fix': {
            'de': 'Nur LWPOLYLINE-Objekte werden unterstützt. Konvertieren Sie LINE, POLYLINE oder CIRCLE zu LWPOLYLINE in CAD.',
            'en': 'Only LWPOLYLINE entities are supported. Convert LINE, POLYLINE or CIRCLE to LWPOLYLINE in CAD.'
        }
    },
    'ezdxf_not_installed': {
        'de': 'Das Paket "ezdxf" ist nicht installiert',
        'en': 'Package "ezdxf" is not installed',
        'fix': {
            'de': 'Windows (OSGeo4W Shell): pip install ezdxf shapely\nQGIS Python Console: import subprocess; subprocess.check_call([\'pip\', \'install\', \'ezdxf\', \'shapely\'])',
            'en': 'Windows (OSGeo4W Shell): pip install ezdxf shapely\nQGIS Python Console: import subprocess; subprocess.check_call([\'pip\', \'install\', \'ezdxf\', \'shapely\'])'
        }
    },

    # ========================================================================
    # File System Errors
    # ========================================================================
    'file_not_found': {
        'de': 'Datei nicht gefunden: {file_path}',
        'en': 'File not found: {file_path}',
        'fix': {
            'de': 'Prüfen Sie den Dateipfad.',
            'en': 'Check the file path.'
        }
    },
    'not_a_file': {
        'de': 'Pfad ist keine Datei: {file_path}',
        'en': 'Path is not a file: {file_path}',
        'fix': {
            'de': 'Geben Sie einen Dateipfad, nicht einen Ordnerpfad an.',
            'en': 'Provide a file path, not a directory path.'
        }
    },
    'wrong_file_extension': {
        'de': 'Falsche Dateiendung: {actual}, erwartet {expected}',
        'en': 'Wrong file extension: {actual}, expected {expected}',
        'fix': {
            'de': 'Verwenden Sie eine Datei mit der Endung {expected}.',
            'en': 'Use a file with extension {expected}.'
        }
    },
    'output_dir_not_found': {
        'de': 'Ausgabe-Verzeichnis existiert nicht: {dir_path}',
        'en': 'Output directory does not exist: {dir_path}',
        'fix': {
            'de': 'Erstellen Sie das Verzeichnis oder wählen Sie ein existierendes.',
            'en': 'Create the directory or select an existing one.'
        }
    },
    'output_dir_not_writable': {
        'de': 'Ausgabe-Verzeichnis ist nicht beschreibbar: {dir_path}',
        'en': 'Output directory is not writable: {dir_path}',
        'fix': {
            'de': 'Prüfen Sie die Schreibrechte für das Verzeichnis.',
            'en': 'Check write permissions for the directory.'
        }
    },

    # ========================================================================
    # Coordinate Reference System (CRS) Errors
    # ========================================================================
    'crs_invalid': {
        'de': 'Ungültiges Koordinatenreferenzsystem',
        'en': 'Invalid coordinate reference system',
        'fix': {
            'de': 'Wählen Sie ein gültiges CRS (z.B. EPSG:25832 für UTM Zone 32N).',
            'en': 'Select a valid CRS (e.g., EPSG:25832 for UTM Zone 32N).'
        }
    },
    'crs_mismatch': {
        'de': 'Falsches CRS: EPSG:{actual}, erwartet EPSG:{expected}',
        'en': 'Wrong CRS: EPSG:{actual}, expected EPSG:{expected}',
        'fix': {
            'de': 'Transformieren Sie die Daten nach EPSG:{expected}. Übliche deutsche CRS: EPSG:25832 (UTM 32N), EPSG:25833 (UTM 33N), EPSG:31467 (Gauss-Krüger Zone 3).',
            'en': 'Transform the data to EPSG:{expected}. Common German CRS: EPSG:25832 (UTM 32N), EPSG:25833 (UTM 33N), EPSG:31467 (Gauss-Krüger Zone 3).'
        }
    },
    'crs_geographic_not_supported': {
        'de': 'Geografisches CRS nicht unterstützt (z.B. EPSG:4326 WGS84)',
        'en': 'Geographic CRS not supported (e.g., EPSG:4326 WGS84)',
        'fix': {
            'de': 'Verwenden Sie ein projiziertes CRS wie EPSG:25832 (UTM 32N) für Meter-Berechnungen.',
            'en': 'Use a projected CRS like EPSG:25832 (UTM 32N) for meter-based calculations.'
        }
    },

    # ========================================================================
    # Geometry Validation Errors
    # ========================================================================
    'geometry_empty': {
        'de': 'Geometrie ist leer',
        'en': 'Geometry is empty',
        'fix': {
            'de': 'Stellen Sie sicher, dass die Geometrie Koordinaten enthält.',
            'en': 'Ensure the geometry contains coordinates.'
        }
    },
    'geometry_invalid': {
        'de': 'Ungültige Geometrie: {error}',
        'en': 'Invalid geometry: {error}',
        'fix': {
            'de': 'Prüfen Sie die Geometrie auf Selbstüberschneidungen, Spitzen oder ungültige Ringe.',
            'en': 'Check geometry for self-intersections, spikes, or invalid rings.'
        }
    },
    'geometry_invalid_area': {
        'de': 'Polygon hat ungültige Fläche: {area} m²',
        'en': 'Polygon has invalid area: {area} m²',
        'fix': {
            'de': 'Fläche muss positiv sein. Prüfen Sie die Polygon-Orientierung.',
            'en': 'Area must be positive. Check polygon orientation.'
        }
    },
    'geometry_self_intersection': {
        'de': 'Polygon hat Selbstüberschneidung bei Koordinate ({x:.2f}, {y:.2f})',
        'en': 'Polygon has self-intersection at coordinate ({x:.2f}, {y:.2f})',
        'fix': {
            'de': 'Korrigieren Sie die Überschneidung in CAD bei dieser Koordinate.',
            'en': 'Fix the intersection in CAD at this coordinate.'
        }
    },
    'geometry_spike_vertex': {
        'de': 'Polygon hat Spitzen-Vertex bei ({x:.2f}, {y:.2f})',
        'en': 'Polygon has spike vertex at ({x:.2f}, {y:.2f})',
        'fix': {
            'de': 'Entfernen Sie überflüssige Stützpunkte.',
            'en': 'Remove redundant vertices.'
        }
    },
    'geometry_not_simple': {
        'de': 'Polygon ist nicht einfach (hat Überschneidungen oder Duplikate)',
        'en': 'Polygon is not simple (has intersections or duplicates)',
        'fix': {
            'de': 'Vereinfachen Sie das Polygon und entfernen Sie Überschneidungen.',
            'en': 'Simplify the polygon and remove intersections.'
        }
    },
    'geometry_too_small': {
        'de': 'Fläche zu klein: {area:.2f} m², Minimum: {min_area:.2f} m²',
        'en': 'Area too small: {area:.2f} m², minimum: {min_area:.2f} m²',
        'fix': {
            'de': 'Vergrößern Sie die Fläche oder prüfen Sie die Eingabedaten.',
            'en': 'Increase the area or check input data.'
        }
    },
    'geometry_too_large': {
        'de': 'Fläche zu groß: {area:.2f} m², Maximum: {max_area:.2f} m²',
        'en': 'Area too large: {area:.2f} m², maximum: {max_area:.2f} m²',
        'fix': {
            'de': 'Verkleinern Sie die Fläche oder prüfen Sie die Eingabedaten.',
            'en': 'Decrease the area or check input data.'
        }
    },

    # ========================================================================
    # Surface Relationship Errors
    # ========================================================================
    'foundation_not_touching_crane_pad': {
        'de': 'Fundamentfläche muss die Kranstellfläche berühren oder darin liegen',
        'en': 'Foundation must touch or be within crane pad',
        'fix': {
            'de': 'Positionieren Sie die Fundamentfläche so, dass sie die Kranstellfläche berührt.',
            'en': 'Position the foundation so it touches the crane pad.'
        }
    },
    'boom_connection_edge_not_found': {
        'de': 'Konnte keine Verbindungskante der Auslegerfläche zur Kranstellfläche finden',
        'en': 'Could not find boom connection edge to crane pad',
        'fix': {
            'de': 'Die Auslegerfläche muss eine Kante haben, die nahe an der Kranstellfläche liegt.',
            'en': 'The boom surface must have an edge close to the crane pad.'
        }
    },
    'boom_too_far_from_crane_pad': {
        'de': 'Auslegerfläche ist zu weit von der Kranstellfläche entfernt. Abstand: {distance:.2f}m, Maximum: {max_distance:.1f}m',
        'en': 'Boom surface is too far from crane pad. Distance: {distance:.2f}m, maximum: {max_distance:.1f}m',
        'fix': {
            'de': 'Verschieben Sie die Auslegerfläche näher zur Kranstellfläche (max. {max_distance:.1f}m Abstand).',
            'en': 'Move boom surface closer to crane pad (max. {max_distance:.1f}m distance).'
        }
    },
    'rotor_too_far_from_crane_pad': {
        'de': 'Blattlagerfläche ist zu weit von der Kranstellfläche entfernt. Abstand: {distance:.2f}m, Maximum: {max_distance:.1f}m',
        'en': 'Rotor storage is too far from crane pad. Distance: {distance:.2f}m, maximum: {max_distance:.1f}m',
        'fix': {
            'de': 'Verschieben Sie die Blattlagerfläche näher zur Kranstellfläche (max. {max_distance:.1f}m Abstand).',
            'en': 'Move rotor storage closer to crane pad (max. {max_distance:.1f}m distance).'
        }
    },
    'boom_rotor_overlap': {
        'de': 'Auslegerfläche und Blattlagerfläche dürfen sich nicht überlappen. Überlappung: {overlap_area:.1f} m²',
        'en': 'Boom surface and rotor storage must not overlap. Overlap: {overlap_area:.1f} m²',
        'fix': {
            'de': 'Verschieben Sie eine der Flächen, sodass keine Überlappung besteht.',
            'en': 'Move one of the surfaces so there is no overlap.'
        }
    },
    'boom_rotor_intersection': {
        'de': 'Auslegerfläche und Blattlagerfläche überlappen sich',
        'en': 'Boom surface and rotor storage overlap',
        'fix': {
            'de': 'Die Flächen dürfen sich nur an den Rändern berühren, nicht überlappen.',
            'en': 'Surfaces may only touch at edges, not overlap.'
        }
    },

    # ========================================================================
    # Height Range Validation Errors
    # ========================================================================
    'height_max_less_than_min': {
        'de': 'Maximale Höhe ({max_height}) muss größer als minimale Höhe ({min_height}) sein',
        'en': 'Maximum height ({max_height}) must be greater than minimum height ({min_height})',
        'fix': {
            'de': 'Erhöhen Sie die maximale Höhe oder verringern Sie die minimale Höhe.',
            'en': 'Increase maximum height or decrease minimum height.'
        }
    },
    'height_step_not_positive': {
        'de': 'Höhenschritt muss positiv sein, erhalten: {step}',
        'en': 'Height step must be positive, got: {step}',
        'fix': {
            'de': 'Verwenden Sie einen positiven Wert für den Höhenschritt (z.B. 0.1 oder 0.5).',
            'en': 'Use a positive value for height step (e.g., 0.1 or 0.5).'
        }
    },
    'height_step_too_large': {
        'de': 'Höhenschritt ({step}) ist größer als Höhenbereich ({range})',
        'en': 'Height step ({step}) is larger than height range ({range})',
        'fix': {
            'de': 'Verringern Sie den Höhenschritt oder vergrößern Sie den Höhenbereich.',
            'en': 'Decrease height step or increase height range.'
        }
    },
    'height_too_many_scenarios': {
        'de': 'Zu viele Szenarien ({num_scenarios}). Bitte erhöhen Sie den Schritt oder verringern Sie den Höhenbereich.',
        'en': 'Too many scenarios ({num_scenarios}). Please increase step size or reduce height range.',
        'fix': {
            'de': 'Maximum: 10000 Szenarien. Verwenden Sie einen größeren Höhenschritt.',
            'en': 'Maximum: 10000 scenarios. Use a larger height step.'
        }
    },
    'height_too_few_scenarios': {
        'de': 'Nicht genug Szenarien ({num_scenarios}). Bitte verringern Sie den Schritt oder vergrößern Sie den Höhenbereich.',
        'en': 'Not enough scenarios ({num_scenarios}). Please decrease step size or increase height range.',
        'fix': {
            'de': 'Minimum: 2 Szenarien erforderlich.',
            'en': 'Minimum: 2 scenarios required.'
        }
    },
    'value_below_minimum': {
        'de': '{name} muss >= {minimum} sein, erhalten: {value}',
        'en': '{name} must be >= {minimum}, got: {value}',
        'fix': {
            'de': 'Erhöhen Sie den Wert auf mindestens {minimum}.',
            'en': 'Increase the value to at least {minimum}.'
        }
    },
    'value_above_maximum': {
        'de': '{name} muss <= {maximum} sein, erhalten: {value}',
        'en': '{name} must be <= {maximum}, got: {value}',
        'fix': {
            'de': 'Verringern Sie den Wert auf maximal {maximum}.',
            'en': 'Decrease the value to at most {maximum}.'
        }
    },

    # ========================================================================
    # Raster (DEM) Validation Errors
    # ========================================================================
    'raster_invalid': {
        'de': 'Raster-Layer ist ungültig',
        'en': 'Raster layer is not valid',
        'fix': {
            'de': 'Stellen Sie sicher, dass die DEM-Datei korrekt geladen ist.',
            'en': 'Ensure the DEM file is loaded correctly.'
        }
    },
    'raster_wrong_band_count': {
        'de': 'Raster muss genau 1 Band haben, erhalten: {band_count}',
        'en': 'Raster must have exactly 1 band, got: {band_count}',
        'fix': {
            'de': 'Verwenden Sie ein Einkanal-Höhenmodell (DEM).',
            'en': 'Use a single-band elevation model (DEM).'
        }
    },
    'raster_does_not_cover_geometry': {
        'de': 'Raster deckt nicht die Geometrie ab. Raster: {raster_extent}, Geometrie (mit {buffer_m}m Puffer): {geom_extent}',
        'en': 'Raster does not cover geometry extent. Raster: {raster_extent}, Geometry (with {buffer_m}m buffer): {geom_extent}',
        'fix': {
            'de': 'Laden Sie ein größeres DEM oder verschieben Sie die Geometrie in den DEM-Bereich.',
            'en': 'Load a larger DEM or move the geometry into the DEM extent.'
        }
    },
    'raster_resolution_too_coarse': {
        'de': 'Raster-Auflösung zu grob: {resolution:.2f}m, empfohlen: <= {recommended:.2f}m',
        'en': 'Raster resolution too coarse: {resolution:.2f}m, recommended: <= {recommended:.2f}m',
        'fix': {
            'de': 'Verwenden Sie ein höher aufgelöstes DEM für genauere Ergebnisse.',
            'en': 'Use a higher resolution DEM for more accurate results.'
        }
    },
    'raster_nodata_in_geometry': {
        'de': 'NoData-Werte im Geometrie-Bereich gefunden',
        'en': 'NoData values found in geometry extent',
        'fix': {
            'de': 'Füllen Sie NoData-Bereiche oder verschieben Sie die Geometrie.',
            'en': 'Fill NoData areas or move the geometry.'
        }
    },

    # ========================================================================
    # Configuration Errors
    # ========================================================================
    'config_error': {
        'de': 'Konfigurationsfehler: {error}',
        'en': 'Configuration error: {error}',
        'fix': {
            'de': 'Überprüfen Sie die Projektkonfiguration.',
            'en': 'Check the project configuration.'
        }
    },
    'surface_config_invalid': {
        'de': 'Ungültige Flächenkonfiguration: {surface_type}',
        'en': 'Invalid surface configuration: {surface_type}',
        'fix': {
            'de': 'Überprüfen Sie die Parameter für {surface_type}.',
            'en': 'Check the parameters for {surface_type}.'
        }
    },

    # ========================================================================
    # Processing Errors
    # ========================================================================
    'processing_error': {
        'de': 'Verarbeitungsfehler: {error}',
        'en': 'Processing error: {error}',
        'fix': {
            'de': 'Überprüfen Sie die Eingabedaten und versuchen Sie es erneut.',
            'en': 'Check input data and try again.'
        }
    },
    'calculation_failed': {
        'de': 'Berechnung fehlgeschlagen für {surface_type} bei Höhe {height}m: {error}',
        'en': 'Calculation failed for {surface_type} at height {height}m: {error}',
        'fix': {
            'de': 'Prüfen Sie die Geometrie und DEM-Daten.',
            'en': 'Check geometry and DEM data.'
        }
    },
}


def get_error_keys():
    """
    Get all available error message keys.

    Returns:
        list: List of error message keys
    """
    return list(ERROR_MESSAGES.keys())


def validate_error_messages():
    """
    Validate that all error messages have required fields.

    Raises:
        ValueError: If any message is missing required fields
    """
    for key, message in ERROR_MESSAGES.items():
        if 'de' not in message:
            raise ValueError(f"Message '{key}' missing German ('de') translation")
        if 'en' not in message:
            raise ValueError(f"Message '{key}' missing English ('en') translation")
        if 'fix' not in message:
            raise ValueError(f"Message '{key}' missing 'fix' field")

        # Validate fix field structure
        fix = message['fix']
        if isinstance(fix, dict):
            if 'de' not in fix or 'en' not in fix:
                raise ValueError(f"Message '{key}' fix field must have both 'de' and 'en' keys")


# Validate messages on import
validate_error_messages()
