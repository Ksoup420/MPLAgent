import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SelfCorrectionLog = ({ log }) => {
  if (!log || log.length === 0) {
    return null;
  }

  const renderLogEntry = (entry, index) => {
    const { event, data } = entry;

    switch (event) {
      case 'self_correction_status':
        return (
          <div key={index} className="text-sm text-cyan-400 italic">
            <p>&gt; Status: {data.status} {data.iteration && `(${data.iteration}/${data.max_iterations})`}</p>
            {data.message && <p className="ml-4">{data.message}</p>}
          </div>
        );
      
      case 'self_correction_analysis':
        return (
          <div key={index} className="bg-gray-800/50 p-3 rounded-md my-2">
            <p className="font-semibold text-yellow-400">Analysis Result:</p>
            <p className="text-sm text-gray-300 mt-1">{data.feedback_summary}</p>
            {data.flaws_found && (
               <pre className="text-xs bg-gray-900 p-2 mt-2 rounded-md overflow-x-auto">
                {JSON.stringify(data.analysis_summary, null, 2)}
              </pre>
            )}
          </div>
        );

      case 'self_correction_revision':
        return (
          <div key={index} className="bg-gray-800/50 p-3 rounded-md my-2">
            <p className="font-semibold text-green-400">Prompt Revised:</p>
            <p className="text-sm text-gray-300 mt-1 whitespace-pre-wrap font-mono">{data.revised_prompt}</p>
          </div>
        );
      
      case 'self_correction_error':
         return (
          <div key={index} className="text-sm text-red-400 font-bold">
            <p>! ERROR: {data.message}</p>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="bg-gray-900/70 border border-gray-700 rounded-lg p-4 mt-4">
      <h4 className="font-bold text-md text-cyan-300 mb-2">Self-Correction Log</h4>
      <div className="space-y-3 font-mono text-xs">
        {log.map(renderLogEntry)}
      </div>
    </div>
  );
};

export default SelfCorrectionLog; 