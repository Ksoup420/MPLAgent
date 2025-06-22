import React from 'react';

const SettingsPanel = ({ settings, setSettings }) => {
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleProviderChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      providers: { ...prev.providers, [name]: value }
    }));
  };

  return (
    <div className="bg-gray-800 p-4 rounded-lg shadow-inner">
      <h2 className="text-xl font-bold mb-4 border-b border-gray-600 pb-2">Settings</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Max Iterations */}
        <div className="flex flex-col">
          <label htmlFor="max_iterations" className="mb-2 font-semibold text-gray-300">Max Iterations</label>
          <input
            type="number"
            id="max_iterations"
            name="max_iterations"
            value={settings.max_iterations}
            onChange={handleInputChange}
            className="bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            min="1"
            max="10"
          />
        </div>

        {/* Temperature */}
        <div className="flex flex-col">
          <label htmlFor="model_temperature" className="mb-2 font-semibold text-gray-300">Model Temperature</label>
          <input
            type="range"
            id="model_temperature"
            name="model_temperature"
            value={settings.model_temperature}
            onChange={handleInputChange}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            min="0"
            max="2.0"
            step="0.1"
          />
          <span className="text-center text-sm text-gray-400 mt-1">{settings.model_temperature}</span>
        </div>

        {/* Architect-specific settings */}
        {settings.providers.enhancer === 'architect' && (
          <>
            {/* Architect Temperature Slider */}
            <div className="flex flex-col">
              <label htmlFor="architect_temperature" className="mb-2 font-semibold text-gray-300">
                Architect Temperature: <span className="text-blue-400 font-mono">{settings.architect_temperature}</span>
              </label>
              <input
                type="range"
                id="architect_temperature"
                name="architect_temperature"
                min="0"
                max="1.0"
                step="0.1"
                value={settings.architect_temperature}
                onChange={handleInputChange}
                className="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer"
              />
               <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Consistent</span>
                <span>Creative</span>
              </div>
            </div>

            {/* Self-Correction Toggle */}
            <div className="flex items-center justify-between col-span-1 md:col-span-2 bg-gray-700 p-3 rounded-md">
              <label htmlFor="enable_self_correction" className="font-semibold text-gray-200">Enable Self-Correction</label>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  id="enable_self_correction"
                  name="enable_self_correction"
                  checked={settings.enable_self_correction}
                  onChange={(e) => setSettings(prev => ({ ...prev, enable_self_correction: e.target.checked }))}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-600 rounded-full peer peer-focus:ring-4 peer-focus:ring-blue-800 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {/* Self-Correction Iterations Slider */}
            {settings.enable_self_correction && (
               <div className="flex flex-col col-span-1 md:col-span-2">
                <label htmlFor="self_correction_iterations" className="mb-2 font-semibold text-gray-300">
                  Self-Correction Iterations: <span className="text-blue-400 font-mono">{settings.self_correction_iterations}</span>
                </label>
                <input
                  type="range"
                  id="self_correction_iterations"
                  name="self_correction_iterations"
                  min="1"
                  max="5"
                  step="1"
                  value={settings.self_correction_iterations}
                  onChange={handleInputChange}
                  className="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer"
                />
              </div>
            )}
          </>
        )}

        {/* Orchestrator Provider */}
        <div className="flex flex-col">
          <label htmlFor="orchestrator" className="mb-2 font-semibold text-gray-300">AI Provider</label>
          <select
            id="orchestrator"
            name="orchestrator"
            value={settings.providers.orchestrator}
            onChange={handleProviderChange}
            className="bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="gemini">Gemini</option>
            <option value="openai">OpenAI</option>
          </select>
        </div>
        
        {/* Enhancer Provider */}
        <div className="flex flex-col">
          <label htmlFor="enhancer" className="mb-2 font-semibold text-gray-300">Enhancer</label>
          <select
            id="enhancer"
            name="enhancer"
            value={settings.providers.enhancer}
            onChange={handleProviderChange}
            className="bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="rule_based">Rule-Based</option>
            <option value="llm_assisted">LLM-Assisted</option>
            <option value="architect">Architect</option>
          </select>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel; 