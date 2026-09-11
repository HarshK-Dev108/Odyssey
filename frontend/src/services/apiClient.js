/**
 * Reusable lightweight API client for Odyssey Frontend.
 * Communicates with backend endpoints via the /api/v1 proxy or configured base URL.
 */

const API_BASE = (typeof window !== 'undefined' && window.__API_BASE__) 
  || (typeof process !== 'undefined' && process.env?.VITE_API_BASE_URL) 
  || '/api/v1';

/**
 * Builds a query string from a parameter object.
 * @param {Record<string, any>} params
 * @returns {string}
 */
export function buildQuery(params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      query.append(key, String(value));
    }
  }
  const queryString = query.toString();
  return queryString ? `?${queryString}` : '';
}

/**
 * Base HTTP request wrapper.
 * @param {string} endpoint
 * @param {RequestInit} [options]
 * @returns {Promise<any>}
 */
export async function request(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    ...(options.headers || {}),
  };

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);
    const contentType = response.headers.get('content-type') || '';
    
    let data;
    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errorMsg = (typeof data === 'object' && data !== null)
        ? (data.detail || data.message || JSON.stringify(data))
        : String(data || `HTTP error ${response.status}`);
      const err = new Error(errorMsg);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (error) {
    console.error(`[API Request Error] ${options.method || 'GET'} ${url}:`, error.message);
    throw error;
  }
}

export const apiClient = {
  get: (endpoint, params) => request(`${endpoint}${buildQuery(params)}`, { method: 'GET' }),
  post: (endpoint, body) => request(endpoint, { method: 'POST', body: JSON.stringify(body) }),
  put: (endpoint, body) => request(endpoint, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (endpoint) => request(endpoint, { method: 'DELETE' }),
};

export default apiClient;
