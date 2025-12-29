import '@testing-library/jest-dom';
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Set test environment
process.env.NODE_ENV = 'test';
process.env.MOCK_SERIAL = 'true';
