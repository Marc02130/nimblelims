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
  async getSamples(filters?: { project_id?: string; status?: string }) {
    const response: AxiosResponse = await this.api.get('/samples', {
      params: filters,
    });
    // API returns SampleListResponse with {samples, total, page, size, pages}
    // Extract the samples array for the frontend
    return response.data.samples || response.data;
  }

  async createSample(sampleData: any) {
    const response: AxiosResponse = await this.api.post('/samples', sampleData);
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
  async getContainers(filters?: { type_id?: string; parent_container_id?: string }) {
    const response: AxiosResponse = await this.api.get('/containers', {
      params: filters,
    });
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
  async createContent(contentData: any) {
    const response: AxiosResponse = await this.api.post('/contents', contentData);
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
  async getProjects() {
    const response: AxiosResponse = await this.api.get('/projects');
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
    const response: AxiosResponse = await this.api.post(`/batches/${batchId}/results`, resultsData);
    return response.data;
  }

  // Analyte endpoints
  async getAnalytes() {
    const response: AxiosResponse = await this.api.get('/analytes');
    return response.data;
  }

  async getAnalysisAnalytes(analysisId: string) {
    const response: AxiosResponse = await this.api.get(`/analyses/${analysisId}/analytes`);
    return response.data;
  }
}

export const apiService = new ApiService();
