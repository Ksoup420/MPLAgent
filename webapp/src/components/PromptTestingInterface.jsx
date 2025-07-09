import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const PromptTestingInterface = () => {
  const [promptVariants, setPromptVariants] = useState([]);
  const [testResults, setTestResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedPromptType, setSelectedPromptType] = useState('architect');
  const [selectedModel, setSelectedModel] = useState('gemini-2.0-flash');
  const [showDetailedResults, setShowDetailedResults] = useState(false);
  const [error, setError] = useState(null);

  // Load available prompt variants
  useEffect(() => {
    loadPromptVariants();
  }, []);

  const loadPromptVariants = async () => {
    try {
      const response = await fetch('/api/prompt-variants');
      if (response.ok) {
        const variants = await response.json();
        setPromptVariants(variants);
      }
    } catch (err) {
      console.error('Failed to load prompt variants:', err);
    }
  };

  const runPromptTests = async () => {
    setLoading(true);
    setError(null);
    setTestResults(null);

    try {
      const response = await fetch('/api/prompt-testing/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt_type: selectedPromptType,
          model: selectedModel,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const results = await response.json();
      setTestResults(results);
    } catch (err) {
      setError(`Failed to run prompt tests: ${err.message}`);
      console.error('Error running prompt tests:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderVariantPerformance = () => {
    if (!testResults?.summary_metrics?.variant_performance) return null;

    const performance = testResults.summary_metrics.variant_performance;
    
    return (
      <div className="bg-gray-800 p-4 rounded-lg">
        <h3 className="text-lg font-bold text-white mb-4">📊 Variant Performance</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-600">
                <th className="text-left py-2 px-3 text-gray-300">Variant Name</th>
                <th className="text-left py-2 px-3 text-gray-300">Success Rate</th>
                <th className="text-left py-2 px-3 text-gray-300">Avg Quality</th>
                <th className="text-left py-2 px-3 text-gray-300">Avg Time (s)</th>
                <th className="text-left py-2 px-3 text-gray-300">Tests</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(performance).map(([variantId, perf]) => (
                <tr key={variantId} className="border-b border-gray-700">
                  <td className="py-2 px-3 text-white font-medium">{perf.name}</td>
                  <td className="py-2 px-3">
                    <span className={`${perf.success_rate >= 0.8 ? 'text-green-400' : 
                      perf.success_rate >= 0.6 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {(perf.success_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-2 px-3">
                    <span className={`${perf.avg_quality_score >= 0.7 ? 'text-green-400' : 
                      perf.avg_quality_score >= 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {perf.avg_quality_score.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-gray-300">{perf.avg_execution_time.toFixed(2)}</td>
                  <td className="py-2 px-3 text-gray-300">{perf.total_tests}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderBestVariant = () => {
    if (!testResults?.summary_metrics?.best_variant) return null;

    const best = testResults.summary_metrics.best_variant;
    
    return (
      <div className="bg-green-900/30 border border-green-600/50 p-4 rounded-lg">
        <h3 className="text-lg font-bold text-green-300 mb-2">🏆 Best Performing Variant</h3>
        <div className="text-white">
          <p className="text-xl font-semibold">{best.name}</p>
          <p className="text-green-400">Quality Score: {best.score.toFixed(2)}</p>
        </div>
      </div>
    );
  };

  const renderRecommendations = () => {
    if (!testResults?.recommendations?.length) return null;

    return (
      <div className="bg-blue-900/30 border border-blue-600/50 p-4 rounded-lg">
        <h3 className="text-lg font-bold text-blue-300 mb-3">💡 Recommendations</h3>
        <ul className="space-y-2">
          {testResults.recommendations.map((rec, index) => (
            <li key={index} className="text-white text-sm flex items-start">
              <span className="text-blue-400 mr-2">{index + 1}.</span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const renderDetailedResults = () => {
    if (!showDetailedResults || !testResults?.results) return null;

    return (
      <div className="bg-gray-800 p-4 rounded-lg">
        <h3 className="text-lg font-bold text-white mb-4">🔍 Detailed Test Results</h3>
        <div className="max-h-96 overflow-y-auto space-y-3">
          {testResults.results.map((result, index) => (
            <div key={index} className={`p-3 rounded border ${
              result.success ? 'bg-green-900/20 border-green-600/30' : 'bg-red-900/20 border-red-600/30'
            }`}>
              <div className="flex justify-between items-start mb-2">
                <span className="text-white font-medium">
                  Test Case: {result.test_case_id}
                </span>
                <span className={`text-sm px-2 py-1 rounded ${
                  result.success ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                }`}>
                  {result.success ? 'Success' : 'Failed'}
                </span>
              </div>
              
              {result.success && result.quality_scores && (
                <div className="text-sm text-gray-300 mb-2">
                  <span>Quality: {result.quality_scores.overall_quality?.toFixed(2) || 'N/A'}</span>
                  <span className="ml-4">Time: {result.execution_time.toFixed(2)}s</span>
                </div>
              )}
              
              {result.error_message && (
                <p className="text-red-400 text-sm">{result.error_message}</p>
              )}
              
              {result.output && (
                <details className="mt-2">
                  <summary className="text-blue-400 cursor-pointer text-sm">Show Output</summary>
                  <div className="mt-2 p-2 bg-gray-900 rounded text-xs text-gray-300 max-h-32 overflow-y-auto">
                    {result.output}
                  </div>
                </details>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-white">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">🧪 MPLA Prompt Testing Framework</h1>
        
        {/* Configuration Section */}
        <div className="bg-gray-800 p-6 rounded-lg mb-6">
          <h2 className="text-xl font-bold mb-4">Test Configuration</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Prompt Type
              </label>
              <select
                value={selectedPromptType}
                onChange={(e) => setSelectedPromptType(e.target.value)}
                className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                disabled={loading}
              >
                <option value="architect">Architect Prompts</option>
                <option value="analyzer">Analyzer Prompts</option>
                <option value="reviser">Reviser Prompts</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                AI Model
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-white"
                disabled={loading}
              >
                <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
              </select>
            </div>
          </div>

          <div className="flex gap-4">
            <button
              onClick={runPromptTests}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-6 py-2 rounded font-medium flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Running Tests...
                </>
              ) : (
                <>
                  ▶️ Run Prompt Tests
                </>
              )}
            </button>
            
            {testResults && (
              <button
                onClick={() => setShowDetailedResults(!showDetailedResults)}
                className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded font-medium"
              >
                {showDetailedResults ? 'Hide' : 'Show'} Detailed Results
              </button>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/50 border border-red-600/50 p-4 rounded-lg mb-6">
            <h3 className="text-lg font-bold text-red-300 mb-2">❌ Error</h3>
            <p className="text-white">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-gray-800 p-8 rounded-lg mb-6 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
            <p className="text-gray-300">Running comprehensive prompt tests...</p>
            <p className="text-sm text-gray-400 mt-2">This may take several minutes</p>
          </div>
        )}

        {/* Results Section */}
        {testResults && (
          <div className="space-y-6">
            {/* Summary Statistics */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="text-lg font-bold text-white mb-4">📊 Summary Statistics</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-400">
                    {testResults.summary_metrics.total_tests}
                  </div>
                  <div className="text-sm text-gray-300">Total Tests</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">
                    {testResults.summary_metrics.successful_tests}
                  </div>
                  <div className="text-sm text-gray-300">Successful</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-400">
                    {(testResults.summary_metrics.success_rate * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-300">Success Rate</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-400">
                    {Object.keys(testResults.summary_metrics.variant_performance || {}).length}
                  </div>
                  <div className="text-sm text-gray-300">Variants Tested</div>
                </div>
              </div>
            </div>

            {/* Best Variant */}
            {renderBestVariant()}

            {/* Variant Performance Table */}
            {renderVariantPerformance()}

            {/* Recommendations */}
            {renderRecommendations()}

            {/* Detailed Results */}
            {renderDetailedResults()}
          </div>
        )}

        {/* Information Section */}
        <div className="bg-gray-800 p-4 rounded-lg mt-6">
          <h3 className="text-lg font-bold text-white mb-3">ℹ️ About Prompt Testing</h3>
          <div className="text-gray-300 text-sm space-y-2">
            <p>
              This testing framework evaluates different prompt variants across multiple test cases to determine
              which prompts perform best for your specific use cases.
            </p>
            <p>
              <strong>Test Categories:</strong> Easy (clear objectives), Medium (ambiguous requirements), 
              Hard (complex multi-part tasks), Edge cases (error handling)
            </p>
            <p>
              <strong>Quality Metrics:</strong> Output relevance, structure quality, characteristic coverage, 
              execution success rate, and response time.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PromptTestingInterface; 