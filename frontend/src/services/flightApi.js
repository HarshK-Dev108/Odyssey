import { apiClient } from './apiClient.js';

/**
 * Flights API service
 */
export const flightApi = {
  /**
   * List and filter flights.
   * @param {Object} [params]
   * @param {string} [params.origin] - Origin code or airport (e.g. DEL, BOM)
   * @param {string} [params.destination] - Destination code or airport (e.g. GOI, JAI)
   * @param {string} [params.airline] - Filter by airline
   * @param {number} [params.min_price]
   * @param {number} [params.max_price]
   * @param {number} [params.page=1]
   * @param {number} [params.limit=10]
   * @returns {Promise<{ items: Array, total: number, page: number, limit: number, total_pages: number }>}
   */
  listFlights: (params = {}) => apiClient.get('/flights', params),

  /**
   * Get single flight details by ID.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  getFlightById: (id) => apiClient.get(`/flights/${id}`),

  /**
   * Create a new flight.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  createFlight: (data) => apiClient.post('/flights', data),

  /**
   * Update a flight.
   * @param {string} id
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  updateFlight: (id, data) => apiClient.put(`/flights/${id}`, data),

  /**
   * Delete a flight.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  deleteFlight: (id) => apiClient.delete(`/flights/${id}`),
};

export default flightApi;
