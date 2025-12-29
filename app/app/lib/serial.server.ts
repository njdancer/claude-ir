/**
 * Serial Manager - Environment-based Selection
 *
 * Automatically selects between mock and real serial manager based on environment.
 * - Use MOCK_SERIAL=true or NODE_ENV=test for mock
 * - Use MOCK_SERIAL=false or NODE_ENV=production for real hardware
 */

import { MockSerialManager } from './serial.mock.server';
import { RealSerialManager } from './serial.real.server';

// Determine which serial manager to use
const USE_MOCK =
  process.env.MOCK_SERIAL === 'true' ||
  process.env.NODE_ENV === 'test' ||
  (process.env.NODE_ENV === 'development' && process.env.MOCK_SERIAL !== 'false');

// Debug logging
console.log('[Serial Manager] Environment:', {
  MOCK_SERIAL: process.env.MOCK_SERIAL,
  NODE_ENV: process.env.NODE_ENV,
  USE_MOCK,
});

// Export the appropriate manager
export const serialManager = USE_MOCK
  ? new MockSerialManager()
  : new RealSerialManager();

console.log('[Serial Manager] Using:', USE_MOCK ? 'MockSerialManager' : 'RealSerialManager');

// Export type for manager
export type SerialManager = MockSerialManager | RealSerialManager;

/**
 * Initialize serial connection
 */
export async function initSerial(): Promise<void> {
  await serialManager.init();
}

/**
 * Send command to ESP8266 and get response
 */
export async function sendCommand(cmd: string): Promise<string> {
  return serialManager.sendCommand(cmd);
}

/**
 * Close serial connection
 */
export async function closeSerial(): Promise<void> {
  await serialManager.close();
}

/**
 * Parse AC state from STATE command response
 * Response format: "OK:Power=ON,Temp=22.5,Mode=COOL,Fan=AUTO"
 */
export function parseStateResponse(response: string): {
  power: boolean;
  temperature: number;
  mode: string;
  fanSpeed: string;
} {
  // Remove "OK:" prefix
  const stateStr = response.replace(/^OK:/, '');

  // Parse key=value pairs
  const pairs = stateStr.split(',');
  const state: Record<string, string> = {};

  pairs.forEach((pair) => {
    const [key, value] = pair.split('=');
    state[key.trim()] = value.trim();
  });

  return {
    power: state.Power === 'ON',
    temperature: parseFloat(state.Temp),
    mode: state.Mode,
    fanSpeed: state.Fan,
  };
}

/**
 * Validate that response is OK (not ERROR)
 */
export function isOkResponse(response: string): boolean {
  return response.startsWith('OK:');
}

/**
 * Extract error message from ERROR response
 */
export function getErrorMessage(response: string): string {
  return response.replace(/^ERROR:/, '');
}
