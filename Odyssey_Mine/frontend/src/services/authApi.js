import { apiClient } from './apiClient.js';

const TOKEN_KEY = 'odyssey_token';
const USER_KEY = 'odyssey_user';

const listeners = new Set();

function notifyAuthChange(user) {
  for (const fn of listeners) {
    try {
      fn(user);
    } catch (e) {
      console.error('Auth listener error:', e);
    }
  }
}

/**
 * Authentication and User Account API Service
 * Integrates with FastAPI /api/v1/users endpoints
 */
export const authApi = {
  /**
   * Login user with email and password
   * Calls POST /api/v1/users/login?email={email}&password={password}
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{ message: string, user_id: number, name: string, email: string, access_token: string, token_type: string }>}
   */
  login: async (email, password) => {
    if (!email || !password) {
      throw new Error('Please provide both email and password.');
    }

    const trimmedEmail = email.trim().toLowerCase();
    const params = { email: trimmedEmail, password };
    const body = { email: trimmedEmail, password };

    // The backend uses query params (email: str, password: str), we also pass body for resilience
    const response = await apiClient.post('/users/login', body, params);

    if (response && response.access_token) {
      authApi.setSession(response);
    }

    return response;
  },

  /**
   * Register a new user
   * Calls POST /api/v1/users/?name={name}&email={email}&password={password}
   * @param {string} name
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{ message: string, user_id: number, name: string, email: string }>}
   */
  register: async (name, email, password) => {
    if (!name || !email || !password) {
      throw new Error('Name, email and password are required.');
    }

    const trimmedName = name.trim();
    const trimmedEmail = email.trim().toLowerCase();
    const params = { name: trimmedName, email: trimmedEmail, password };
    const body = { name: trimmedName, email: trimmedEmail, password };

    return await apiClient.post('/users/', body, params);
  },

  /**
   * Save session to localStorage
   */
  setSession: (authData) => {
    if (typeof window === 'undefined') return;

    if (authData.access_token) {
      localStorage.setItem(TOKEN_KEY, authData.access_token);
    }

    const userData = {
      id: authData.user_id,
      name: authData.name,
      email: authData.email,
    };
    localStorage.setItem(USER_KEY, JSON.stringify(userData));

    notifyAuthChange(userData);
  },

  /**
   * Retrieve active JWT access token
   * @returns {string | null}
   */
  getToken: () => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Retrieve current user profile
   * @returns {{ id: number, name: string, email: string } | null}
   */
  getUser: () => {
    if (typeof window === 'undefined') return null;
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  /**
   * Check if user is currently authenticated
   * @returns {boolean}
   */
  isAuthenticated: () => {
    return Boolean(authApi.getToken());
  },

  /**
   * Logout user and clear stored session
   */
  logout: () => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    notifyAuthChange(null);
  },

  /**
   * Subscribe to authentication state changes
   * @param {(user: { id: number, name: string, email: string } | null) => void} callback
   * @returns {() => void} unsubscribe function
   */
  onAuthChange: (callback) => {
    listeners.add(callback);
    return () => listeners.delete(callback);
  },
};

export default authApi;
