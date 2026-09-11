import { apiClient } from './apiClient.js';

/**
 * Expenses API service
 */
export const expenseApi = {
  /**
   * List and filter expenses.
   * @param {Object} [params]
   * @param {number} [params.trip_id] - Filter by SQLite trip ID
   * @param {string} [params.category] - Filter by category (Food, Stay, Travel, Activities, Other)
   * @param {number} [params.page=1]
   * @param {number} [params.limit=10]
   * @returns {Promise<{ items: Array, total: number, page: number, limit: number, total_pages: number }>}
   */
  listExpenses: (params = {}) => apiClient.get('/expenses', params),

  /**
   * Get aggregated expense summary (optionally filtered by trip_id).
   * @param {number} [trip_id]
   * @returns {Promise<{ trip_id: number|null, total_expenses: number, total_amount: number, currency: string, by_category: Record<string, number> }>}
   */
  getExpenseSummary: (trip_id) => apiClient.get('/expenses/summary', trip_id ? { trip_id } : {}),

  /**
   * Get single expense details by ID.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  getExpenseById: (id) => apiClient.get(`/expenses/${id}`),

  /**
   * Create a new expense record.
   * @param {Object} data
   * @param {number} data.trip_id
   * @param {string} data.category
   * @param {string} data.title
   * @param {number} data.amount
   * @param {string} [data.currency='INR']
   * @param {string} [data.expense_date]
   * @param {string} [data.notes]
   * @returns {Promise<Object>}
   */
  createExpense: (data) => apiClient.post('/expenses', data),

  /**
   * Update an expense record.
   * @param {string} id
   * @param {Object} data
   * @returns {Promise<Object>}
   */
  updateExpense: (id, data) => apiClient.put(`/expenses/${id}`, data),

  /**
   * Delete an expense record.
   * @param {string} id
   * @returns {Promise<Object>}
   */
  deleteExpense: (id) => apiClient.delete(`/expenses/${id}`),
};

export default expenseApi;
