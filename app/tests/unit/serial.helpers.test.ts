/**
 * Unit Tests for Serial Helper Functions
 */

import { describe, it, expect } from 'vitest';
import { parseStateResponse, isOkResponse, getErrorMessage } from '../../app/lib/serial.server';

describe('Serial Helper Functions', () => {
  describe('parseStateResponse', () => {
    it('should parse valid state response with power ON', () => {
      const response = 'OK:Power=ON,Temp=24.5,Mode=HEAT,Fan=60';
      const state = parseStateResponse(response);

      expect(state.power).toBe(true);
      expect(state.temperature).toBe(24.5);
      expect(state.mode).toBe('HEAT');
      expect(state.fanSpeed).toBe('60');
    });

    it('should parse valid state response with power OFF', () => {
      const response = 'OK:Power=OFF,Temp=22.0,Mode=COOL,Fan=AUTO';
      const state = parseStateResponse(response);

      expect(state.power).toBe(false);
      expect(state.temperature).toBe(22.0);
      expect(state.mode).toBe('COOL');
      expect(state.fanSpeed).toBe('AUTO');
    });

    it('should parse all mode types', () => {
      const modes = ['COOL', 'HEAT', 'DRY', 'FAN', 'AUTO'];
      modes.forEach((mode) => {
        const response = `OK:Power=ON,Temp=22.0,Mode=${mode},Fan=AUTO`;
        const state = parseStateResponse(response);
        expect(state.mode).toBe(mode);
      });
    });

    it('should parse all fan speeds', () => {
      const fanSpeeds = ['AUTO', '20', '40', '60', '80', '100'];
      fanSpeeds.forEach((fanSpeed) => {
        const response = `OK:Power=ON,Temp=22.0,Mode=COOL,Fan=${fanSpeed}`;
        const state = parseStateResponse(response);
        expect(state.fanSpeed).toBe(fanSpeed);
      });
    });

    it('should parse temperature range', () => {
      const temps = [16.0, 18.5, 22.0, 25.5, 30.0];
      temps.forEach((temp) => {
        const response = `OK:Power=ON,Temp=${temp},Mode=COOL,Fan=AUTO`;
        const state = parseStateResponse(response);
        expect(state.temperature).toBe(temp);
      });
    });

    it('should handle whitespace in response', () => {
      const response = 'OK: Power=ON, Temp=22.0, Mode=COOL, Fan=AUTO';
      const state = parseStateResponse(response);

      expect(state.power).toBe(true);
      expect(state.temperature).toBe(22.0);
      expect(state.mode).toBe('COOL');
      expect(state.fanSpeed).toBe('AUTO');
    });
  });

  describe('isOkResponse', () => {
    it('should return true for OK responses', () => {
      expect(isOkResponse('OK:Power ON')).toBe(true);
      expect(isOkResponse('OK:Temperature set to 22.0C')).toBe(true);
      expect(isOkResponse('OK:Mode set to COOL')).toBe(true);
    });

    it('should return false for ERROR responses', () => {
      expect(isOkResponse('ERROR:Invalid temperature')).toBe(false);
      expect(isOkResponse('ERROR:Unknown command')).toBe(false);
    });

    it('should return false for invalid responses', () => {
      expect(isOkResponse('Invalid response')).toBe(false);
      expect(isOkResponse('')).toBe(false);
    });
  });

  describe('getErrorMessage', () => {
    it('should extract error message', () => {
      expect(getErrorMessage('ERROR:Invalid temperature')).toBe('Invalid temperature');
      expect(getErrorMessage('ERROR:Unknown command: INVALID')).toBe('Unknown command: INVALID');
    });

    it('should handle error without ERROR prefix', () => {
      expect(getErrorMessage('Invalid temperature')).toBe('Invalid temperature');
    });

    it('should handle empty error', () => {
      expect(getErrorMessage('ERROR:')).toBe('');
    });
  });
});
