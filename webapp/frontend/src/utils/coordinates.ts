/**
 * Coordinate conversion utilities using proj4
 * CRITICAL: hoehendaten.de API requires UTM coordinates (EPSG:25832-25836)
 */

import proj4 from 'proj4';
import { LatLng, UTMCoordinate } from '../types';

// Define UTM projections for zones 32-36 (Germany)
// EPSG:25832 = UTM Zone 32N (ETRS89)
// EPSG:25833 = UTM Zone 33N (ETRS89)
// EPSG:25834 = UTM Zone 34N (ETRS89)
// EPSG:25835 = UTM Zone 35N (ETRS89)
// EPSG:25836 = UTM Zone 36N (ETRS89)

proj4.defs([
  ['EPSG:4326', '+proj=longlat +datum=WGS84 +no_defs'],
  ['EPSG:25832', '+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs'],
  ['EPSG:25833', '+proj=utm +zone=33 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs'],
  ['EPSG:25834', '+proj=utm +zone=34 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs'],
  ['EPSG:25835', '+proj=utm +zone=35 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs'],
  ['EPSG:25836', '+proj=utm +zone=36 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs'],
]);

/**
 * Determine the appropriate UTM zone for a given longitude
 * Germany is primarily in zones 32 and 33
 */
export function getUTMZoneFromLongitude(longitude: number): number {
  // UTM zone calculation: zone = floor((longitude + 180) / 6) + 1
  const zone = Math.floor((longitude + 180) / 6) + 1;

  // Clamp to zones 32-36 for Germany/Central Europe
  return Math.max(32, Math.min(36, zone));
}

/**
 * Convert Lat/Lng (WGS84) to UTM coordinates
 * Returns UTM coordinates in EPSG:25832-25836
 */
export function latLngToUTM(latLng: LatLng): UTMCoordinate {
  const { lat, lng } = latLng;

  // Determine appropriate UTM zone
  const zone = getUTMZoneFromLongitude(lng);
  const epsg = `EPSG:25${zone + 800}`; // 25832-25836

  // Convert using proj4
  const [easting, northing] = proj4('EPSG:4326', epsg, [lng, lat]);

  return {
    easting: Math.round(easting * 100) / 100, // Round to cm
    northing: Math.round(northing * 100) / 100,
    zone,
    epsg,
  };
}

/**
 * Convert UTM coordinates to Lat/Lng (WGS84)
 */
export function utmToLatLng(utm: UTMCoordinate): LatLng {
  const { easting, northing, epsg } = utm;

  // Convert using proj4
  const [lng, lat] = proj4(epsg, 'EPSG:4326', [easting, northing]);

  return {
    lat: Math.round(lat * 1000000) / 1000000, // Round to 6 decimals
    lng: Math.round(lng * 1000000) / 1000000,
  };
}

/**
 * Validate if coordinates are within Germany
 */
export function isInGermany(latLng: LatLng): boolean {
  const { lat, lng } = latLng;

  // Approximate bounding box for Germany
  const minLat = 47.2;
  const maxLat = 55.1;
  const minLng = 5.8;
  const maxLng = 15.1;

  return lat >= minLat && lat <= maxLat && lng >= minLng && lng <= maxLng;
}

/**
 * Format UTM coordinates for display
 */
export function formatUTM(utm: UTMCoordinate): string {
  return `${utm.zone}N ${utm.easting.toFixed(2)}E ${utm.northing.toFixed(2)}N`;
}

/**
 * Format Lat/Lng for display
 */
export function formatLatLng(latLng: LatLng): string {
  return `${latLng.lat.toFixed(6)}° ${latLng.lng.toFixed(6)}°`;
}

/**
 * Calculate distance between two Lat/Lng points in meters (Haversine formula)
 */
export function distanceLatLng(point1: LatLng, point2: LatLng): number {
  const R = 6371000; // Earth radius in meters
  const dLat = (point2.lat - point1.lat) * Math.PI / 180;
  const dLng = (point2.lng - point1.lng) * Math.PI / 180;

  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(point1.lat * Math.PI / 180) * Math.cos(point2.lat * Math.PI / 180) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}
