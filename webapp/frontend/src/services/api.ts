/**
 * API Client for Geo-Engineering Platform
 * Communicates with API Gateway (Port 8000)
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  DEMRequest,
  DEMResponse,
  WKACalculationRequest,
  WKACalculationResponse,
  CostCalculationRequest,
  CostCalculationResponse,
  CostRatesPreset,
  ReportRequest,
  ReportResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to include auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );

    // Load token from localStorage
    this.loadToken();
  }

  // Auth methods
  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  loadToken() {
    const token = localStorage.getItem('auth_token');
    if (token) {
      this.token = token;
    }
  }

  async requestLogin(email: string) {
    const response = await this.client.post('/auth/request-login', { email });
    return response.data;
  }

  async verifyToken(token: string) {
    const response = await this.client.get(`/auth/verify/${token}`);
    if (response.data.access_token) {
      this.setToken(response.data.access_token);
    }
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  async logout() {
    try {
      await this.client.post('/auth/logout');
    } finally {
      this.clearToken();
    }
  }

  // DEM Service methods
  async fetchDEM(request: DEMRequest): Promise<DEMResponse> {
    const response = await this.client.post('/dem/fetch', request);
    return response.data;
  }

  async getDEM(demId: string): Promise<DEMResponse> {
    const response = await this.client.get(`/dem/${demId}`);
    return response.data;
  }

  async getDEMCacheStats() {
    const response = await this.client.get('/dem/cache/stats');
    return response.data;
  }

  // Calculation Service methods
  async calculateFoundationCircular(data: {
    diameter: number;
    depth: number;
    foundation_type: number;
  }) {
    const response = await this.client.post('/calc/foundation/circular', data);
    return response.data;
  }

  async calculatePlatformRectangle(data: {
    dem_id: string;
    center_x: number;
    center_y: number;
    length: number;
    width: number;
    slope_width: number;
    slope_angle: number;
    optimization_method: string;
  }) {
    const response = await this.client.post('/calc/platform/rectangle', data);
    return response.data;
  }

  async calculateWKASite(request: WKACalculationRequest): Promise<WKACalculationResponse> {
    const response = await this.client.post('/calc/wka/site', request);
    return response.data;
  }

  // Phase 2: Road Calculation methods
  async calculateRoad(data: {
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
  }) {
    const response = await this.client.post('/road/calculate', data);
    return response.data;
  }

  async getRoadProfileTypes() {
    const response = await this.client.get('/road/profile-types');
    return response.data;
  }

  // Phase 2: Solar Park Calculation methods
  async calculateSolar(data: {
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
  }) {
    const response = await this.client.post('/solar/calculate', data);
    return response.data;
  }

  async getSolarFoundationTypes() {
    const response = await this.client.get('/solar/foundation-types');
    return response.data;
  }

  async getSolarGradingStrategies() {
    const response = await this.client.get('/solar/grading-strategies');
    return response.data;
  }

  // Phase 2: Terrain Analysis methods
  async analyzeTerrain(data: {
    dem_id: string;
    polygon: number[][];
    analysis_type: string;
    resolution?: number;
    target_elevation?: number;
    optimization_method?: string;
    contour_interval?: number;
  }) {
    const response = await this.client.post('/terrain/analyze', data);
    return response.data;
  }

  async getTerrainAnalysisTypes() {
    const response = await this.client.get('/terrain/analysis-types');
    return response.data;
  }

  async getTerrainOptimizationMethods() {
    const response = await this.client.get('/terrain/optimization-methods');
    return response.data;
  }

  // Cost Service methods
  async calculateCosts(request: CostCalculationRequest): Promise<CostCalculationResponse> {
    const response = await this.client.post('/costs/calculate', request);
    return response.data;
  }

  async getCostPresets(): Promise<CostRatesPreset[]> {
    const response = await this.client.get('/costs/presets');
    return response.data;
  }

  // Report Service methods
  async generateReport(request: ReportRequest): Promise<ReportResponse> {
    const response = await this.client.post('/report/generate', request);
    return response.data;
  }

  async downloadReport(reportId: string, filename: string): Promise<Blob> {
    const response = await this.client.get(`/report/download/${reportId}/${filename}`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // Gateway health check
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }

  async getServices() {
    const response = await this.client.get('/services');
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
