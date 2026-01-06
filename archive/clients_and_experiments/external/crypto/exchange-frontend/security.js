// Security Utilities Module
import DOMPurify from 'dompurify';
import Cookies from 'js-cookie';

// Configure DOMPurify
DOMPurify.setConfig({
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'span', 'div', 'p', 'br'],
  ALLOWED_ATTR: ['class'],
  KEEP_CONTENT: true,
});

// CSRF Token Management
export const CSRF = {
  TOKEN_HEADER: 'X-CSRF-Token',
  TOKEN_COOKIE: 'csrf_token',

  getToken() {
    return Cookies.get(this.TOKEN_COOKIE) || '';
  },

  setToken(token) {
    if (!token || typeof token !== 'string') {
      console.error('Invalid CSRF token');
      return;
    }
    Cookies.set(this.TOKEN_COOKIE, token, {
      secure: window.location.protocol === 'https:',
      sameSite: 'Strict',
      expires: 1, // 1 day
    });
  },

  clearToken() {
    Cookies.remove(this.TOKEN_COOKIE);
  },

  validateToken(token) {
    const storedToken = this.getToken();
    return storedToken && storedToken === token;
  },
};

// Input Sanitization
export const Sanitizer = {
  // Sanitize HTML content
  html(dirty) {
    return DOMPurify.sanitize(dirty);
  },

  // Sanitize username (alphanumeric + underscore, dash)
  username(input) {
    if (typeof input !== 'string') {return '';}
    return input.replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 32);
  },

  // Sanitize numeric input
  number(input, min = 0, max = Number.MAX_SAFE_INTEGER) {
    const num = parseFloat(input);
    if (isNaN(num)) {return min;}
    return Math.max(min, Math.min(max, num));
  },

  // Sanitize URL
  url(input) {
    if (typeof input !== 'string') {return '';}
    try {
      const url = new URL(input);
      // Only allow http and https protocols
      if (!['http:', 'https:'].includes(url.protocol)) {
        return '';
      }
      return url.toString();
    } catch {
      return '';
    }
  },
};

// Rate Limiter (Client-side)
export class RateLimiter {
  constructor(maxRequests = 60, windowMs = 60000) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
    this.requests = [];
  }

  canMakeRequest() {
    const now = Date.now();
    // Remove old requests outside the time window
    this.requests = this.requests.filter(time => now - time < this.windowMs);

    if (this.requests.length >= this.maxRequests) {
      return false;
    }

    this.requests.push(now);
    return true;
  }

  getRemainingRequests() {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < this.windowMs);
    return Math.max(0, this.maxRequests - this.requests.length);
  }

  getResetTime() {
    if (this.requests.length === 0) {return 0;}
    const oldestRequest = Math.min(...this.requests);
    return oldestRequest + this.windowMs;
  }
}

// Content Security Policy (CSP) Helper
export const CSP = {
  // Check if CSP is supported
  isSupported() {
    return 'SecurityPolicyViolationEvent' in window;
  },

  // Report CSP violations
  reportViolation(event) {
    console.error('CSP Violation:', {
      violatedDirective: event.violatedDirective,
      blockedURI: event.blockedURI,
      originalPolicy: event.originalPolicy,
    });
  },

  // Initialize CSP violation reporting
  init() {
    if (this.isSupported()) {
      document.addEventListener('securitypolicyviolation', this.reportViolation);
    }
  },
};

// Secure Storage Wrapper
export const SecureStorage = {
  // Store data with expiration
  set(key, value, expiresInMs = 3600000) {
    try {
      const item = {
        value,
        expires: Date.now() + expiresInMs,
      };
      localStorage.setItem(key, JSON.stringify(item));
    } catch (error) {
      console.error('Storage error:', error);
    }
  },

  // Retrieve data if not expired
  get(key) {
    try {
      const itemStr = localStorage.getItem(key);
      if (!itemStr) {return null;}

      const item = JSON.parse(itemStr);
      if (Date.now() > item.expires) {
        localStorage.removeItem(key);
        return null;
      }

      return item.value;
    } catch (error) {
      console.error('Storage error:', error);
      return null;
    }
  },

  // Remove data
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Storage error:', error);
    }
  },

  // Clear all expired items
  clearExpired() {
    try {
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        const itemStr = localStorage.getItem(key);
        if (itemStr) {
          try {
            const item = JSON.parse(itemStr);
            if (item.expires && Date.now() > item.expires) {
              localStorage.removeItem(key);
            }
          } catch {
            // Skip invalid items
          }
        }
      });
    } catch (error) {
      console.error('Storage cleanup error:', error);
    }
  },
};

// Password Strength Validator
export const PasswordValidator = {
  minLength: 8,

  validate(password) {
    const errors = [];

    if (password.length < this.minLength) {
      errors.push(`Password must be at least ${this.minLength} characters`);
    }

    if (!/[A-Z]/.test(password)) {
      errors.push('Password must contain at least one uppercase letter');
    }

    if (!/[a-z]/.test(password)) {
      errors.push('Password must contain at least one lowercase letter');
    }

    if (!/[0-9]/.test(password)) {
      errors.push('Password must contain at least one number');
    }

    if (!/[^A-Za-z0-9]/.test(password)) {
      errors.push('Password must contain at least one special character');
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  },

  getStrength(password) {
    let strength = 0;

    if (password.length >= this.minLength) {strength += 1;}
    if (password.length >= 12) {strength += 1;}
    if (/[A-Z]/.test(password)) {strength += 1;}
    if (/[a-z]/.test(password)) {strength += 1;}
    if (/[0-9]/.test(password)) {strength += 1;}
    if (/[^A-Za-z0-9]/.test(password)) {strength += 1;}

    if (strength <= 2) {return 'weak';}
    if (strength <= 4) {return 'medium';}
    return 'strong';
  },
};

// Initialize CSP reporting
CSP.init();

// Clean expired storage items on page load
SecureStorage.clearExpired();

export default {
  CSRF,
  Sanitizer,
  RateLimiter,
  CSP,
  SecureStorage,
  PasswordValidator,
};
