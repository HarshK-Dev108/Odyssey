import { apiClient } from './apiClient.js';

/**
 * Weather API service
 */
export const weatherApi = {
  /**
   * Get current live weather for given geographical coordinates.
   * @param {number} latitude - Between -90 and 90
   * @param {number} longitude - Between -180 and 180
   * @returns {Promise<{ latitude: number, longitude: number, temperature: number, condition: string, weather_code: number|null, humidity: number|null, wind_speed: number|null, unit: string, timestamp: string }>}
   */
  getWeather: (latitude, longitude) => apiClient.get('/weather', { latitude, longitude }),
};

export default weatherApi;
