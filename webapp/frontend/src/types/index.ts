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

// Phase 2: Road Calculation types
export interface RoadCalculationRequest {
  dem_id: string;
  centerline: number[][];
  road_width: number;
  design_grade: number;
  cut_slope?: number;
  fill_slope?: number;
  profile_type?: string;
  station_interval?: number;
  start_elevation?: number;
  include_ditches?: boolean;
  ditch_width?: number;
  ditch_depth?: number;
}

export interface RoadCalculationResponse {
  road_length: number;
  total_cut: number;
  total_fill: number;
  net_volume: number;
  avg_cut_depth: number;
  avg_fill_depth: number;
  num_stations: number;
  station_interval: number;
  design_grade: number;
  road_width: number;
  profile_type: string;
  start_elevation: number;
  end_elevation: number;
  ditch_cut?: number;
  stations: StationData[];
}

export interface StationData {
  station: number;
  distance: number;
  x: number;
  y: number;
  ground_elevation: number;
  design_elevation: number;
  cut_depth: number;
  fill_depth: number;
  cut_area: number;
  fill_area: number;
}

// Phase 2: Solar Park types
export interface SolarCalculationRequest {
  dem_id: string;
  boundary: number[][];
  panel_length: number;
  panel_width: number;
  row_spacing: number;
  panel_tilt: number;
  foundation_type: string;
  grading_strategy: string;
  orientation?: number;
  access_road_width?: number;
  access_road_length?: number;
}

export interface SolarCalculationResponse {
  num_panels: number;
  panel_area: number;
  panel_density: number;
  site_area: number;
  foundation_volume: number;
  foundation_type: string;
  grading_cut: number;
  grading_fill: number;
  grading_strategy: string;
  access_road_cut: number;
  access_road_fill: number;
  access_road_length: number;
  total_cut: number;
  total_fill: number;
  net_volume: number;
  panel_positions: number[][];
}

// Phase 2: Terrain Analysis types
export interface TerrainAnalysisRequest {
  dem_id: string;
  polygon: number[][];
  analysis_type: string;
  resolution?: number;
  target_elevation?: number;
  optimization_method?: string;
  contour_interval?: number;
}

export interface TerrainAnalysisResponse {
  analysis_type: string;
  polygon_area: number;
  num_sample_points: number;
  resolution: number;
  optimal_elevation?: number;
  cut_volume?: number;
  fill_volume?: number;
  net_volume?: number;
  target_elevation?: number;
  min_elevation?: number;
  max_elevation?: number;
  avg_elevation?: number;
  statistics?: Record<string, any>;
  slope_analysis?: Record<string, any>;
  contour_data?: Record<string, any>;
}

// Phase 2: Extended Project types
export interface RoadProject {
  id: string;
  name: string;
  centerline: LatLng[];
  utmCenterline: Array<[number, number]>;
  calculation?: RoadCalculationResponse;
  cost?: CostCalculationResponse;
}

export interface SolarProject {
  id: string;
  name: string;
  boundary: LatLng[];
  utmBoundary: Array<[number, number]>;
  calculation?: SolarCalculationResponse;
  cost?: CostCalculationResponse;
}

export interface TerrainProject {
  id: string;
  name: string;
  polygon: LatLng[];
  utmPolygon: Array<[number, number]>;
  analysis?: TerrainAnalysisResponse;
}

// UI State types
export interface AppState {
  currentProject: Project | null;
  selectedSite: WKASite | null;
  isCalculating: boolean;
  mapBounds: L.LatLngBounds | null;
  activeTab: 'wka' | 'road' | 'solar' | 'terrain';
  roadProjects: RoadProject[];
  solarProjects: SolarProject[];
  terrainProjects: TerrainProject[];
}

// =============================================================================
// Phase 3: Project Management Types
// =============================================================================

export interface Project {
  id: string;
  user_id: string;
  use_case: 'wka' | 'road' | 'solar' | 'terrain';
  name: string;
  description?: string;
  crs: string;
  utm_zone: number;
  bounds?: any; // GeoJSON Polygon
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  // Statistics
  job_count?: number;
  completed_jobs?: number;
  last_calculation?: string;
}

export interface ProjectCreateRequest {
  name: string;
  description?: string;
  use_case: 'wka' | 'road' | 'solar' | 'terrain';
  crs: string;
  utm_zone: number;
  bounds?: any;
  metadata?: Record<string, any>;
}

export interface ProjectUpdateRequest {
  name?: string;
  description?: string;
  bounds?: any;
  metadata?: Record<string, any>;
}

// =============================================================================
// Phase 3: Jobs History Types
// =============================================================================

export interface JobHistory {
  id: string;
  project_id: string;
  project_name?: string;
  status: 'pending' | 'fetching_dem' | 'calculating' | 'computing_costs' | 'generating_report' | 'completed' | 'failed';
  progress: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  site_count?: number;
  created_at: string;
}

export interface JobDetails extends JobHistory {
  input_data: any;
  result_data?: any;
  report_url?: string;
  updated_at: string;
}

// =============================================================================
// Phase 3: Batch Upload Types
// =============================================================================

export interface SiteImport {
  name?: string;
  lat?: number;
  lng?: number;
  utm_x?: number;
  utm_y?: number;
  utm_zone?: number;
  foundation_diameter: number;
  foundation_depth: number;
  platform_length: number;
  platform_width: number;
}

export interface BatchUploadRequest {
  project_id: string;
  sites: SiteImport[];
  crs?: string;
  cost_params?: any;
  auto_start_jobs?: boolean;
}

export interface BatchUploadResponse {
  project_id: string;
  sites_imported: number;
  jobs_created: string[];
  errors: string[];
}
