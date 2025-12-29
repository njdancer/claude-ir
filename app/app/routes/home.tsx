/**
 * ActronAir Control Route
 *
 * Main control interface for the AC unit.
 * - Loader: Fetches current AC state on page load
 * - Action: Handles form submissions (power, temp, mode, fan, special functions)
 */

import { useLoaderData, useFetcher } from 'react-router';
import type { Route } from './+types/home';
import { sendCommand, parseStateResponse, initSerial, isOkResponse, getErrorMessage } from '../lib/serial.server';
import { useState, useEffect } from 'react';

// Loader: Fetch current AC state
export async function loader() {
  try {
    console.log('[Loader] Starting - attempting to initialize serial...');
    await initSerial();
    console.log('[Loader] Serial initialized - sending STATE command...');

    const response = await sendCommand('STATE');
    console.log('[Loader] Received response:', response);

    if (!isOkResponse(response)) {
      const errorMsg = getErrorMessage(response);
      console.error('[Loader] ESP8266 returned error:', errorMsg);
      throw new Error(errorMsg);
    }

    const state = parseStateResponse(response);
    console.log('[Loader] Parsed state:', state);

    return { state, error: null };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Unknown error';
    console.error('[Loader] ERROR:', errorMsg);
    console.error('[Loader] Full error:', error);

    return {
      state: { power: false, temperature: 22.0, mode: 'COOL', fanSpeed: 'AUTO' },
      error: errorMsg,
    };
  }
}

