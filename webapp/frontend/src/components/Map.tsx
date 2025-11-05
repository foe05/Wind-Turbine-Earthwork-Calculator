/**
 * Map Component with Leaflet
 * Allows users to click on map to place WKA sites
 */

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LatLng, WKASite } from '../types';
import { latLngToUTM, formatUTM, isInGermany } from '../utils/coordinates';

// Fix Leaflet default icon issue with bundlers
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

interface MapProps {
  sites: WKASite[];
  onSiteAdded: (site: WKASite) => void;
  onSiteSelected: (site: WKASite | null) => void;
  selectedSite: WKASite | null;
}

const Map: React.FC<MapProps> = ({ sites, onSiteAdded, onSiteSelected, selectedSite }) => {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Create map centered on Germany
    const map = L.map(mapContainerRef.current).setView([51.1657, 10.4515], 6);

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Add click handler to add new sites
    map.on('click', (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      const position: LatLng = { lat, lng };

      // Validate location is in Germany
      if (!isInGermany(position)) {
        alert('Bitte wählen Sie einen Standort in Deutschland');
        return;
      }

      // Convert to UTM
      const utmPosition = latLngToUTM(position);

      // Create new site
      const newSite: WKASite = {
        id: `site_${Date.now()}`,
        name: `WKA ${sites.length + 1}`,
        position,
        utmPosition,
      };

      onSiteAdded(newSite);
    });

    mapRef.current = map;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Update markers when sites change
  useEffect(() => {
    if (!mapRef.current) return;

    // Remove old markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current.clear();

    // Add new markers
    sites.forEach((site) => {
      const marker = L.marker([site.position.lat, site.position.lng], {
        icon: DefaultIcon,
      });

      // Add popup with site info
      const popupContent = `
        <div style="padding: 8px;">
          <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">${site.name}</h3>
          <p style="margin: 4px 0; font-size: 12px;">
            <strong>Lat/Lng:</strong> ${site.position.lat.toFixed(6)}°, ${site.position.lng.toFixed(6)}°
          </p>
          <p style="margin: 4px 0; font-size: 12px;">
            <strong>UTM:</strong> ${formatUTM(site.utmPosition)}
          </p>
          ${site.calculation ? `
            <p style="margin: 4px 0; font-size: 12px;">
              <strong>Aushub:</strong> ${site.calculation.total_cut.toFixed(1)} m³
            </p>
            <p style="margin: 4px 0; font-size: 12px;">
              <strong>Auffüllung:</strong> ${site.calculation.total_fill.toFixed(1)} m³
            </p>
          ` : ''}
        </div>
      `;

      marker.bindPopup(popupContent);

      // Click handler to select site
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
        // Change to red icon for selected site
        const redIcon = L.icon({
          iconUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjUiIGhlaWdodD0iNDEiIHZpZXdCb3g9IjAgMCAyNSA0MSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTIuNSAwQzUuNiAwIDAgNS42IDAgMTIuNWMwIDkuNCAxMi41IDI4LjUgMTIuNSAyOC41czEyLjUtMTkuMSAxMi41LTI4LjVDMjUgNS42IDE5LjQgMCAxMi41IDB6bTAgMTcuNWMtMi44IDAtNS0yLjItNS01czIuMi01IDUtNSA1IDIuMiA1IDUtMi4yIDUtNSA1eiIgZmlsbD0iI0VGNDQ0NCIvPjwvc3ZnPg==',
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

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <div ref={mapContainerRef} style={{ height: '100%', width: '100%' }} />
      <div
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          background: 'white',
          padding: '10px',
          borderRadius: '4px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
          fontSize: '12px',
          zIndex: 1000,
        }}
      >
        <strong>Standorte:</strong> {sites.length}
        <br />
        <small>Klicken Sie auf die Karte, um einen WKA-Standort hinzuzufügen</small>
      </div>
    </div>
  );
};

export default Map;
