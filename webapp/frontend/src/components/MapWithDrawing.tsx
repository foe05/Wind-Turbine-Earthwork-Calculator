/**
 * Enhanced Map Component with Drawing Tools
 * Supports: Point (WKA), Line (Road), Polygon (Solar/Terrain)
 */

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LatLng, WKASite } from '../types';
import { latLngToUTM, formatUTM, isInGermany } from '../utils/coordinates';

// Fix Leaflet default icon
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

interface MapWithDrawingProps {
  sites: WKASite[];
  onSiteAdded: (site: WKASite) => void;
  onSiteSelected: (site: WKASite | null) => void;
  selectedSite: WKASite | null;
  drawingMode: 'point' | 'line' | 'polygon' | null;
  onLineDrawn?: (coordinates: LatLng[]) => void;
  onPolygonDrawn?: (coordinates: LatLng[]) => void;
}

const MapWithDrawing: React.FC<MapWithDrawingProps> = ({
  sites,
  onSiteAdded,
  onSiteSelected,
  selectedSite,
  drawingMode,
  onLineDrawn,
  onPolygonDrawn,
}) => {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());

  // Drawing state
  const [drawingPoints, setDrawingPoints] = useState<LatLng[]>([]);
  const drawingLayerRef = useRef<L.Polyline | L.Polygon | null>(null);
  const tempMarkersRef = useRef<L.CircleMarker[]>([]);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current).setView([51.1657, 10.4515], 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    mapRef.current = map;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Handle map clicks based on drawing mode
  useEffect(() => {
    if (!mapRef.current) return;

    const map = mapRef.current;

    const handleClick = (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      const position: LatLng = { lat, lng };

      if (!isInGermany(position)) {
        alert('Bitte wählen Sie einen Standort in Deutschland');
        return;
      }

      if (drawingMode === 'point') {
        // WKA mode - add marker immediately
        const utmPosition = latLngToUTM(position);
        const newSite: WKASite = {
          id: `site_${Date.now()}`,
          name: `WKA ${sites.length + 1}`,
          position,
          utmPosition,
        };
        onSiteAdded(newSite);
      } else if (drawingMode === 'line' || drawingMode === 'polygon') {
        // Drawing mode - collect points
        const newPoints = [...drawingPoints, position];
        setDrawingPoints(newPoints);

        // Add temporary marker
        const tempMarker = L.circleMarker([lat, lng], {
          radius: 5,
          color: '#3B82F6',
          fillColor: '#3B82F6',
          fillOpacity: 0.7,
        }).addTo(map);

        tempMarkersRef.current.push(tempMarker);

        // Update drawing layer
        if (drawingLayerRef.current) {
          drawingLayerRef.current.remove();
        }

        const latLngs: [number, number][] = newPoints.map((p) => [p.lat, p.lng]);

        if (drawingMode === 'line') {
          drawingLayerRef.current = L.polyline(latLngs, {
            color: '#3B82F6',
            weight: 3,
          }).addTo(map);
        } else if (drawingMode === 'polygon') {
          drawingLayerRef.current = L.polygon(latLngs, {
            color: '#10B981',
            fillColor: '#10B981',
            fillOpacity: 0.2,
            weight: 2,
          }).addTo(map);
        }
      }
    };

    const handleDblClick = () => {
      // Double-click to finish drawing
      if ((drawingMode === 'line' || drawingMode === 'polygon') && drawingPoints.length >= 2) {
        if (drawingMode === 'line' && onLineDrawn) {
          onLineDrawn(drawingPoints);
        } else if (drawingMode === 'polygon' && drawingPoints.length >= 3 && onPolygonDrawn) {
          onPolygonDrawn(drawingPoints);
        }

        // Clear drawing state
        clearDrawing();
      }
    };

    map.on('click', handleClick);
    map.on('dblclick', handleDblClick);

    return () => {
      map.off('click', handleClick);
      map.off('dblclick', handleDblClick);
    };
  }, [drawingMode, drawingPoints, sites.length, onSiteAdded, onLineDrawn, onPolygonDrawn]);

  // Clear drawing when mode changes
  useEffect(() => {
    clearDrawing();
  }, [drawingMode]);

  const clearDrawing = () => {
    setDrawingPoints([]);

    // Remove drawing layer
    if (drawingLayerRef.current && mapRef.current) {
      drawingLayerRef.current.remove();
      drawingLayerRef.current = null;
    }

    // Remove temporary markers
    if (mapRef.current) {
      tempMarkersRef.current.forEach((marker) => marker.remove());
      tempMarkersRef.current = [];
    }
  };

  // Update WKA markers
  useEffect(() => {
    if (!mapRef.current) return;

    // Remove old markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current.clear();

    // Add new markers (only for WKA sites)
    sites.forEach((site) => {
      const marker = L.marker([site.position.lat, site.position.lng], {
        icon: DefaultIcon,
      });

      const popupContent = `
        <div style="padding: 8px;">
          <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">${site.name}</h3>
          <p style="margin: 4px 0; font-size: 12px;">
            <strong>UTM:</strong> ${formatUTM(site.utmPosition)}
          </p>
          ${
            site.calculation
              ? `
            <p style="margin: 4px 0; font-size: 12px;">
              <strong>Aushub:</strong> ${site.calculation.total_cut.toFixed(1)} m³
            </p>
            <p style="margin: 4px 0; font-size: 12px;">
              <strong>Auffüllung:</strong> ${site.calculation.total_fill.toFixed(1)} m³
            </p>
          `
              : ''
          }
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('click', () => {
        onSiteSelected(site);
      });

      marker.addTo(mapRef.current!);
      markersRef.current.set(site.id, marker);
    });
  }, [sites, onSiteSelected]);

  // Highlight selected site
  useEffect(() => {
    markersRef.current.forEach((marker, siteId) => {
      const isSelected = selectedSite?.id === siteId;

      if (isSelected) {
        const redIcon = L.icon({
          iconUrl:
            'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjUiIGhlaWdodD0iNDEiIHZpZXdCb3g9IjAgMCAyNSA0MSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTIuNSAwQzUuNiAwIDAgNS42IDAgMTIuNWMwIDkuNCAxMi41IDI4LjUgMTIuNSAyOC41czEyLjUtMTkuMSAxMi41LTI4LjVDMjUgNS42IDE5LjQgMCAxMi41IDB6bTAgMTcuNWMtMi44IDAtNS0yLjItNS01czIuMi01IDUtNSA1IDIuMiA1IDUtMi4yIDUtNSA1eiIgZmlsbD0iI0VGNDQ0NCIvPjwvc3ZnPg==',
          shadowUrl: iconShadow,
          iconSize: [25, 41],
          iconAnchor: [12, 41],
        });
        marker.setIcon(redIcon);
        marker.openPopup();
      } else {
        marker.setIcon(DefaultIcon);
        marker.closePopup();
      }
    });
  }, [selectedSite]);

  const getInstructionText = () => {
    if (drawingMode === 'point') {
      return 'Klicken Sie auf die Karte, um einen WKA-Standort hinzuzufügen';
    } else if (drawingMode === 'line') {
      return `Klicken Sie, um Punkte hinzuzufügen (${drawingPoints.length} Punkte). Doppelklick zum Abschließen.`;
    } else if (drawingMode === 'polygon') {
      return `Klicken Sie, um Polygon-Punkte hinzuzufügen (${drawingPoints.length} Punkte). Doppelklick zum Abschließen.`;
    }
    return 'Wählen Sie einen Tab aus, um zu beginnen';
  };

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <div ref={mapContainerRef} style={{ height: '100%', width: '100%' }} />
      <div
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          background: 'white',
          padding: '12px',
          borderRadius: '4px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
          fontSize: '12px',
          zIndex: 1000,
          maxWidth: '250px',
        }}
      >
        <strong>Zeichenmodus:</strong>{' '}
        {drawingMode === 'point'
          ? '📍 Punkt'
          : drawingMode === 'line'
          ? '📏 Linie'
          : drawingMode === 'polygon'
          ? '⬟ Polygon'
          : '—'}
        <br />
        <small style={{ marginTop: '8px', display: 'block' }}>{getInstructionText()}</small>
        {drawingPoints.length > 0 && (
          <button
            onClick={clearDrawing}
            style={{
              marginTop: '8px',
              padding: '4px 8px',
              fontSize: '11px',
              backgroundColor: '#EF4444',
              color: 'white',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
            }}
          >
            Zeichnung löschen
          </button>
        )}
      </div>
    </div>
  );
};

export default MapWithDrawing;