// Action: Handle form submissions
export async function action({ request }: Route.ActionArgs) {
  const formData = await request.formData();
  const intent = formData.get('intent') as string;

  try {
    let response: string;

    switch (intent) {
      case 'power':
        const powerState = formData.get('state') as string;
        response = await sendCommand(`POWER:${powerState}`);
        break;

      case 'setTemp':
        const temp = formData.get('temp') as string;
        response = await sendCommand(`TEMP:${temp}`);
        break;

      case 'setMode':
        const mode = formData.get('mode') as string;
        response = await sendCommand(`MODE:${mode}`);
        break;

      case 'setFan':
        const fanSpeed = formData.get('fanSpeed') as string;
        response = await sendCommand(`FAN:${fanSpeed}`);
        break;

      case 'swing':
        response = await sendCommand('SWING');
        break;

      case 'boost':
        response = await sendCommand('BOOST');
        break;

      case 'led':
        response = await sendCommand('LED');
        break;

      default:
        return { success: false, error: `Unknown intent: ${intent}` };
    }

    if (!isOkResponse(response)) {
      return { success: false, error: getErrorMessage(response) };
    }

    // Parse special function state from response
    const message = response.replace(/^OK:/, '');
    let specialState: { swing?: boolean; boost?: boolean } = {};

    if (intent === 'swing' && message.includes('Swing')) {
      specialState.swing = message.includes('ON');
    } else if (intent === 'boost' && message.includes('Boost')) {
      specialState.boost = message.includes('ON');
    }

    return { success: true, message, ...specialState };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

// Meta: Page title and description
export function meta({}: Route.MetaArgs) {
  return [
    { title: 'ActronAir Control' },
    { name: 'description', content: 'Control your ActronAir AC unit via IR' },
  ];
}

// Component: Main control interface
export default function Home() {
  const { state, error } = useLoaderData<typeof loader>();
  const fetcher = useFetcher();
  const [localTemp, setLocalTemp] = useState(state.temperature);
  const [swingOn, setSwingOn] = useState(false);
  const [boostOn, setBoostOn] = useState(false);

  // Update local temp when state changes
  useEffect(() => {
    setLocalTemp(state.temperature);
  }, [state.temperature]);

  // Update special function states from fetcher response
  useEffect(() => {
    if (fetcher.data?.success) {
      if (fetcher.data.swing !== undefined) {
        setSwingOn(fetcher.data.swing);
      }
      if (fetcher.data.boost !== undefined) {
        setBoostOn(fetcher.data.boost);
      }
    }
  }, [fetcher.data]);

  const handlePower = (powerState: 'ON' | 'OFF') => {
    fetcher.submit({ intent: 'power', state: powerState }, { method: 'post' });
  };

  const handleTempChange = (temp: number) => {
    setLocalTemp(temp);
  };

  const handleTempSubmit = () => {
    fetcher.submit({ intent: 'setTemp', temp: localTemp.toString() }, { method: 'post' });
  };

  const handleModeChange = (mode: string) => {
    fetcher.submit({ intent: 'setMode', mode }, { method: 'post' });
  };

  const handleFanChange = (fanSpeed: string) => {
    fetcher.submit({ intent: 'setFan', fanSpeed }, { method: 'post' });
  };

  const handleSpecialFunction = (func: 'swing' | 'boost' | 'led') => {
    fetcher.submit({ intent: func }, { method: 'post' });
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800">ActronAir Control</h1>
          <p className="text-gray-600 mt-2">IR Remote Control Interface</p>
        </header>

        {/* Error Display */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Fetcher Error Display */}
        {fetcher.data && !fetcher.data.success && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {fetcher.data.error}
          </div>
        )}

        {/* State Display */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Current State</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-gray-600">Power:</span>
              <span className={`ml-2 font-bold ${state.power ? 'text-green-600' : 'text-red-600'}`}>
                {state.power ? 'ON' : 'OFF'}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Temperature:</span>
              <span className="ml-2 font-bold text-gray-800">{state.temperature.toFixed(1)}°C</span>
            </div>
            <div>
              <span className="text-gray-600">Mode:</span>
              <span className="ml-2 font-bold text-gray-800">{state.mode}</span>
            </div>
            <div>
              <span className="text-gray-600">Fan:</span>
              <span className="ml-2 font-bold text-gray-800">{state.fanSpeed}</span>
            </div>
          </div>
        </div>

        {/* Power Control */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Power</h2>
          <div className="flex gap-4">
            <button
              onClick={() => handlePower('ON')}
              disabled={fetcher.state !== 'idle'}
              className="flex-1 bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-6 rounded disabled:opacity-50"
            >
              Power ON
            </button>
            <button
              onClick={() => handlePower('OFF')}
              disabled={fetcher.state !== 'idle'}
              className="flex-1 bg-red-500 hover:bg-red-600 text-white font-bold py-3 px-6 rounded disabled:opacity-50"
            >
              Power OFF
            </button>
          </div>
        </div>

        {/* Temperature Control */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Temperature</h2>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="16"
              max="30"
              step="0.5"
              value={localTemp}
              onChange={(e) => handleTempChange(parseFloat(e.target.value))}
              className="flex-1"
            />
            <span className="text-2xl font-bold w-24 text-center text-gray-800">{localTemp.toFixed(1)}°C</span>
            <button
              onClick={handleTempSubmit}
              disabled={fetcher.state !== 'idle' || localTemp === state.temperature}
              className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
            >
              Set
            </button>
          </div>
        </div>

        {/* Mode Control */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Mode</h2>
          <div className="grid grid-cols-5 gap-2">
            {['COOL', 'HEAT', 'DRY', 'FAN', 'AUTO'].map((mode) => (
              <button
                key={mode}
                onClick={() => handleModeChange(mode)}
                disabled={fetcher.state !== 'idle'}
                className={`py-3 px-4 rounded font-semibold ${
                  state.mode === mode
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-800'
                } disabled:opacity-50`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        {/* Fan Speed Control */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Fan Speed</h2>
          <div className="grid grid-cols-6 gap-2">
            {['AUTO', '20', '40', '60', '80', '100'].map((speed) => (
              <button
                key={speed}
                onClick={() => handleFanChange(speed)}
                disabled={fetcher.state !== 'idle'}
                className={`py-3 px-4 rounded font-semibold ${
                  state.fanSpeed === speed
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-800'
                } disabled:opacity-50`}
              >
                {speed}
              </button>
            ))}
          </div>
        </div>

        {/* Special Functions */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Special Functions</h2>
          <div className="grid grid-cols-3 gap-4">
            <button
              onClick={() => handleSpecialFunction('swing')}
              disabled={fetcher.state !== 'idle'}
              className={`font-bold py-3 px-6 rounded disabled:opacity-50 transition-colors ${
                swingOn
                  ? 'bg-purple-600 hover:bg-purple-700 text-white ring-2 ring-purple-300'
                  : 'bg-purple-200 hover:bg-purple-300 text-purple-900'
              }`}
            >
              <div>Swing</div>
              <div className="text-sm">{swingOn ? 'ON' : 'OFF'}</div>
            </button>
            <button
              onClick={() => handleSpecialFunction('boost')}
              disabled={fetcher.state !== 'idle'}
              className={`font-bold py-3 px-6 rounded disabled:opacity-50 transition-colors ${
                boostOn
                  ? 'bg-orange-600 hover:bg-orange-700 text-white ring-2 ring-orange-300'
                  : 'bg-orange-200 hover:bg-orange-300 text-orange-900'
              }`}
            >
              <div>Boost</div>
              <div className="text-sm">{boostOn ? 'ON' : 'OFF'}</div>
            </button>
            <button
              onClick={() => handleSpecialFunction('led')}
              disabled={fetcher.state !== 'idle'}
              className="bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-3 px-6 rounded disabled:opacity-50 transition-colors"
            >
              LED Toggle
            </button>
          </div>
        </div>

        {/* Loading Indicator */}
        {fetcher.state !== 'idle' && (
          <div className="fixed bottom-4 right-4 bg-blue-500 text-white px-6 py-3 rounded shadow-lg">
            Sending command...
          </div>
        )}
      </div>
    </div>
  );
}
