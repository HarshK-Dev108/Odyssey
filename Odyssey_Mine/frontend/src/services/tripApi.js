import { apiClient } from './apiClient.js';

/**
 * Trip Planning API service
 */
export const tripApi = {
  /**
   * Create and persist a new trip plan.
   * @param {Object} tripData
   * @param {string} tripData.from_city
   * @param {string} tripData.destination
   * @param {string} tripData.start_date - YYYY-MM-DD
   * @param {string} tripData.end_date - YYYY-MM-DD
   * @param {number} tripData.travellers
   * @param {number} tripData.budget
   * @param {string} [tripData.currency='INR']
   * @param {string[]} [tripData.interests=[]]
   * @param {number} [tripData.hotel_rating=3]
   * @param {string} [tripData.pace='moderate']
   * @param {boolean} [tripData.avoid_crowds=false]
   * @returns {Promise<{ message: string, trip_id: number, trip: Object }>}
   */
  createTripPlan: (tripData) => apiClient.post('/trips/plan', tripData),

  /**
   * Get trip details by SQLite trip ID.
   * @param {number} tripId
   * @returns {Promise<Object>}
   */
  getTripById: (tripId) => apiClient.get(`/trips/${tripId}`),
};

export default tripApi;
