import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Use nginx proxy at /api/ which forwards to backend:8000
// This avoids CORS issues and works in Docker
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

// System client ID constant (matches backend)
const SYSTEM_CLIENT_ID = '00000000-0000-0000-0000-000000000001';

/**
 * Helper function to conditionally add client_id to query params.
 * For non-System clients, adds client_id filter (backend RLS will also enforce this).
 * For System clients and Admins, relies entirely on backend RLS (no client_id filter).
 * 
 * @param filters - Existing filters object
 * @param userClientId - Current user's client_id
 * @param userRole - Current user's role
 * @returns Filters object with client_id added if needed
 */
export function addClientFilterIfNeeded(
  filters: Record<string, string | undefined> = {},
  userClientId?: string,
  userRole?: string
): Record<string, string | undefined> {
  // Admins and System client users see all data (rely on RLS)
  if (userRole === 'Administrator' || userClientId === SYSTEM_CLIENT_ID) {
    return filters;
  }
  
  // Regular client users: add client_id filter (though RLS will also enforce this)
  // This is optional but can help with UI clarity and performance hints
  if (userClientId) {
    // Only add if not already present (don't override explicit filters)
    if (!filters.client_id) {
      filters.client_id = userClientId;
    }
  }
  
  return filters;
}

// Types for eligible samples with prioritization
export interface EligibleSample {
  id: string;
  name: string;
  description?: string;
  due_date?: string;
  received_date?: string;
  date_sampled?: string;
  sample_type: string;
  status: string;
  matrix: string;
  project_id: string;
  qc_type?: string;
  // Prioritization fields
  days_until_expiration?: number;
  days_until_due?: number;
  is_expired: boolean;
  is_overdue: boolean;
  expiration_warning?: string;
  // Analysis context
  shelf_life?: number;
  // Project context
  project_name?: string;
  project_due_date?: string;
  effective_due_date?: string;
}

export interface EligibleSamplesResponse {
  samples: EligibleSample[];
  total: number;
  page: number;
  size: number;
  pages: number;
  warnings: string[];
}

// Types for batch compatibility validation with expiration warnings
export interface ExpiredSampleWarning {
  sample_id: string;
  sample_name: string;
  days_expired: number;
  expiration_date: string;
}

export interface ExpiringSoonSampleWarning {
  sample_id: string;
  sample_name: string;
  days_until_expiration: number;
  expiration_date: string;
}

export interface BatchCompatibilityWarning {
  type: 'expired_samples' | 'expiring_soon';
  message: string;
  samples: ExpiredSampleWarning[] | ExpiringSoonSampleWarning[];
}

/** Dry-run promote-on-publish plan (GET /v1/lims-runs/{id}/promotion/preview). */
export interface PromotionPreviewItem {
  action: 'create' | 'update' | 'conflict' | 'skip' | string;
  sample_id?: string | null;
  test_id?: string | null;
  analyte_id?: string | null;
  analyte_name?: string | null;
  raw_result?: string | null;
  replicate?: number;
  column_key?: string | null;
  match_via?: string | null;
  message?: string | null;
  lims_run_data_id?: string | null;
}

export interface PromotionPreview {
  run_id: string;
  analysis_id?: string | null;
  will_promote: boolean;
  create_count: number;
  update_count: number;
  conflict_count: number;
  skip_count: number;
  unresolved_columns: string[];
  missing_sample_rows: number;
  errors: string[];
  items: PromotionPreviewItem[];
  items_truncated?: boolean;
}

export interface BatchCompatibilityResult {
  compatible: boolean;
  error?: string;
  details?: {
    projects: string[];
    common_analyses?: string[];
    analyses?: string[];
    suggestion?: string;
  };
  warnings?: BatchCompatibilityWarning[];
}

