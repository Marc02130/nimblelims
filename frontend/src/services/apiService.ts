import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Use nginx proxy at /api/ which forwards to backend:8000
// This avoids CORS issues and works in Docker
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
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
  async getAnalyses() {
    const response: AxiosResponse = await this.api.get('/analyses');
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

  async validateBatchCompatibility(data: { container_ids: string[] }) {
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
  async getAnalytes() {
    const response: AxiosResponse = await this.api.get('/analytes');
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
  async getUsers(filters?: { role_id?: string; client_id?: string }) {
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
    billing_info?: Record<string, any>;
  }) {
    const response: AxiosResponse = await this.api.post('/clients', clientData);
    return response.data;
  }

  async updateClient(id: string, clientData: {
    name?: string;
    description?: string;
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

  // Custom Attributes Configuration endpoints
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

  async getCustomAttributeConfig(id: string) {
    const response: AxiosResponse = await this.api.get(`/admin/custom-attributes/${id}`);
    return response.data;
  }

  async createCustomAttributeConfig(configData: {
    entity_type: string;
    attr_name: string;
    data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
    validation_rules: Record<string, any>;
    description?: string;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.post('/admin/custom-attributes', configData);
    return response.data;
  }

  async updateCustomAttributeConfig(
    id: string,
    configData: {
      entity_type?: string;
      attr_name?: string;
      data_type?: 'text' | 'number' | 'date' | 'boolean' | 'select';
      validation_rules?: Record<string, any>;
      description?: string;
      active?: boolean;
    }
  ) {
    const response: AxiosResponse = await this.api.patch(`/admin/custom-attributes/${id}`, configData);
    return response.data;
  }

  async deleteCustomAttributeConfig(id: string) {
    const response: AxiosResponse = await this.api.delete(`/admin/custom-attributes/${id}`);
    return response.data;
  }

  // Name Templates endpoints
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

  async getNameTemplate(id: string) {
    const response: AxiosResponse = await this.api.get(`/admin/name-templates/${id}`);
    return response.data;
  }

  async createNameTemplate(templateData: {
    entity_type: string;
    template: string;
    description?: string;
    active?: boolean;
  }) {
    const response: AxiosResponse = await this.api.post('/admin/name-templates', templateData);
    return response.data;
  }

  async updateNameTemplate(
    id: string,
    templateData: {
      entity_type?: string;
      template?: string;
      description?: string;
      active?: boolean;
    }
  ) {
    const response: AxiosResponse = await this.api.patch(`/admin/name-templates/${id}`, templateData);
    return response.data;
  }

  async deleteNameTemplate(id: string) {
    const response: AxiosResponse = await this.api.delete(`/admin/name-templates/${id}`);
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
}

export const apiService = new ApiService();
