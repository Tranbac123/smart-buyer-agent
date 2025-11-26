/**
 * localStorage wrapper with SSR safety
 */

export const storage = {
  /**
   * Get value from localStorage with fallback
   */
  get<T>(key: string, fallback: T): T {
    if (typeof window === "undefined") return fallback;
    
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : fallback;
    } catch {
      return fallback;
    }
  },

  /**
   * Set value to localStorage
   */
  set<T>(key: string, value: T): void {
    if (typeof window === "undefined") return;
    
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error("Storage set error:", error);
    }
  },

  /**
   * Remove item from localStorage
   */
  remove(key: string): void {
    if (typeof window === "undefined") return;
    
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error("Storage remove error:", error);
    }
  },

  /**
   * Clear all localStorage
   */
  clear(): void {
    if (typeof window === "undefined") return;
    
    try {
      localStorage.clear();
    } catch (error) {
      console.error("Storage clear error:", error);
    }
  }
};