export class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor: auth token + multipart FormData handling
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        // Default Content-Type is application/json. For FormData the browser must set
        // multipart/form-data WITH boundary — otherwise FastAPI returns 422 on File/Form.
        if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
          if (config.headers && typeof (config.headers as any).set === 'function') {
            (config.headers as any).delete('Content-Type');
          } else if (config.headers) {
            delete (config.headers as any)['Content-Type'];
            delete (config.headers as any)['content-type'];
          }
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        // Don't auto-redirect on 401 during login - let the login page handle it
        if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
          localStorage.removeItem('token');
          // Only redirect if not already on login page
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  setAuthToken(token: string | null) {
    if (token) {
      this.api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete this.api.defaults.headers.common['Authorization'];
    }
  }

  // Auth endpoints
  async login(username: string, password: string) {
    const response: AxiosResponse = await this.api.post('/auth/login', {
      username,
      password,
    });
    return response.data;
  }

  async getCurrentUser() {
    const response: AxiosResponse = await this.api.get('/auth/me');
    return response.data;
  }

  // Sample endpoints
  async getSamples(filters?: Record<string, string | undefined>) {
    const response: AxiosResponse = await this.api.get('/samples', {
      params: filters,
    });
    // API returns SampleListResponse with {samples, total, page, size, pages}
    // Extract the samples array for the frontend
    return response.data.samples || response.data;
  }

  async getSample(id: string) {
    const response: AxiosResponse = await this.api.get(`/samples/${id}`);
    return response.data;
  }

  async createSample(sampleData: any) {
    const response: AxiosResponse = await this.api.post('/samples', sampleData);
    return response.data;
  }

  async accessionSample(sampleData: any) {
    const response: AxiosResponse = await this.api.post('/samples/accession', sampleData);
    return response.data;
  }

  async bulkAccessionSamples(bulkData: {
    due_date: string;
    received_date: string;
    sample_type: string;
    matrix: string;
    client_id: string;
    client_project_id?: string;
    qc_type?: string;
    assigned_tests: string[];
    battery_id?: string;
    container_type_id: string;
    uniques: Array<{
      name?: string;
      client_sample_id?: string;
      container_name: string;
      temperature?: number;
      anomalies?: string;
      description?: string;
    }>;
    auto_name_prefix?: string;
    auto_name_start?: number;
  }) {
    const response: AxiosResponse = await this.api.post('/samples/bulk-accession', bulkData);
    return response.data;
  }

  async updateSample(id: string, sampleData: any) {
    const response: AxiosResponse = await this.api.patch(`/samples/${id}`, sampleData);
    return response.data;
  }

  /**
   * Get eligible samples with prioritization based on expiration and due dates.
   * 
   * Returns samples sorted by:
   * 1. days_until_expiration ASC NULLS LAST (most urgent first)
   * 2. days_until_due ASC NULLS LAST (earliest due first)
   * 
   * @param filters - Optional filters for eligible samples
   * @param filters.test_ids - Comma-separated analysis IDs to filter by
   * @param filters.project_id - Filter by specific project
   * @param filters.include_expired - If true, includes expired samples (default: false)
   * @param filters.page - Page number (default: 1)
   * @param filters.size - Page size (default: 10)
   */
  async getEligibleSamples(filters?: {
    test_ids?: string;
    project_id?: string;
    include_expired?: boolean;
    page?: number;
    size?: number;
  }): Promise<EligibleSamplesResponse> {
    const response: AxiosResponse = await this.api.get('/samples/eligible', {
      params: filters,
    });
    return response.data;
  }

  // Test endpoints
  async getTests(filters?: { sample_id?: string; status?: string }) {
    const response: AxiosResponse = await this.api.get('/tests', {
      params: filters,
    });
    return response.data;
  }

  async getTest(id: string) {
    const response: AxiosResponse = await this.api.get(`/tests/${id}`);
    return response.data;
  }

  async getTestsByBatch(batchId: string) {
    const response: AxiosResponse = await this.api.get(`/batches/${batchId}/tests`);
    return response.data;
  }

  async createTest(testData: any) {
    const response: AxiosResponse = await this.api.post('/tests', testData);
    return response.data;
  }

  async updateTest(id: string, testData: any) {
    const response: AxiosResponse = await this.api.patch(`/tests/${id}`, testData);
    return response.data;
  }

  // Container endpoints
  async getContainers(filters?: { type_id?: string; parent_container_id?: string; project_ids?: string[] }) {
    const params: any = { ...filters };
    // Handle project_ids array for cross-project queries
    if (filters?.project_ids && Array.isArray(filters.project_ids)) {
      params.project_ids = filters.project_ids.join(',');
    }
    const response: AxiosResponse = await this.api.get('/containers', {
      params,
    });
    return response.data;
  }

  async getContainer(id: string) {
    const response: AxiosResponse = await this.api.get(`/containers/${id}`);
    return response.data;
  }

  async createContainer(containerData: any) {
    const response: AxiosResponse = await this.api.post('/containers', containerData);
    return response.data;
  }

  async updateContainer(id: string, containerData: any) {
    const response: AxiosResponse = await this.api.patch(`/containers/${id}`, containerData);
    return response.data;
  }

  // Contents endpoints
  async createContent(containerId: string, contentData: any) {
    const response: AxiosResponse = await this.api.post(`/containers/${containerId}/contents`, contentData);
    return response.data;
  }

  async updateContent(id: string, contentData: any) {
    const response: AxiosResponse = await this.api.patch(`/contents/${id}`, contentData);
    return response.data;
  }

  async deleteContent(id: string) {
    const response: AxiosResponse = await this.api.delete(`/contents/${id}`);
    return response.data;
  }

  // Analysis endpoints
  async getAnalyses(filters?: { search?: string; active?: boolean; page?: number; size?: number }) {
    const response: AxiosResponse = await this.api.get('/analyses', {
      params: filters,
    });
    // API returns AnalysisListResponse with {analyses, total, page, size, pages}
    return response.data;
  }

  /**
   * Normalize getAnalyses() payload to a plain list.
   * Backend returns { analyses, total, page, size, pages }; some callers still expect an array.
   */
  static unwrapAnalysesList(response: any): any[] {
    if (!response) return [];
    if (Array.isArray(response)) return response;
    if (Array.isArray(response.analyses)) return response.analyses;
    return [];
  }

  /**
   * Turn FastAPI/axios errors into a string safe for React text nodes.
   * Validation 422 bodies are arrays of { type, loc, msg, input, ctx }.
   */
  static formatError(err: any, fallback: string): string {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return (
        detail
          .map((d: any) => {
            if (typeof d === 'string') return d;
            if (d?.msg) {
              const loc = Array.isArray(d.loc)
                ? d.loc.filter((x: any) => x !== 'body' && x !== 'query').join('.')
                : '';
              return loc ? `${loc}: ${d.msg}` : d.msg;
            }
            return null;
          })
          .filter(Boolean)
          .join('; ') || fallback
      );
    }
    if (detail && typeof detail === 'object') {
      if (typeof detail.message === 'string') {
        const extra =
          Array.isArray(detail.errors) && detail.errors.length
            ? ` ${detail.errors.slice(0, 3).join('; ')}`
            : '';
        return `${detail.message}${extra}`;
      }
      try {
        return JSON.stringify(detail);
      } catch {
        return fallback;
      }
    }
    if (typeof err?.message === 'string' && err.message) return err.message;
    return fallback;
  }

  async getAnalysis(id: string) {
    const response: AxiosResponse = await this.api.get(`/analyses/${id}`);
    return response.data;
  }

  async createAnalysis(analysisData: any) {
    const response: AxiosResponse = await this.api.post('/analyses', analysisData);
    return response.data;
  }

  async updateAnalysis(id: string, analysisData: any) {
    const response: AxiosResponse = await this.api.patch(`/analyses/${id}`, analysisData);
    return response.data;
  }

  async deleteAnalysis(id: string) {
    const response: AxiosResponse = await this.api.delete(`/analyses/${id}`);
    return response.data;
  }

  async getAnalysisAnalytes(analysisId: string) {
    const response: AxiosResponse = await this.api.get(`/analyses/${analysisId}/analytes`);
    return response.data;
  }

  async updateAnalysisAnalytes(analysisId: string, analyteIds: string[]) {
    const response: AxiosResponse = await this.api.put(`/analyses/${analysisId}/analytes`, {
      analyte_ids: analyteIds,
    });
    return response.data;
  }

  async linkAnalytesToAnalysis(analysisId: string, analyteIds: string[]) {
    const response: AxiosResponse = await this.api.post(`/analyses/${analysisId}/analytes`, {
      analyte_ids: analyteIds,
    });
    return response.data;
  }

  async unlinkAnalyteFromAnalysis(analysisId: string, analyteId: string) {
    const response: AxiosResponse = await this.api.delete(`/analyses/${analysisId}/analytes/${analyteId}`);
    return response.data;
  }

  // Analysis-Analyte junction endpoints (for configuring rules)
  async getAnalysisAnalyteRules(analysisId: string) {
    const response: AxiosResponse = await this.api.get(`/analyses/${analysisId}/analyte-rules`);
    return response.data;
  }

  async createAnalysisAnalyteRule(analysisId: string, ruleData: any) {
    const response: AxiosResponse = await this.api.post(`/analyses/${analysisId}/analyte-rules`, ruleData);
    return response.data;
  }

  async updateAnalysisAnalyteRule(analysisId: string, analyteId: string, ruleData: any) {
    const response: AxiosResponse = await this.api.patch(`/analyses/${analysisId}/analyte-rules/${analyteId}`, ruleData);
    return response.data;
  }

  async deleteAnalysisAnalyteRule(analysisId: string, analyteId: string) {
    const response: AxiosResponse = await this.api.delete(`/analyses/${analysisId}/analyte-rules/${analyteId}`);
    return response.data;
  }

  // List endpoints for dropdowns
  async getListEntries(listName: string) {
    const response: AxiosResponse = await this.api.get(`/lists/${listName}/entries`);
    return response.data;
  }

  // Units endpoints
  async getUnits() {
    const response: AxiosResponse = await this.api.get('/units');
    return response.data;
  }

  async createUnit(unitData: any) {
    const response: AxiosResponse = await this.api.post('/units', unitData);
    return response.data;
  }

  async updateUnit(id: string, unitData: any) {
    const response: AxiosResponse = await this.api.patch(`/units/${id}`, unitData);
    return response.data;
  }

  async deleteUnit(id: string) {
    const response: AxiosResponse = await this.api.delete(`/units/${id}`);
    return response.data;
  }

  // Instrument types / instruments / CRO sources (data-parsers P0)
  async getInstrumentTypes(params?: { search?: string; active?: boolean }) {
    const response: AxiosResponse = await this.api.get('/v1/instrument-types', { params });
    return response.data;
  }

  async createInstrumentType(data: {
    name: string;
    description?: string;
    vendor?: string;
    model?: string;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.post('/v1/instrument-types', data);
    return response.data;
  }

  async updateInstrumentType(
    id: string,
    data: Partial<{
      name: string;
      description?: string;
      vendor?: string;
      model?: string;
      active?: boolean;
    }>
  ) {
    const response: AxiosResponse = await this.api.patch(`/v1/instrument-types/${id}`, data);
    return response.data;
  }

  async deleteInstrumentType(id: string) {
    const response: AxiosResponse = await this.api.delete(`/v1/instrument-types/${id}`);
    return response.data;
  }

  async getInstruments(params?: {
    search?: string;
    instrument_type_id?: string;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.get('/v1/instruments', { params });
    return response.data;
  }

  async createInstrument(data: {
    name: string;
    description?: string;
    instrument_type_id: string;
    serial_number?: string;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.post('/v1/instruments', data);
    return response.data;
  }

  async updateInstrument(
    id: string,
    data: Partial<{
      name: string;
      description?: string;
      instrument_type_id: string;
      serial_number?: string;
      active?: boolean;
    }>
  ) {
    const response: AxiosResponse = await this.api.patch(`/v1/instruments/${id}`, data);
    return response.data;
  }

  async deleteInstrument(id: string) {
    const response: AxiosResponse = await this.api.delete(`/v1/instruments/${id}`);
    return response.data;
  }

  async getCroSources(params?: { search?: string; active?: boolean }) {
    const response: AxiosResponse = await this.api.get('/v1/cro-sources', { params });
    return response.data;
  }

  async createCroSource(data: {
    name: string;
    description?: string;
    client_id?: string | null;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.post('/v1/cro-sources', data);
    return response.data;
  }

  async updateCroSource(
    id: string,
    data: Partial<{
      name: string;
      description?: string;
      client_id?: string | null;
      active?: boolean;
    }>
  ) {
    const response: AxiosResponse = await this.api.patch(`/v1/cro-sources/${id}`, data);
    return response.data;
  }

  async deleteCroSource(id: string) {
    const response: AxiosResponse = await this.api.delete(`/v1/cro-sources/${id}`);
    return response.data;
  }

  // Data parsers (P1)
  async getDataParsers(params?: {
    active_only?: boolean;
    instrument_id?: string;
    cro_source_id?: string;
    analysis_id?: string;
    version_group_id?: string;
  }) {
    const response: AxiosResponse = await this.api.get('/v1/data-parsers', { params });
    return response.data;
  }

  async getDataParser(id: string) {
    const response: AxiosResponse = await this.api.get(`/v1/data-parsers/${id}`);
    return response.data;
  }

  async createDataParser(data: any) {
    const response: AxiosResponse = await this.api.post('/v1/data-parsers', data);
    return response.data;
  }

  async activateDataParser(id: string) {
    const response: AxiosResponse = await this.api.post(`/v1/data-parsers/${id}/activate`);
    return response.data;
  }

  async createDataParserVersion(versionGroupId: string, data: any) {
    const response: AxiosResponse = await this.api.post(
      `/v1/data-parsers/groups/${versionGroupId}/versions`,
      data
    );
    return response.data;
  }

  async testDataParserConfig(parserConfig: any, files: File[]) {
    const form = new FormData();
    form.append('parser_config', JSON.stringify(parserConfig));
    // Same field name repeated — FastAPI List[UploadFile] = File(...)
    files.forEach((f) => form.append('files', f));
    const response: AxiosResponse = await this.api.post('/v1/data-parsers/test', form);
    return response.data;
  }

  async importLimsRunFile(
    runId: string,
    file: File,
    meta: { instrument_id?: string; cro_source_id?: string; parser_id?: string }
  ) {
    const form = new FormData();
    form.append('file', file);
    if (meta.instrument_id) form.append('instrument_id', meta.instrument_id);
    if (meta.cro_source_id) form.append('cro_source_id', meta.cro_source_id);
    if (meta.parser_id) form.append('parser_id', meta.parser_id);
    const response: AxiosResponse = await this.api.post(
      `/v1/lims-runs/${runId}/import-file`,
      form
    );
    return response.data;
  }

  async getLimsRunImports(runId: string) {
    const response: AxiosResponse = await this.api.get(`/v1/lims-runs/${runId}/imports`);
    return response.data;
  }

  // Container types endpoints
  async getContainerTypes() {
    const response: AxiosResponse = await this.api.get('/containers/types');
    return response.data;
  }

  async createContainerType(containerTypeData: any) {
    const response: AxiosResponse = await this.api.post('/containers/types', containerTypeData);
    return response.data;
  }

  async updateContainerType(id: string, containerTypeData: any) {
    const response: AxiosResponse = await this.api.patch(`/containers/types/${id}`, containerTypeData);
    return response.data;
  }

  async deleteContainerType(id: string) {
    const response: AxiosResponse = await this.api.delete(`/containers/types/${id}`);
    return response.data;
  }

  // Lists endpoints (admin CRUD)
  async getLists() {
    const response: AxiosResponse = await this.api.get('/lists');
    return response.data;
  }

  async createList(listData: any) {
    const response: AxiosResponse = await this.api.post('/lists', listData);
    return response.data;
  }

  async updateList(id: string, listData: any) {
    const response: AxiosResponse = await this.api.patch(`/lists/${id}`, listData);
    return response.data;
  }

  async deleteList(id: string) {
    const response: AxiosResponse = await this.api.delete(`/lists/${id}`);
    return response.data;
  }

  async createListEntry(listName: string, entryData: any) {
    const response: AxiosResponse = await this.api.post(`/lists/${listName}/entries`, entryData);
    return response.data;
  }

  async updateListEntry(listName: string, entryId: string, entryData: any) {
    const response: AxiosResponse = await this.api.patch(`/lists/${listName}/entries/${entryId}`, entryData);
    return response.data;
  }

  async deleteListEntry(listName: string, entryId: string) {
    const response: AxiosResponse = await this.api.delete(`/lists/${listName}/entries/${entryId}`);
    return response.data;
  }

  // Project endpoints
  async getProjects(filters?: { status?: string; client_id?: string; page?: number; size?: number }) {
    const response: AxiosResponse = await this.api.get('/projects', {
      params: filters,
    });
    // API returns ProjectListResponse with {projects, total, page, size, pages}
    // Return the full response for pagination support
    return response.data;
  }

  async getProject(id: string) {
    const response: AxiosResponse = await this.api.get(`/projects/${id}`);
    return response.data;
  }

  async createProject(projectData: {
    name: string;
    description?: string;
    start_date: string;
    client_id: string;
    client_project_id?: string;
    status: string;
    custom_attributes?: Record<string, any>;
  }) {
    const response: AxiosResponse = await this.api.post('/projects', projectData);
    return response.data;
  }

  async updateProject(id: string, projectData: {
    name?: string;
    description?: string;
    start_date?: string;
    client_id?: string;
    client_project_id?: string;
    status?: string;
    custom_attributes?: Record<string, any>;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.patch(`/projects/${id}`, projectData);
    return response.data;
  }

  async deleteProject(id: string) {
    const response: AxiosResponse = await this.api.delete(`/projects/${id}`);
    return response.data;
  }

  // Aliquot/Derivative endpoints
  async createAliquot(aliquotData: any) {
    const response: AxiosResponse = await this.api.post('/samples/aliquot', aliquotData);
    return response.data;
  }

  async createDerivative(derivativeData: any) {
    const response: AxiosResponse = await this.api.post('/samples/derivative', derivativeData);
    return response.data;
  }

  // Batch endpoints
  async getBatches(filters?: { status?: string; type?: string }) {
    const response: AxiosResponse = await this.api.get('/batches', {
      params: filters,
    });
    // API returns BatchListResponse with {batches, total, page, size, pages}
    // Extract the batches array for the frontend
    return response.data.batches || response.data;
  }

  async getBatch(batchId: string) {
    const response: AxiosResponse = await this.api.get(`/batches/${batchId}`);
    return response.data;
  }

  async createBatch(batchData: any) {
    const response: AxiosResponse = await this.api.post('/batches', batchData);
    return response.data;
  }

  async validateBatchCompatibility(data: { container_ids: string[] }): Promise<BatchCompatibilityResult> {
    const response: AxiosResponse = await this.api.post('/batches/validate-compatibility', data);
    return response.data;
  }

  async updateBatch(id: string, batchData: any) {
    const response: AxiosResponse = await this.api.patch(`/batches/${id}`, batchData);
    return response.data;
  }

  async getBatchContainers(batchId: string) {
    const response: AxiosResponse = await this.api.get(`/batches/${batchId}/containers`);
    return response.data;
  }

  async addContainerToBatch(batchId: string, containerData: any) {
    const response: AxiosResponse = await this.api.post(`/batches/${batchId}/containers`, containerData);
    return response.data;
  }

  async removeContainerFromBatch(batchId: string, containerId: string) {
    const response: AxiosResponse = await this.api.delete(`/batches/${batchId}/containers/${containerId}`);
    return response.data;
  }

  // Results endpoints
  async getResults(filters?: { batch_id?: string; test_id?: string; analyte_id?: string }) {
    const response: AxiosResponse = await this.api.get('/results', {
      params: filters,
    });
    return response.data;
  }

  async createResult(resultData: any) {
    const response: AxiosResponse = await this.api.post('/results', resultData);
    return response.data;
  }

  async updateResult(id: string, resultData: any) {
    const response: AxiosResponse = await this.api.patch(`/results/${id}`, resultData);
    return response.data;
  }

  async getBatchResults(batchId: string, testId?: string) {
    const response: AxiosResponse = await this.api.get(`/batches/${batchId}/results`, {
      params: { test_id: testId },
    });
    return response.data;
  }

  async enterBatchResults(batchId: string, resultsData: any) {
    // US-28: Batch Results Entry endpoint
    const response: AxiosResponse = await this.api.post(`/results/batch`, resultsData);
    return response.data;
  }

  // Analyte endpoints
  async getAnalytes(filters?: { search?: string; active?: boolean; page?: number; size?: number }) {
    const response: AxiosResponse = await this.api.get('/analytes', {
      params: filters,
    });
    // API returns AnalyteListResponse with {analytes, total, page, size, pages}
    // Extract array for consistency with other list endpoints (samples, batches, etc.)
    return response.data?.analytes || response.data || [];
  }

  async getAnalyte(id: string) {
    const response: AxiosResponse = await this.api.get(`/analytes/${id}`);
    return response.data;
  }

  async createAnalyte(analyteData: any) {
    const response: AxiosResponse = await this.api.post('/analytes', analyteData);
    return response.data;
  }

  async updateAnalyte(id: string, analyteData: any) {
    const response: AxiosResponse = await this.api.patch(`/analytes/${id}`, analyteData);
    return response.data;
  }

  async getAnalyteAliases(analyteId: string) {
    const response: AxiosResponse = await this.api.get(`/analytes/${analyteId}/aliases`);
    return response.data;
  }

  async addAnalyteAlias(analyteId: string, alias: string) {
    const response: AxiosResponse = await this.api.post(`/analytes/${analyteId}/aliases`, {
      alias,
    });
    return response.data;
  }

  async deleteAnalyteAlias(analyteId: string, aliasId: string) {
    await this.api.delete(`/analytes/${analyteId}/aliases/${aliasId}`);
  }

  async deleteAnalyte(id: string) {
    const response: AxiosResponse = await this.api.delete(`/analytes/${id}`);
    return response.data;
  }

  // Test Battery endpoints
  async getTestBatteries(filters?: { name?: string; page?: number; size?: number }) {
    const response: AxiosResponse = await this.api.get('/test-batteries', {
      params: filters,
    });
    return response.data;
  }

  async getTestBattery(id: string) {
    const response: AxiosResponse = await this.api.get(`/test-batteries/${id}`);
    return response.data;
  }

  async createTestBattery(batteryData: { name: string; description?: string }) {
    const response: AxiosResponse = await this.api.post('/test-batteries', batteryData);
    return response.data;
  }

  async updateTestBattery(id: string, batteryData: { name?: string; description?: string; active?: boolean }) {
    const response: AxiosResponse = await this.api.patch(`/test-batteries/${id}`, batteryData);
    return response.data;
  }

  async deleteTestBattery(id: string) {
    const response: AxiosResponse = await this.api.delete(`/test-batteries/${id}`);
    return response.data;
  }

  async getBatteryAnalyses(batteryId: string) {
    const response: AxiosResponse = await this.api.get(`/test-batteries/${batteryId}/analyses`);
    return response.data;
  }

  async addAnalysisToBattery(batteryId: string, analysisData: { analysis_id: string; sequence: number; optional: boolean }) {
    const response: AxiosResponse = await this.api.post(`/test-batteries/${batteryId}/analyses`, analysisData);
    return response.data;
  }

  async updateBatteryAnalysis(batteryId: string, analysisId: string, analysisData: { sequence?: number; optional?: boolean }) {
    const response: AxiosResponse = await this.api.patch(`/test-batteries/${batteryId}/analyses/${analysisId}`, analysisData);
    return response.data;
  }

  async removeAnalysisFromBattery(batteryId: string, analysisId: string) {
    const response: AxiosResponse = await this.api.delete(`/test-batteries/${batteryId}/analyses/${analysisId}`);
    return response.data;
  }

  // Users endpoints (admin CRUD)
  async getUsers(filters?: { role_id?: string; client_id?: string; include_inactive?: boolean }) {
    const response: AxiosResponse = await this.api.get('/users', {
      params: filters,
    });
    return response.data;
  }

  async createUser(userData: any) {
    const response: AxiosResponse = await this.api.post('/users', userData);
    return response.data;
  }

  async updateUser(id: string, userData: any) {
    const response: AxiosResponse = await this.api.patch(`/users/${id}`, userData);
    return response.data;
  }

  async deleteUser(id: string) {
    const response: AxiosResponse = await this.api.delete(`/users/${id}`);
    return response.data;
  }

  // Roles endpoints
  async getRoles() {
    const response: AxiosResponse = await this.api.get('/roles');
    return response.data;
  }

  async createRole(roleData: any) {
    const response: AxiosResponse = await this.api.post('/roles', roleData);
    return response.data;
  }

  async updateRole(id: string, roleData: any) {
    const response: AxiosResponse = await this.api.patch(`/roles/${id}`, roleData);
    return response.data;
  }

  async deleteRole(id: string) {
    const response: AxiosResponse = await this.api.delete(`/roles/${id}`);
    return response.data;
  }

  async getRolePermissions(roleId: string) {
    const response: AxiosResponse = await this.api.get(`/roles/${roleId}/permissions`);
    return response.data;
  }

  async updateRolePermissions(roleId: string, permissionIds: string[]) {
    const response: AxiosResponse = await this.api.put(`/roles/${roleId}/permissions`, {
      permission_ids: permissionIds,
    });
    return response.data;
  }

  // Permissions endpoints
  async getPermissions() {
    const response: AxiosResponse = await this.api.get('/permissions');
    return response.data;
  }

  async createPermission(permissionData: any) {
    const response: AxiosResponse = await this.api.post('/permissions', permissionData);
    return response.data;
  }

  async updatePermission(id: string, permissionData: any) {
    const response: AxiosResponse = await this.api.patch(`/permissions/${id}`, permissionData);
    return response.data;
  }

  async deletePermission(id: string) {
    const response: AxiosResponse = await this.api.delete(`/permissions/${id}`);
    return response.data;
  }

  // Clients endpoints
  async getClients(filters?: { name?: string; active?: boolean }) {
    const response: AxiosResponse = await this.api.get('/clients', {
      params: filters,
    });
    return response.data;
  }

  async createClient(clientData: {
    name: string;
    description?: string;
    abbreviation?: string;
    billing_info?: Record<string, any>;
  }) {
    const response: AxiosResponse = await this.api.post('/clients', clientData);
    return response.data;
  }

  async updateClient(id: string, clientData: {
    name?: string;
    description?: string;
    abbreviation?: string;
    billing_info?: Record<string, any>;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.patch(`/clients/${id}`, clientData);
    return response.data;
  }

  async deleteClient(id: string) {
    // Soft delete via active=false
    const response: AxiosResponse = await this.api.delete(`/clients/${id}`);
    return response.data;
  }

  // Client Projects endpoints
  async getClientProjects(filters?: { client_id?: string; page?: number; size?: number }) {
    const response: AxiosResponse = await this.api.get('/client-projects', {
      params: filters,
    });
    return response.data;
  }

  async getClientProject(id: string) {
    const response: AxiosResponse = await this.api.get(`/client-projects/${id}`);
    return response.data;
  }

  async createClientProject(clientProjectData: {
    name: string;
    description?: string;
    client_id: string;
  }) {
    const response: AxiosResponse = await this.api.post('/client-projects', clientProjectData);
    return response.data;
  }

  async updateClientProject(id: string, clientProjectData: {
    name?: string;
    description?: string;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.patch(`/client-projects/${id}`, clientProjectData);
    return response.data;
  }

  async deleteClientProject(id: string) {
    const response: AxiosResponse = await this.api.delete(`/client-projects/${id}`);
    return response.data;
  }

  // FieldDefinitions (new modeled fields system)
  async getFieldDefinitions(filters?: {
    entity_type?: string;
    active?: boolean;
    page?: number;
    size?: number;
  }) {
    const response: AxiosResponse = await this.api.get('/admin/fields', {
      params: filters,
    });
    return response.data;
  }

  async getFieldDefinition(id: string) {
    const response: AxiosResponse = await this.api.get(`/admin/fields/${id}`);
    return response.data;
  }

  async createFieldDefinition(fieldData: {
    entity_type: string;
    name: string;
    display_name?: string;
    data_type: 'text' | 'number' | 'date' | 'boolean' | 'list';
    source_list_id?: string;
    is_required?: boolean;
    validation_rules?: Record<string, any>;
    description?: string;
    active?: boolean;
    is_materialized_column?: boolean;
    column_name?: string;
  }) {
    const response: AxiosResponse = await this.api.post('/admin/fields', fieldData);
    return response.data;
  }

  async updateFieldDefinition(
    id: string,
    fieldData: {
      entity_type?: string;
      name?: string;
      display_name?: string;
      data_type?: 'text' | 'number' | 'date' | 'boolean' | 'list';
      source_list_id?: string;
      is_required?: boolean;
      validation_rules?: Record<string, any>;
      description?: string;
      active?: boolean;
    }
  ) {
    const response: AxiosResponse = await this.api.patch(`/admin/fields/${id}`, fieldData);
    return response.data;
  }

  async deleteFieldDefinition(id: string) {
    const response: AxiosResponse = await this.api.delete(`/admin/fields/${id}`);
    return response.data;
  }

  // Custom Attributes config loading (used by forms for runtime custom fields)
  // Note: Admin management UI deleted (replaced by FieldDefinitions)
  async getCustomAttributeConfigs(filters?: {
    entity_type?: string;
    active?: boolean;
    page?: number;
    size?: number;
  }) {
    const response: AxiosResponse = await this.api.get('/admin/custom-attributes', {
      params: filters,
    });
    return response.data;
  }

  // Name Templates (used by forms for name generation)
  // Note: Admin management UI deleted
  async getNameTemplates(filters?: {
    entity_type?: string;
    active?: boolean;
    page?: number;
    size?: number;
  }) {
    const response: AxiosResponse = await this.api.get('/admin/name-templates', {
      params: filters,
    });
    return response.data;
  }

  async getNameTemplatesPreview(entity_type: string, client_id?: string, reference_date?: string) {
    const response: AxiosResponse = await this.api.get('/admin/name-templates/preview', {
      params: { entity_type, client_id, reference_date },
    });
    return response.data;
  }

  // Workflow templates (admin) and execute
  async getWorkflowTemplates(params?: { active?: boolean }) {
    const response: AxiosResponse = await this.api.get('/admin/workflow-templates', { params });
    return response.data;
  }

  async getWorkflowTemplate(id: string) {
    const response: AxiosResponse = await this.api.get(`/admin/workflow-templates/${id}`);
    return response.data;
  }

  async createWorkflowTemplate(data: {
    name: string;
    description?: string;
    active?: boolean;
    template_definition: Record<string, unknown>;
  }) {
    const response: AxiosResponse = await this.api.post('/admin/workflow-templates', data);
    return response.data;
  }

  async updateWorkflowTemplate(
    id: string,
    data: { name?: string; description?: string; active?: boolean; template_definition?: Record<string, unknown> }
  ) {
    const response: AxiosResponse = await this.api.patch(`/admin/workflow-templates/${id}`, data);
    return response.data;
  }

  async deleteWorkflowTemplate(id: string) {
    const response: AxiosResponse = await this.api.delete(`/admin/workflow-templates/${id}`);
    return response.data;
  }

  async executeWorkflow(templateId: string, body?: { name?: string; context?: Record<string, unknown> }) {
    const response: AxiosResponse = await this.api.post(`/workflows/execute/${templateId}`, body ?? {});
    return response.data;
  }

  async getGeneratedNamePreview(entity_type: string, client_id?: string, reference_date?: string) {
    try {
      const response: AxiosResponse = await this.api.get('/admin/name-templates/preview', {
        params: { entity_type, client_id, reference_date },
      });
      return response.data.preview;
    } catch (err) {
      // If endpoint doesn't exist, return null
      return null;
    }
  }

  /** Set the next value for an entity type's name sequence (e.g. sample, project). Requires config:edit. */
  async setSequenceStart(entity_type: string, start_value: number) {
    const response: AxiosResponse = await this.api.post(
      `/admin/sequences/${encodeURIComponent(entity_type)}/start`,
      { start_value }
    );
    return response.data;
  }

  // Help endpoints
  async getHelp(filters?: {
    role?: string;
    section?: string;
    page?: number;
    size?: number;
  }) {
    const config: any = {};
    if (filters && Object.keys(filters).length > 0) {
      config.params = filters;
      // Normalize role to slug format if provided (e.g., 'Lab Technician' -> 'lab-technician', 'Lab Manager' -> 'lab-manager')
      if (config.params.role) {
        config.params.role = config.params.role.toLowerCase().replace(' ', '-');
      }
    }
    const response: AxiosResponse = await this.api.get('/help', config);
    return response.data;
  }

  async getContextualHelp(section: string) {
    const response: AxiosResponse = await this.api.get('/help/contextual', {
      params: { section },
    });
    return response.data;
  }

  // Experiment endpoints (v1 API)
  async getExperiments(params?: {
    experiment_template_id?: string;
    status_id?: string;
    active?: boolean;
    mine?: boolean;
    page?: number;
    size?: number;
  }) {
    const response: AxiosResponse = await this.api.get('v1/experiments', { params });
    return response.data;
  }

  async getExperiment(id: string) {
    const response: AxiosResponse = await this.api.get(`v1/experiments/${id}`);
    return response.data;
  }

  async createExperiment(data: {
    name: string;
    description?: string;
    experiment_template_id?: string;
    status_id?: string;
    started_at?: string;
    completed_at?: string;
    custom_attributes?: Record<string, unknown>;
  }) {
    const response: AxiosResponse = await this.api.post('v1/experiments', data);
    return response.data;
  }

  async updateExperiment(id: string, data: {
    name?: string;
    description?: string;
    active?: boolean;
    experiment_template_id?: string;
    status_id?: string;
    started_at?: string;
    completed_at?: string;
    custom_attributes?: Record<string, unknown>;
  }) {
    const response: AxiosResponse = await this.api.patch(`v1/experiments/${id}`, data);
    return response.data;
  }

  async getExperimentLineage(id: string) {
    const response: AxiosResponse = await this.api.get(`v1/experiments/${id}/lineage`);
    return response.data;
  }

  async getSampleExperiments(sampleId: string) {
    const response: AxiosResponse = await this.api.get(`v1/experiments/by-sample/${sampleId}`);
    return response.data;
  }

  async linkSampleToExperiment(experimentId: string, data: {
    sample_id: string;
    role_in_experiment_id?: string;
    processing_conditions?: Record<string, unknown>;
    replicate_number?: number;
    test_id?: string;
    result_id?: string;
    custom_attributes?: Record<string, unknown>;
  }) {
    const response: AxiosResponse = await this.api.post(`v1/experiments/${experimentId}/samples`, data);
    return response.data;
  }

  async addExperimentDetailStep(experimentId: string, data: {
    detail_type: string;
    content?: Record<string, unknown>;
    sort_order?: number;
  }) {
    const response: AxiosResponse = await this.api.post(`v1/experiments/${experimentId}/details`, data);
    return response.data;
  }

  async linkExperiments(experimentId: string, linkedExperimentId: string) {
    const response: AxiosResponse = await this.api.post(`v1/experiments/${experimentId}/links`, {
      linked_experiment_id: linkedExperimentId,
    });
    return response.data;
  }

  // Experiment templates (v1 API)
  async getExperimentTemplates(params?: { active?: boolean; page?: number; size?: number }) {
    const response: AxiosResponse = await this.api.get('v1/experiment-templates', { params });
    return response.data;
  }

  async getExperimentTemplate(id: string) {
    const response: AxiosResponse = await this.api.get(`v1/experiment-templates/${id}`);
    return response.data;
  }

  async createExperimentTemplate(data: {
    name: string;
    description?: string;
    lifecycle_type?: string;
    template_definition?: Record<string, unknown>;
    custom_attributes?: Record<string, unknown>;
  }) {
    const response: AxiosResponse = await this.api.post('v1/experiment-templates', data);
    return response.data;
  }

  async updateExperimentTemplate(id: string, data: {
    name?: string;
    description?: string;
    active?: boolean;
    lifecycle_type?: string;
    template_definition?: Record<string, unknown>;
    custom_attributes?: Record<string, unknown>;
  }) {
    const response: AxiosResponse = await this.api.patch(`v1/experiment-templates/${id}`, data);
    return response.data;
  }

  async deleteExperimentTemplate(id: string) {
    await this.api.delete(`v1/experiment-templates/${id}`);
  }

  // ELN Processes (Phase 1–3) — definitions + instances + typed steps
  async getElnProcesses(params?: {
    active?: boolean;
    mine?: boolean;
    page?: number;
    size?: number;
  }) {
    const response: AxiosResponse = await this.api.get('v1/eln-processes', { params });
    return response.data;
  }

  async getElnProcess(id: string) {
    const response: AxiosResponse = await this.api.get(`v1/eln-processes/${id}`);
    return response.data;
  }

  async createElnProcess(data: {
    name: string;
    description?: string;
    status_id?: string;
    process_definition_id?: string;
    steps?: Array<{
      experiment_template_id: string;
      step_kind?: 'eln_experiment' | 'lims_run';
      execution_mode?: 'eln_experiment' | 'lims_run';
      name?: string;
      sort_order?: number;
    }>;
  }) {
    const response: AxiosResponse = await this.api.post('v1/eln-processes', data);
    return response.data;
  }

  async updateElnProcess(id: string, data: {
    name?: string;
    description?: string;
    active?: boolean;
    status_id?: string;
  }) {
    const response: AxiosResponse = await this.api.patch(`v1/eln-processes/${id}`, data);
    return response.data;
  }

  async deleteElnProcess(id: string) {
    await this.api.delete(`v1/eln-processes/${id}`);
  }

  async getElnProcessSteps(processId: string) {
    const response: AxiosResponse = await this.api.get(`v1/eln-processes/${processId}/steps`);
    return response.data;
  }

  async addElnProcessStep(processId: string, data: {
    experiment_template_id: string;
    step_kind?: 'eln_experiment' | 'lims_run';
    execution_mode?: 'eln_experiment' | 'lims_run';
    name?: string;
    sort_order?: number;
  }) {
    const response: AxiosResponse = await this.api.post(
      `v1/eln-processes/${processId}/steps`,
      data,
    );
    return response.data;
  }

  async updateElnProcessStep(
    processId: string,
    stepId: string,
    data: {
      name?: string;
      experiment_template_id?: string;
      experiment_id?: string;
      current_lims_run_id?: string;
      sort_order?: number;
      step_kind?: string;
      execution_mode?: string;
    },
  ) {
    const response: AxiosResponse = await this.api.patch(
      `v1/eln-processes/${processId}/steps/${stepId}`,
      data,
    );
    return response.data;
  }

  async removeElnProcessStep(processId: string, stepId: string) {
    await this.api.delete(`v1/eln-processes/${processId}/steps/${stepId}`);
  }

  async reorderElnProcessSteps(processId: string, stepIds: string[]) {
    const response: AxiosResponse = await this.api.post(
      `v1/eln-processes/${processId}/steps/reorder`,
      { step_ids: stepIds },
    );
    return response.data;
  }

  /** Start/materialize a step (Experiment or lazy LimsRun). */
  async startElnProcessStep(
    processId: string,
    stepId: string,
    data?: { name?: string; force_new?: boolean },
  ) {
    const response: AxiosResponse = await this.api.post(
      `v1/eln-processes/${processId}/steps/${stepId}/start`,
      data ?? {},
    );
    return response.data;
  }

  /** @deprecated Prefer startElnProcessStep */
  async instantiateElnProcessStep(
    processId: string,
    stepId: string,
    data?: { name?: string; force_new?: boolean },
  ) {
    return this.startElnProcessStep(processId, stepId, data);
  }

  async getElnProcessSamples(
    processId: string,
    params?: { current_step_id?: string; sample_status?: string },
  ) {
    const response: AxiosResponse = await this.api.get(
      `v1/eln-processes/${processId}/samples`,
      { params },
    );
    return response.data;
  }

  async assignElnProcessSamples(
    processId: string,
    data: { sample_ids: string[]; set_to_first_step?: boolean },
  ) {
    const response: AxiosResponse = await this.api.post(
      `v1/eln-processes/${processId}/samples`,
      data,
    );
    return response.data;
  }

  async removeElnProcessSample(processId: string, sampleId: string) {
    await this.api.delete(`v1/eln-processes/${processId}/samples/${sampleId}`);
  }

  async setElnProcessSampleStep(
    processId: string,
    sampleId: string,
    data: { step_id?: string | null; status?: string },
  ) {
    const response: AxiosResponse = await this.api.patch(
      `v1/eln-processes/${processId}/samples/${sampleId}/step`,
      data,
    );
    return response.data;
  }

  async advanceElnProcessSample(processId: string, sampleId: string) {
    const response: AxiosResponse = await this.api.post(
      `v1/eln-processes/${processId}/samples/${sampleId}/advance`,
    );
    return response.data;
  }

  // ELN Process Definitions (Phase 3)
  async getElnProcessDefinitions(params?: {
    active?: boolean;
    page?: number;
    size?: number;
  }) {
    const response: AxiosResponse = await this.api.get('v1/eln-process-definitions', {
      params,
    });
    return response.data;
  }

  async getElnProcessDefinition(id: string) {
    const response: AxiosResponse = await this.api.get(`v1/eln-process-definitions/${id}`);
    return response.data;
  }

  async createElnProcessDefinition(data: {
    name: string;
    description?: string;
    steps?: Array<{
      experiment_template_id: string;
      step_kind?: 'eln_experiment' | 'lims_run';
      execution_mode?: 'eln_experiment' | 'lims_run';
      name?: string;
      sort_order?: number;
    }>;
  }) {
    const response: AxiosResponse = await this.api.post('v1/eln-process-definitions', data);
    return response.data;
  }

  async updateElnProcessDefinition(
    id: string,
    data: { name?: string; description?: string; active?: boolean },
  ) {
    const response: AxiosResponse = await this.api.patch(
      `v1/eln-process-definitions/${id}`,
      data,
    );
    return response.data;
  }

  async addElnProcessDefinitionStep(
    definitionId: string,
    data: {
      experiment_template_id: string;
      step_kind?: 'eln_experiment' | 'lims_run';
      execution_mode?: 'eln_experiment' | 'lims_run';
      name?: string;
      sort_order?: number;
    },
  ) {
    const response: AxiosResponse = await this.api.post(
      `v1/eln-process-definitions/${definitionId}/steps`,
      data,
    );
    return response.data;
  }

  async instantiateFromElnProcessDefinition(
    definitionId: string,
    data?: {
      name?: string;
      description?: string;
      sample_ids?: string[];
      set_to_first_step?: boolean;
    },
  ) {
    const response: AxiosResponse = await this.api.post(
      `v1/eln-process-definitions/${definitionId}/instantiate`,
      data ?? {},
    );
    return response.data;
  }

  /** Sample-scoped process journey (Decision #7) */
  async getSampleJourney(sampleId: string) {
    const response: AxiosResponse = await this.api.get(`v1/samples/${sampleId}/journey`);
    return response.data;
  }

  // Experiment Entries (Phase 2)
  async getExperimentEntries(
    experimentId: string,
    params?: { active?: boolean; include_values?: boolean },
  ) {
    const response: AxiosResponse = await this.api.get(
      `v1/experiments/${experimentId}/entries`,
      { params },
    );
    return response.data;
  }

  async createExperimentEntry(
    experimentId: string,
    data: {
      entry_type: string;
      name: string;
      description?: string;
      predefined_entry_key?: string;
      sort_order?: number;
      config?: Record<string, unknown>;
      process_step_id?: string;
      fields?: Array<{
        field_definition_id: string;
        sort_order?: number;
        visible?: boolean;
        write_back_target?: string;
      }>;
    },
  ) {
    const response: AxiosResponse = await this.api.post(
      `v1/experiments/${experimentId}/entries`,
      { ...data, experiment_id: experimentId },
    );
    return response.data;
  }

  async instantiateExperimentEntries(
    experimentId: string,
    data?: { process_step_id?: string; skip_if_exists?: boolean },
  ) {
    const response: AxiosResponse = await this.api.post(
      `v1/experiments/${experimentId}/entries/instantiate`,
      data ?? {},
    );
    return response.data;
  }

  async getEntry(entryId: string) {
    const response: AxiosResponse = await this.api.get(`v1/entries/${entryId}`);
    return response.data;
  }

  async updateEntry(
    entryId: string,
    data: {
      name?: string;
      description?: string;
      active?: boolean;
      sort_order?: number;
      config?: Record<string, unknown>;
    },
  ) {
    const response: AxiosResponse = await this.api.patch(`v1/entries/${entryId}`, data);
    return response.data;
  }

  async deleteEntry(entryId: string) {
    await this.api.delete(`v1/entries/${entryId}`);
  }

  async getEntryValues(entryId: string, params?: { sample_id?: string }) {
    const response: AxiosResponse = await this.api.get(`v1/entries/${entryId}/values`, {
      params,
    });
    return response.data;
  }

  async upsertEntryValues(
    entryId: string,
    values: Array<{
      field_definition_id: string;
      sample_id?: string;
      value_text?: string;
      value_number?: number;
      value_list_entry_id?: string;
      value_date?: string;
      value_boolean?: boolean;
      value_json?: unknown;
      apply_write_back?: boolean;
    }>,
  ) {
    const response: AxiosResponse = await this.api.put(`v1/entries/${entryId}/values`, {
      values,
    });
    return response.data;
  }

  // SOP parse jobs (v1 API)
  async createSopParseJob(sopFile: File, instrumentFile: File) {
    const form = new FormData();
    form.append('sop_file', sopFile);
    form.append('instrument_file', instrumentFile);
    const response: AxiosResponse = await this.api.post('v1/sop-parse', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data as { id: string; status: string };
  }

  async getSopParseJob(jobId: string) {
    const response: AxiosResponse = await this.api.get(`v1/sop-parse/${jobId}`);
    return response.data as { id: string; status: string; result?: Record<string, unknown> };
  }

  async applySopParseJob(jobId: string) {
    const response: AxiosResponse = await this.api.post(`v1/sop-parse/${jobId}/apply`);
    return response.data as { job_id: string; experiment_template_id: string };
  }

  // Admin Help CRUD endpoints
  async createHelpEntry(data: {
    section: string;
    content: string;
    role_filter: string | null;
  }) {
    const response: AxiosResponse = await this.api.post('/help/admin/help', data);
    return response.data;
  }

  async updateHelpEntry(
    id: string,
    data: {
      section?: string;
      content?: string;
      role_filter?: string | null;
      active?: boolean;
    }
  ) {
    const response: AxiosResponse = await this.api.patch(`/help/admin/help/${id}`, data);
    return response.data;
  }

  async deleteHelpEntry(id: string) {
    const response: AxiosResponse = await this.api.delete(`/help/admin/help/${id}`);
    return response.data;
  }

  // ── Experiment Runs ────────────────────────────────────────────────────────

  async getLimsRuns(params?: {
    template_id?: string;
    status?: string;
    mine?: boolean;
    page?: number;
    size?: number;
  }) {
    const response: AxiosResponse = await this.api.get('/v1/lims-runs', { params });
    return response.data;
  }

  async getLimsRun(id: string) {
    const response: AxiosResponse = await this.api.get(`/v1/lims-runs/${id}`);
    return response.data;
  }

  async createLimsRun(data: {
    name: string;
    description?: string;
    experiment_template_id: string;
    analysis_id?: string | null;
  }) {
    const response: AxiosResponse = await this.api.post('/v1/lims-runs', data);
    return response.data;
  }

  async updateLimsRun(
    id: string,
    data: {
      name?: string;
      description?: string;
      analysis_id?: string | null;
      clear_analysis?: boolean;
    },
  ) {
    const response: AxiosResponse = await this.api.patch(`/v1/lims-runs/${id}`, data);
    return response.data;
  }

  async orderLimsRun(id: string) {
    const response: AxiosResponse = await this.api.patch(`/v1/lims-runs/${id}/order`);
    return response.data;
  }

  async startLimsRun(id: string, body?: { acknowledge_no_analysis?: boolean }) {
    const response: AxiosResponse = await this.api.patch(
      `/v1/lims-runs/${id}/start`,
      body ?? {},
    );
    return response.data;
  }

  async markResultsReceived(id: string) {
    const response: AxiosResponse = await this.api.patch(`/v1/lims-runs/${id}/results-received`);
    return response.data;
  }

  async reviewLimsRun(id: string, notes?: string) {
    const response: AxiosResponse = await this.api.patch(`/v1/lims-runs/${id}/review`, { notes });
    return response.data;
  }

  async publishLimsRun(id: string) {
    const response: AxiosResponse = await this.api.patch(`/v1/lims-runs/${id}/complete`);
    return response.data;
  }

  /** Dry-run of promote-on-publish (creates/updates/conflicts). */
  async getLimsRunPromotionPreview(id: string): Promise<PromotionPreview> {
    const response: AxiosResponse<PromotionPreview> = await this.api.get(
      `/v1/lims-runs/${id}/promotion/preview`,
    );
    return response.data;
  }

  async cancelLimsRun(id: string) {
    const response: AxiosResponse = await this.api.patch(`/v1/lims-runs/${id}/cancel`);
    return response.data;
  }

  async getLimsRunData(id: string, params?: { page?: number; size?: number }) {
    const response: AxiosResponse = await this.api.get(`/v1/lims-runs/${id}/data`, { params });
    return response.data;
  }

  // ── Dose Response ──────────────────────────────────────────────────────────

  async triggerDoseResponseFit(runId: string) {
    const response: AxiosResponse = await this.api.post(`/v1/lims-runs/${runId}/dose-response/fit`);
    return response.data;
  }

  async triggerDoseResponseRefit(runId: string, sampleId: string) {
    const response: AxiosResponse = await this.api.post(`/v1/lims-runs/${runId}/dose-response/refit/${sampleId}`);
    return response.data;
  }

  async getDoseResponseSummary(runId: string) {
    const response: AxiosResponse = await this.api.get(`/v1/lims-runs/${runId}/dose-response/summary`);
    return response.data;
  }

  async getDoseResponseResults(
    runId: string,
    params: { category?: string; review_status?: string; page?: number; size?: number }
  ) {
    const response: AxiosResponse = await this.api.get(
      `/v1/lims-runs/${runId}/dose-response/results`,
      { params }
    );
    return response.data;
  }

  async getDoseResponseResult(runId: string, resultId: string) {
    const response: AxiosResponse = await this.api.get(
      `/v1/lims-runs/${runId}/dose-response/results/${resultId}`
    );
    return response.data;
  }

  async reviewDoseResponseResult(runId: string, resultId: string, reviewStatus: string, notes?: string) {
    const response: AxiosResponse = await this.api.post(
      `/v1/lims-runs/${runId}/dose-response/results/${resultId}/review`,
      { status: reviewStatus, notes }
    );
    return response.data;
  }

  async batchReviewDoseResponse(runId: string, category: string, reviewStatus: string) {
    const response: AxiosResponse = await this.api.post(
      `/v1/lims-runs/${runId}/dose-response/results/batch-review`,
      { category, status: reviewStatus }
    );
    return response.data;
  }

  async excludeDataPoint(dataId: string, reason?: string) {
    const response: AxiosResponse = await this.api.post(
      `/v1/lims-runs/data/${dataId}/exclude`,
      { reason }
    );
    return response.data;
  }

  async unexcludeDataPoint(dataId: string) {
    const response: AxiosResponse = await this.api.delete(
      `/v1/lims-runs/data/${dataId}/exclude`
    );
    return response.data;
  }
}

export const apiService = new ApiService();
