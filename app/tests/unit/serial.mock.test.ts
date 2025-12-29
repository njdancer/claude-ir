/**
 * Unit Tests for Mock Serial Manager
 *
 * Tests all serial commands and state management
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { MockSerialManager } from '../../app/lib/serial.mock.server';

describe('MockSerialManager', () => {
  let serial: MockSerialManager;

  beforeEach(async () => {
    serial = new MockSerialManager();
    await serial.init();
    serial.resetState();
  });

  describe('Initialization', () => {
    it('should initialize successfully', async () => {
      const newSerial = new MockSerialManager();
      await expect(newSerial.init()).resolves.toBeUndefined();
    });

    it('should start with default state', () => {
      const state = serial.getState();
      expect(state.power).toBe(false);
      expect(state.temperature).toBe(22.0);
      expect(state.mode).toBe('COOL');
      expect(state.fanSpeed).toBe('AUTO');
    });
  });

  describe('POWER Command', () => {
    it('should turn power ON', async () => {
      const response = await serial.sendCommand('POWER:ON');
      expect(response).toBe('OK:Power ON, sent BOSCH144 command');
      expect(serial.getState().power).toBe(true);
    });

    it('should turn power OFF', async () => {
      await serial.sendCommand('POWER:ON');
      const response = await serial.sendCommand('POWER:OFF');
      expect(response).toBe('OK:Power OFF, sent COOLIX command');
      expect(serial.getState().power).toBe(false);
    });

    it('should reject invalid power state', async () => {
      const response = await serial.sendCommand('POWER:INVALID');
      expect(response).toMatch(/ERROR:/);
    });
  });

  describe('TEMP Command', () => {
    it('should set valid whole number temperatures', async () => {
      const temps = [16.0, 20.0, 22.0, 25.0, 30.0];
      for (const temp of temps) {
        const response = await serial.sendCommand(`TEMP:${temp}`);
        expect(response).toBe(`OK:Temperature set to ${temp.toFixed(1)}C`);
        expect(serial.getState().temperature).toBe(temp);
        expect(serial.getState().power).toBe(true); // Setting temp implies power on
      }
    });

    it('should set valid half-degree temperatures', async () => {
      const temps = [16.5, 20.5, 22.5, 25.5, 29.5];
      for (const temp of temps) {
        const response = await serial.sendCommand(`TEMP:${temp}`);
        expect(response).toBe(`OK:Temperature set to ${temp.toFixed(1)}C`);
        expect(serial.getState().temperature).toBe(temp);
      }
    });

    it('should reject temperatures below 16°C', async () => {
      const response = await serial.sendCommand('TEMP:15.5');
      expect(response).toMatch(/ERROR:/);
      expect(response).toMatch(/16.0-30.0/);
    });

    it('should reject temperatures above 30°C', async () => {
      const response = await serial.sendCommand('TEMP:30.5');
      expect(response).toMatch(/ERROR:/);
    });

    it('should reject invalid increments', async () => {
      const invalidTemps = [20.1, 22.3, 25.7, 28.9];
      for (const temp of invalidTemps) {
        const response = await serial.sendCommand(`TEMP:${temp}`);
        expect(response).toMatch(/ERROR:/);
      }
    });

    it('should turn on power when setting temperature', async () => {
      serial.resetState();
      expect(serial.getState().power).toBe(false);

      await serial.sendCommand('TEMP:24.0');
      expect(serial.getState().power).toBe(true);
    });
  });

  describe('MODE Command', () => {
    const validModes = ['COOL', 'HEAT', 'DRY', 'FAN', 'AUTO'];

    it('should set all valid modes', async () => {
      for (const mode of validModes) {
        const response = await serial.sendCommand(`MODE:${mode}`);
        expect(response).toBe(`OK:Mode set to ${mode}`);
        expect(serial.getState().mode).toBe(mode);
      }
    });

    it('should reject invalid modes', async () => {
      const response = await serial.sendCommand('MODE:INVALID');
      expect(response).toMatch(/ERROR:/);
      expect(response).toMatch(/COOL\/HEAT\/DRY\/FAN\/AUTO/);
    });

    it('should turn on power when setting mode', async () => {
      serial.resetState();
      expect(serial.getState().power).toBe(false);

      await serial.sendCommand('MODE:HEAT');
      expect(serial.getState().power).toBe(true);
    });
  });

  describe('FAN Command', () => {
    const validSpeeds = ['AUTO', '20', '40', '60', '80', '100'];

    it('should set all valid fan speeds', async () => {
      for (const speed of validSpeeds) {
        const response = await serial.sendCommand(`FAN:${speed}`);
        expect(response).toBe(`OK:Fan set to ${speed}`);
        expect(serial.getState().fanSpeed).toBe(speed);
      }
    });

    it('should reject invalid fan speeds', async () => {
      const response = await serial.sendCommand('FAN:50');
      expect(response).toMatch(/ERROR:/);
    });

    it('should turn on power when setting fan speed', async () => {
      serial.resetState();
      expect(serial.getState().power).toBe(false);

      await serial.sendCommand('FAN:60');
      expect(serial.getState().power).toBe(true);
    });
  });

  describe('Special Functions', () => {
    it('should toggle SWING', async () => {
      const response = await serial.sendCommand('SWING');
      expect(response).toBe('OK:Swing toggled');
    });

    it('should activate BOOST', async () => {
      const response = await serial.sendCommand('BOOST');
      expect(response).toBe('OK:Boost activated');
    });

    it('should toggle LED', async () => {
      const response = await serial.sendCommand('LED');
      expect(response).toBe('OK:LED toggled');
    });
  });

  describe('STATE Command', () => {
    it('should return current state in correct format', async () => {
      await serial.sendCommand('POWER:ON');
      await serial.sendCommand('TEMP:24.5');
      await serial.sendCommand('MODE:HEAT');
      await serial.sendCommand('FAN:60');

      const response = await serial.sendCommand('STATE');
      expect(response).toBe('OK:Power=ON,Temp=24.5,Mode=HEAT,Fan=60');
    });

    it('should return state when power is OFF', async () => {
      serial.resetState();
      const response = await serial.sendCommand('STATE');
      expect(response).toBe('OK:Power=OFF,Temp=22.0,Mode=COOL,Fan=AUTO');
    });
  });

  describe('DEBUG Command', () => {
    it('should enable debug mode', async () => {
      const response = await serial.sendCommand('DEBUG:ON');
      expect(response).toBe('OK:Debug mode enabled');
    });

    it('should disable debug mode', async () => {
      const response = await serial.sendCommand('DEBUG:OFF');
      expect(response).toBe('OK:Debug mode disabled');
    });

    it('should reject invalid debug parameter', async () => {
      const response = await serial.sendCommand('DEBUG:INVALID');
      expect(response).toMatch(/ERROR:/);
    });
  });

  describe('PIN Command', () => {
    it('should set pin HIGH', async () => {
      const response = await serial.sendCommand('PIN:4:HIGH');
      expect(response).toBe('OK:Pin 4 set HIGH');
    });

    it('should set pin LOW', async () => {
      const response = await serial.sendCommand('PIN:4:LOW');
      expect(response).toBe('OK:Pin 4 set LOW');
    });

    it('should handle different pin numbers', async () => {
      const response = await serial.sendCommand('PIN:14:HIGH');
      expect(response).toBe('OK:Pin 14 set HIGH');
    });

    it('should reject invalid pin state', async () => {
      const response = await serial.sendCommand('PIN:4:INVALID');
      expect(response).toMatch(/ERROR:/);
    });
  });

  describe('RAW Command', () => {
    it('should send COOLIX raw code', async () => {
      const response = await serial.sendCommand('RAW:COOLIX:B27BE0');
      expect(response).toBe('OK:Sent COOLIX code 0xB27BE0');
    });

    it('should send NEC raw code', async () => {
      const response = await serial.sendCommand('RAW:NEC:FF00FF00');
      expect(response).toBe('OK:Sent NEC code 0xFF00FF00');
    });

    it('should send BOSCH144 raw code', async () => {
      const response = await serial.sendCommand('RAW:BOSCH144:AABBCCDD');
      expect(response).toBe('OK:Sent BOSCH144 code 0xAABBCCDD');
    });

    it('should reject unsupported protocol', async () => {
      const response = await serial.sendCommand('RAW:INVALID:123456');
      expect(response).toMatch(/ERROR:/);
      expect(response).toMatch(/COOLIX\/NEC\/BOSCH144/);
    });
  });

  describe('Error Handling', () => {
    it('should return error for unknown command', async () => {
      const response = await serial.sendCommand('UNKNOWN');
      expect(response).toMatch(/ERROR:Unknown command:/);
    });

    it('should handle malformed commands', async () => {
      const response = await serial.sendCommand('TEMP');
      expect(response).toMatch(/ERROR:/);
    });

    it('should throw error if not initialized', async () => {
      const uninitSerial = new MockSerialManager();
      await expect(uninitSerial.sendCommand('STATE')).rejects.toThrow('not initialized');
    });
  });

  describe('State Management', () => {
    it('should reset state to defaults', () => {
      serial.sendCommand('POWER:ON');
      serial.sendCommand('TEMP:28.0');
      serial.sendCommand('MODE:HEAT');
      serial.sendCommand('FAN:100');

      serial.resetState();
      const state = serial.getState();

      expect(state.power).toBe(false);
      expect(state.temperature).toBe(22.0);
      expect(state.mode).toBe('COOL');
      expect(state.fanSpeed).toBe('AUTO');
    });

    it('should maintain state across multiple commands', async () => {
      await serial.sendCommand('POWER:ON');
      await serial.sendCommand('TEMP:25.0');
      await serial.sendCommand('MODE:COOL');
      await serial.sendCommand('FAN:80');

      const state = serial.getState();
      expect(state.power).toBe(true);
      expect(state.temperature).toBe(25.0);
      expect(state.mode).toBe('COOL');
      expect(state.fanSpeed).toBe('80');
    });
  });

  describe('Connection Management', () => {
    it('should close connection', async () => {
      await expect(serial.close()).resolves.toBeUndefined();
    });

    it('should allow re-initialization after close', async () => {
      await serial.close();
      await expect(serial.init()).resolves.toBeUndefined();
    });
  });
});
