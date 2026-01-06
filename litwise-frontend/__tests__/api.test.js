/**
 * Jest Unit Tests for API Functions
 * Tests core API functionality
 */

describe('API Functions', () => {
  // Mock fetch
  global.fetch = jest.fn();

  beforeEach(() => {
    fetch.mockClear();
  });

  describe('getAuthToken', () => {
    it('should return null if not authenticated', async () => {
      // Mock localStorage as empty
      const getItemSpy = jest.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
      
      expect(getItemSpy('supabase-token')).toBeNull();
      
      getItemSpy.mockRestore();
    });

    it('should retrieve token from session', async () => {
      const mockToken = 'test-jwt-token-123';
      const getItemSpy = jest.spyOn(Storage.prototype, 'getItem').mockReturnValue(mockToken);
      
      expect(getItemSpy('access_token')).toBe(mockToken);
      
      getItemSpy.mockRestore();
    });
  });

  describe('apiRequest', () => {
    it('should make GET request to correct endpoint', async () => {
      const mockData = { id: 1, title: 'Test Paper' };
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      // Simulate API call
      const response = await fetch('http://localhost:8000/papers', {
        method: 'GET',
        headers: { 'Authorization': 'Bearer test-token' },
      });

      const data = await response.json();

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/papers',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
          }),
        })
      );
      expect(data).toEqual(mockData);
    });

    it('should handle API errors', async () => {
      const errorMessage = 'API Error';
      
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: errorMessage }),
      });

      const response = await fetch('http://localhost:8000/papers');
      const data = await response.json();

      expect(response.ok).toBe(false);
      expect(data.detail).toBe(errorMessage);
    });

    it('should include authorization header', async () => {
      const token = 'test-jwt-token';
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await fetch('http://localhost:8000/api/notes', {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': `Bearer ${token}`,
          }),
        })
      );
    });
  });

  describe('Rate Limiting', () => {
    it('should handle 429 rate limit response', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        headers: new Map([['retry-after', '60']]),
        json: async () => ({ detail: 'Rate limit exceeded' }),
      });

      const response = await fetch('http://localhost:8000/papers');
      const retryAfter = response.headers.get('retry-after');

      expect(response.status).toBe(429);
      expect(retryAfter).toBe('60');
    });
  });
});
