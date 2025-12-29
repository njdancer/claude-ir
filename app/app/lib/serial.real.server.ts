/**
 * Real Serial Manager
 *
 * Communicates with ESP8266 over USB serial port.
 * Uses Node.js serialport package.
 */

import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';

export class RealSerialManager {
  private port: SerialPort | null = null;
  private parser: ReadlineParser | null = null;
  private portPath: string;
  private baudRate: number;
  private bufferDrained: boolean = false;

  constructor(portPath?: string, baudRate: number = 115200) {
    // Auto-detect port or use provided path
    // Common paths: /dev/ttyUSB0 (Linux), /dev/cu.usbserial-* (macOS), COM3 (Windows)
    this.portPath = portPath || this.detectPortPath();
    this.baudRate = baudRate;
  }

  /**
   * Detect serial port path based on platform
   */
  private detectPortPath(): string {
    const platform = process.platform;

    if (platform === 'darwin') {
      // macOS: /dev/cu.usbserial-*
      // Note: This is a placeholder - actual detection requires listing ports
      return '/dev/cu.usbserial-0001';
    } else if (platform === 'linux') {
      // Linux: /dev/ttyUSB0
      return '/dev/ttyUSB0';
    } else if (platform === 'win32') {
      // Windows: COM3
      return 'COM3';
    }

    throw new Error(`Unsupported platform: ${platform}`);
  }

  /**
   * Initialize serial port connection
   */
  async init(): Promise<void> {
    if (this.port) {
      return; // Already initialized
    }

    return new Promise((resolve, reject) => {
      this.port = new SerialPort({
        path: this.portPath,
        baudRate: this.baudRate,
        autoOpen: false,
      });

      this.port.open((err) => {
        if (err) {
          reject(new Error(`Failed to open serial port ${this.portPath}: ${err.message}`));
          return;
        }

        // Create line parser (reads until \n)
        this.parser = this.port!.pipe(new ReadlineParser({ delimiter: '\n' }));

        // Mark that buffer needs draining (boot messages, etc.)
        this.bufferDrained = false;

        resolve();
      });
    });
  }

  /**
   * Drain any buffered data from the parser
   */
  private async drainBuffer(drainTime: number = 100): Promise<void> {
    return new Promise((resolve) => {
      const drainHandler = () => {
        // Discard data
      };

      // Listen and discard any data for a short time
      this.parser!.on('data', drainHandler);

      setTimeout(() => {
        this.parser!.removeListener('data', drainHandler);
        resolve();
      }, drainTime);
    });
  }

  /**
   * Send command to ESP8266 and wait for response
   */
  async sendCommand(cmd: string, timeout: number = 5000): Promise<string> {
    if (!this.port || !this.parser) {
      throw new Error('Serial port not initialized. Call init() first.');
    }

    // Drain buffer only once after opening the port (to clear boot messages)
    if (!this.bufferDrained) {
      await this.drainBuffer(200); // Wait longer on first drain to catch all boot messages
      this.bufferDrained = true;
    }

    return new Promise((resolve, reject) => {
      // Set timeout
      const timer = setTimeout(() => {
        this.parser!.removeListener('data', responseHandler);
        reject(new Error(`Timeout waiting for response to: ${cmd}`));
      }, timeout);

      // Listen for response
      const responseHandler = (data: string) => {
        clearTimeout(timer);
        this.parser!.removeListener('data', responseHandler);
        resolve(data.trim());
      };

      this.parser!.once('data', responseHandler);

      // Send command (with newline)
      this.port!.write(`${cmd}\n`, (err) => {
        if (err) {
          clearTimeout(timer);
          this.parser!.removeListener('data', responseHandler);
          reject(new Error(`Failed to send command: ${err.message}`));
        }
      });
    });
  }

  /**
   * Close serial port
   */
  async close(): Promise<void> {
    if (!this.port) {
      return;
    }

    return new Promise((resolve, reject) => {
      this.port!.close((err) => {
        if (err) {
          reject(new Error(`Failed to close serial port: ${err.message}`));
        } else {
          this.port = null;
          this.parser = null;
          resolve();
        }
      });
    });
  }

  /**
   * List available serial ports
   */
  static async listPorts(): Promise<string[]> {
    const ports = await SerialPort.list();
    return ports.map((port) => port.path);
  }

  /**
   * Get port path
   */
  getPortPath(): string {
    return this.portPath;
  }

  /**
   * Set port path (must call before init())
   */
  setPortPath(path: string): void {
    if (this.port) {
      throw new Error('Cannot change port path while connected. Call close() first.');
    }
    this.portPath = path;
  }
}

export const serialManager = new RealSerialManager();
