import { apiClient } from './apiClient.js';

/**
 * Activities API service
 */
export const activityApi = {
  /**
   * List and filter activities.
   * @param {Object} [params]
   * @param {string} [params.destination_id] - Associated destination ID
   * @param {string} [params.category] - Category (Sightseeing, Adventure, Heritage, Food, etc.)
   * @param {string} [params.search] - Search keyword
   * @param {number} [params.min_price]
   * @param {number} [params.max_price]
   * @param {number} [params.min_rating]
   * @param {number} [params.page=1]
   * @param {number} [params.limit=10]
   * @returns {Promise<{ items: Array, total: number, page: number, limit: number, total_pages: number }>}
   */
  listActivities: (params = {}) => apiClient.get('/activities', params),

  /**
   * Get single activity details by ID.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  getActivityById: (id) => apiClient.get(`/activities/${id}`),

  /**
   * Create a new activity.
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  createActivity: (data) => apiClient.post('/activities', data),

  /**
   * Update an activity.
   * @param {string} id
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  updateActivity: (id, data) => apiClient.put(`/activities/${id}`, data),

  /**
   * Delete an activity.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  deleteActivity: (id) => apiClient.delete(`/activities/${id}`),
};

export default activityApi;
