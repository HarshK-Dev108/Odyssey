import { apiClient } from './apiClient.js';

/**
 * Hotels API service
 */
export const hotelApi = {
  /**
   * List and filter hotels.
   * @param {Object} [params]
   * @param {string} [params.destination_id] - Associated destination ID
   * @param {string} [params.search] - Search keyword (name, address, amenities)
   * @param {number} [params.min_price]
   * @param {number} [params.max_price]
   * @param {number} [params.min_rating]
   * @param {number} [params.page=1]
   * @param {number} [params.limit=10]
   * @returns {Promise<{ items: Array, total: number, page: number, limit: number, total_pages: number }>}
   */
  listHotels: (params = {}) => apiClient.get('/hotels', params),

  /**
   * Get single hotel details by ID.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  getHotelById: (id) => apiClient.get(`/hotels/${id}`),

  /**
   * Create a new hotel.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  createHotel: (data) => apiClient.post('/hotels', data),

  /**
   * Update a hotel.
   * @param {string} id
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  updateHotel: (id, data) => apiClient.put(`/hotels/${id}`, data),

  /**
   * Delete a hotel.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  deleteHotel: (id) => apiClient.delete(`/hotels/${id}`),
};

export default hotelApi;
