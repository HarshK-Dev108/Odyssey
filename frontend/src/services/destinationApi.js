import { apiClient } from './apiClient.js';

/**
 * Destinations API service
 */
export const destinationApi = {
  /**
   * List and search destinations.
   * @param {Object} [params]
   * @param {string} [params.search] - Search keyword (name, city, state, tags)
   * @param {string} [params.country] - Filter by country
   * @param {number} [params.page=1]
   * @param {number} [params.limit=10]
   * @returns {Promise<{ items: Array, total: number, page: number, limit: number, total_pages: number }>}
   */
  listDestinations: (params = {}) => apiClient.get('/destinations', params),

  /**
   * Get single destination details by ID.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  getDestinationById: (id) => apiClient.get(`/destinations/${id}`),

  /**
   * Create a new destination.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  createDestination: (data) => apiClient.post('/destinations', data),

  /**
   * Update a destination.
   * @param {string} id
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  updateDestination: (id, data) => apiClient.put(`/destinations/${id}`, data),

  /**
   * Delete a destination.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  deleteDestination: (id) => apiClient.delete(`/destinations/${id}`),
};

export default destinationApi;
