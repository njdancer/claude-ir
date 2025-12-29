/**
 * Mock Serial Manager for Testing
 *
 * Simulates ESP8266 responses without requiring actual hardware.
 * Used for unit tests, E2E tests, and development.
 */

export interface ACState {
  power: boolean;
  temperature: number; // 16.0 - 30.0
  mode: 'COOL' | 'HEAT' | 'DRY' | 'FAN' | 'AUTO';
  fanSpeed: 'AUTO' | '20' | '40' | '60' | '80' | '100';
}

export class MockSerialManager {
  private state: ACState = {
    power: false,
    temperature: 22.0,
    mode: 'COOL',
    fanSpeed: 'AUTO',
  };

  private connected = false;

  /**
   * Initialize mock serial connection (no-op)
   */
  async init(): Promise<void> {
    this.connected = true;
    return Promise.resolve();
  }

  /**
   * Send command to mock ESP8266 and get response
   */
  async sendCommand(cmd: string): Promise<string> {
    if (!this.connected) {
      throw new Error('Serial port not initialized');
    }

    const trimmedCmd = cmd.trim();
    const colonPos = trimmedCmd.indexOf(':');
    const command = colonPos === -1 ? trimmedCmd : trimmedCmd.substring(0, colonPos);
    const param = colonPos === -1 ? '' : trimmedCmd.substring(colonPos + 1);

    switch (command) {
      case 'POWER':
        if (param === 'ON') {
          this.state.power = true;
          return 'OK:Power ON, sent BOSCH144 command';
        } else if (param === 'OFF') {
          this.state.power = false;
          return 'OK:Power OFF, sent COOLIX command';
        }
        return 'ERROR:Invalid parameter. Use POWER:ON or POWER:OFF';

      case 'TEMP':
        const temp = parseFloat(param);
        if (this.validateTemperature(temp)) {
          this.state.temperature = temp;
          this.state.power = true; // Setting temp implies power on
          return `OK:Temperature set to ${temp.toFixed(1)}C`;
        }
        return 'ERROR:Invalid temperature. Use 16.0-30.0 in 0.5° steps';

      case 'MODE':
        if (['COOL', 'HEAT', 'DRY', 'FAN', 'AUTO'].includes(param)) {
          this.state.mode = param as ACState['mode'];
          this.state.power = true; // Setting mode implies power on
          return `OK:Mode set to ${param}`;
        }
        return 'ERROR:Invalid mode. Use COOL/HEAT/DRY/FAN/AUTO';

      case 'FAN':
        if (['AUTO', '20', '40', '60', '80', '100'].includes(param)) {
          this.state.fanSpeed = param as ACState['fanSpeed'];
          this.state.power = true; // Setting fan implies power on
          return `OK:Fan set to ${param}`;
        }
        return 'ERROR:Invalid fan speed. Use AUTO/20/40/60/80/100';

      case 'SWING':
        return 'OK:Swing toggled';

      case 'BOOST':
        return 'OK:Boost activated';

      case 'LED':
        return 'OK:LED toggled';

      case 'STATE':
        return `OK:Power=${this.state.power ? 'ON' : 'OFF'},Temp=${this.state.temperature.toFixed(1)},Mode=${this.state.mode},Fan=${this.state.fanSpeed}`;

      case 'DEBUG':
        if (param === 'ON' || param === 'OFF') {
          return `OK:Debug mode ${param === 'ON' ? 'enabled' : 'disabled'}`;
        }
        return 'ERROR:Invalid parameter. Use DEBUG:ON or DEBUG:OFF';

      case 'PIN': {
        // PIN:4:HIGH or PIN:4:LOW
        const parts = param.split(':');
        if (parts.length !== 2) {
          return 'ERROR:Invalid format. Use PIN:<pin>:<HIGH|LOW>';
        }
        const [pin, pinState] = parts;
        if (pinState === 'HIGH' || pinState === 'LOW') {
          return `OK:Pin ${pin} set ${pinState}`;
        }
        return 'ERROR:Invalid format. Use PIN:<pin>:<HIGH|LOW>';
      }

      case 'RAW': {
        // RAW:COOLIX:B27BE0 or RAW:BOSCH144:hex
        const parts = param.split(':');
        if (parts.length !== 2) {
          return 'ERROR:Invalid format. Use RAW:<protocol>:<hex_code>';
        }
        const [protocol, code] = parts;
        if (['COOLIX', 'NEC', 'BOSCH144'].includes(protocol)) {
          return `OK:Sent ${protocol} code 0x${code}`;
        }
        return 'ERROR:Unsupported protocol. Use COOLIX/NEC/BOSCH144';
      }

      default:
        return `ERROR:Unknown command: ${command}`;
    }
  }

  /**
   * Get current AC state (for testing)
   */
  getState(): ACState {
    return { ...this.state };
  }

  /**
   * Reset state to defaults (for testing)
   */
  resetState(): void {
    this.state = {
      power: false,
      temperature: 22.0,
      mode: 'COOL',
      fanSpeed: 'AUTO',
    };
  }

  /**
   * Close connection (no-op for mock)
   */
  async close(): Promise<void> {
    this.connected = false;
    return Promise.resolve();
  }

  /**
   * Validate temperature is in range and 0.5° increments
   */
  private validateTemperature(temp: number): boolean {
    if (temp < 16.0 || temp > 30.0) {
      return false;
    }

    // Check 0.5° increments
    const remainder = temp % 0.5;
    return remainder < 0.01 || remainder > 0.49; // Allow small floating point errors
  }
}

export const serialManager = new MockSerialManager();
