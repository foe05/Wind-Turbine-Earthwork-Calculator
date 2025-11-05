/**
 * Type definitions for Geo-Engineering Platform
 */

// Coordinate types
export interface LatLng {
  lat: number;
  lng: number;
}

export interface UTMCoordinate {
  easting: number;
  northing: number;
  zone: number;
  epsg: string;
}

// DEM types
export interface DEMRequest {
  crs: string;
  center_x: number;
  center_y: number;
  buffer_meters: number;
}

export interface DEMResponse {
  dem_id: string;
  crs: string;
  center_x: number;
  center_y: number;
  bounds: {
    minx: number;
    miny: number;
    maxx: number;
    maxy: number;
  };
  tiles_count: number;
  cached: boolean;
}

// WKA Calculation types
export interface WKACalculationRequest {
  dem_id: string;
  center_x: number;
  center_y: number;
  foundation_diameter: number;
  foundation_depth: number;
  foundation_type: number;
  platform_length: number;
  platform_width: number;
  slope_width: number;
  slope_angle: number;
  optimization_method: 'mean' | 'min_cut' | 'balanced';
}

export interface WKACalculationResponse {
  site_id: string;
  center_x: number;
  center_y: number;
  foundation_volume: number;
  platform_height: number;
  platform_cut: number;
  platform_fill: number;
  slope_cut: number;
  slope_fill: number;
  total_cut: number;
  total_fill: number;
  platform_area: number;
}

// Cost calculation types
export interface CostCalculationRequest {
  foundation_volume: number;
  crane_cut: number;
  crane_fill: number;
  platform_area: number;
  cost_excavation: number;
  cost_transport: number;
  cost_disposal: number;
  cost_fill_material: number;
  cost_platform_prep: number;
  material_reuse: boolean;
  swell_factor: number;
  compaction_factor: number;
}

export interface CostCalculationResponse {
  total_cost: number;
  excavation_cost: number;
  disposal_cost: number;
  fill_cost: number;
  platform_prep_cost: number;
  material_balance: {
    available: number;
    required: number;
    surplus: number;
    deficit: number;
    reused: number;
  };
}

export interface CostRatesPreset {
  name: string;
  cost_excavation: number;
  cost_transport: number;
  cost_disposal: number;
  cost_fill_material: number;
  cost_platform_prep: number;
}

// Report types
export interface SiteData {
  id: string;
  coord_x: number;
  coord_y: number;
  foundation_volume: number;
  platform_height: number;
  platform_cut: number;
  platform_fill: number;
  slope_cut: number;
  slope_fill: number;
  total_cut: number;
  total_fill: number;
  platform_area: number;
}

export interface ReportRequest {
  project_name: string;
  sites: SiteData[];
  format: 'html' | 'pdf';
}

export interface ReportResponse {
  report_id: string;
  download_url: string;
  format: string;
  expires_at: string;
}

// Project types
export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  sites: WKASite[];
}

export interface WKASite {
  id: string;
  name: string;
  position: LatLng;
  utmPosition: UTMCoordinate;
  calculation?: WKACalculationResponse;
  cost?: CostCalculationResponse;
}

// UI State types
export interface AppState {
  currentProject: Project | null;
  selectedSite: WKASite | null;
  isCalculating: boolean;
  mapBounds: L.LatLngBounds | null;
}
