import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SettingsPanel from './components/SettingsPanel';
import SelfCorrectionLog from './components/SelfCorrectionLog';
import SystemStatusLog from './components/SystemStatusLog';
import MetaPromptManager from './components/MetaPromptManager';
import { createParser } from 'eventsource-parser';
import './index.css';

function App() {
  const [settings, setSettings] = useState({
    max_iterations: 3,
    model_temperature: 0.7,
    architect_temperature: 0.2,
    providers: {
      orchestrator: 'gemini',
      enhancer: 'architect',
    },
    evaluation_mode: 'basic',
    enable_self_correction: false,
    self_correction_iterations: 3,
  });
  const [initialPrompt, setInitialPrompt] = useState('');
  const [results, setResults] = useState([]);
  const [selfCorrectionLog, setSelfCorrectionLog] = useState([]);
  const [systemStatusLog, setSystemStatusLog] = useState([]);
  const [finalReport, setFinalReport] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showPromptManager, setShowPromptManager] = useState(false);

  const handleRefine = async () => {
    setResults([]);
    setSelfCorrectionLog([]);
    setSystemStatusLog([]);
    setFinalReport(null);
    setError(null);
    setIsLoading(true);

    // Use relative URL for production, absolute for development
    const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : '';
    const response = await fetch(`${API_BASE}/api/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            initial_prompt: initialPrompt,
            ...settings
        })
    });

    if (!response.ok) {
        setError(`Server error: ${response.statusText}`);
        setIsLoading(false);
        return;
    }

    const onParse = (event) => {
        if (event.type === 'event') {
            const eventName = event.event;
            
            try {
                // The data payload is always a JSON string from our FastAPI server
                const data = JSON.parse(event.data);
                
                if (eventName === 'iteration_result') {
                    setResults(prev => [...prev, data]);
                } else if (eventName.startsWith('self_correction')) {
                    setSelfCorrectionLog(prev => [...prev, { event: eventName, data }]);
                } else if (eventName.startsWith('system_')) {
                    setSystemStatusLog(prev => [...prev, { event: eventName, data }]);
                } else if (eventName === 'final_report') {
                    setFinalReport(data);
                    setIsLoading(false);
                } else if (eventName === 'complete') {
                    console.log("Stream complete.");
                    setIsLoading(false);
                } else if (eventName === 'error') {
                    setError(data.message || 'An unknown error occurred.');
                    setIsLoading(false);
                } else if (eventName === 'message') {
                    // Generic messages for logging/toasting
                    console.log("Server message:", data);
                }
            } catch (e) {
                console.error("Failed to parse event data:", event.data, e);
                // Also handle non-JSON data if necessary, though our server shouldn't send it
                if (event.data.includes("Stream finished")) {
                    setIsLoading(false);
                }
            }
        }
    };
    
    const parser = createParser(onParse);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }
            const chunk = decoder.decode(value);
            parser.feed(chunk);
        }
    } catch (e) {
        setError("Error reading stream from server.");
        console.error(e);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 text-white min-h-screen font-sans">
      <header className="bg-gray-800 p-4 shadow-md">
        <h1 className="text-3xl font-bold text-center text-blue-400">MPLA Web Interface</h1>
      </header>
      <main className="p-4 md:p-8">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Settings and Input */}
          <div className="lg:col-span-1 flex flex-col gap-8">
            <SettingsPanel settings={settings} setSettings={setSettings} />
            
            <div className="bg-gray-800 p-4 rounded-lg shadow-inner">
                <h2 className="text-xl font-bold mb-4">Initial Prompt</h2>
                <textarea
                    value={initialPrompt}
                    onChange={(e) => setInitialPrompt(e.target.value)}
                    className="w-full h-40 bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="Enter the prompt you want to refine..."
                />
                <button
                    onClick={handleRefine}
                    disabled={isLoading || !initialPrompt}
                    className="w-full mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 text-white font-bold py-2 px-4 rounded-md transition-colors duration-300"
                >
                    {isLoading ? 'Refining...' : 'Run Refinement'}
                </button>
            </div>
            
            {/* Meta-Prompt Manager (Collapsible) */}
            <div className="bg-gray-800 p-4 rounded-lg shadow-inner">
              <button 
                onClick={() => setShowPromptManager(!showPromptManager)}
                className="w-full text-left font-bold text-lg flex justify-between items-center"
              >
                <span>Meta-Prompt Configuration</span>
                <span>{showPromptManager ? '▼' : '▶'}</span>
              </button>
              {showPromptManager && <MetaPromptManager />}
            </div>
          </div>

          {/* Right Column: Results */}
          <div className="lg:col-span-2 bg-gray-800 p-4 rounded-lg shadow-inner min-h-[500px]">
            <h2 className="text-xl font-bold mb-4 border-b border-gray-600 pb-2">Refinement Results</h2>
            <div className="space-y-6 overflow-y-auto h-[calc(100vh-250px)] p-2">
                {error && <div className="text-red-400 bg-red-900/50 p-3 rounded-md">{error}</div>}
                
                <SystemStatusLog statusLog={systemStatusLog} />
                <SelfCorrectionLog log={selfCorrectionLog} />

                {results.map((result, index) => (
                    <div key={index} className="bg-gray-700/50 p-4 rounded-lg animate-fade-in">
                        <h3 className="font-bold text-lg text-blue-300">Iteration {result.iteration}</h3>
                        <div className="mt-2">
                            <h4 className="font-semibold text-gray-300">New Prompt:</h4>
                            <p className="text-gray-200 bg-gray-900 p-3 rounded-md mt-1 whitespace-pre-wrap">{result.prompt}</p>
                        </div>
                        <div className="mt-3">
                            <h4 className="font-semibold text-gray-300">Rationale:</h4>
                            <p className="text-gray-400 italic mt-1">{result.rationale}</p>
                        </div>
                        <div className="bg-gray-800 p-4 rounded-lg mt-4">
                            <h3 className="text-lg font-semibold text-gray-200">AI Output:</h3>
                            <div className="prose prose-invert mt-2 text-gray-300 max-w-none">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {result.raw_ai_output}
                                </ReactMarkdown>
                            </div>
                        </div>
                        <div className="mt-3">
                            <h4 className="font-semibold text-gray-300">Evaluation:</h4>
                            <pre className="text-sm text-yellow-300 bg-gray-900 p-3 rounded-md mt-1">{JSON.stringify(result.evaluation, null, 2)}</pre>
                        </div>
                    </div>
                ))}

                {finalReport && (
                    <div className="bg-green-800/20 border border-green-500 p-4 rounded-lg animate-fade-in">
                        <h3 className="font-bold text-xl text-green-300">Final Report</h3>
                        <div className="prose prose-invert mt-2 text-gray-300 max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {finalReport.content || 'No content in report.'}
                            </ReactMarkdown>
                        </div>
                    </div>
                )}

                {isLoading && results.length === 0 && <div className="text-center p-8">Waiting for refinement to start...</div>}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App 