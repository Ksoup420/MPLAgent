import React from 'react';

const SystemStatusLog = ({ statusLog }) => {
  if (!statusLog || statusLog.length === 0) {
    return null;
  }

  const renderDiagnosis = (data) => {
    if (!data) return <p className="text-gray-400">No diagnosis details provided.</p>;
    return (
      <div className="mt-2 text-sm bg-gray-700 p-3 rounded-md">
        <p><strong className="text-yellow-400">Root Cause:</strong> {data.root_cause_analysis || 'N/A'}</p>
        <p><strong className="text-yellow-400">Proposed Strategy:</strong> <span className="font-mono bg-gray-800 px-2 py-1 rounded">{data.recovery_strategy || 'N/A'}</span></p>
        <p><strong className="text-yellow-400">Justification:</strong> {data.justification || 'N/A'}</p>
      </div>
    );
  };

  return (
    <div className="my-4 bg-gray-800/50 border border-yellow-600/30 p-4 rounded-lg shadow-inner">
      <h3 className="text-lg font-bold text-yellow-300 mb-2">System Status</h3>
      <div className="space-y-3 max-h-60 overflow-y-auto p-2">
        {statusLog.map((log, index) => (
          <div key={index} className="text-sm font-mono animate-fade-in">
            {log.event === 'system_error' && (
              <div className="p-3 bg-red-900/50 rounded-lg">
                <p className="font-bold text-red-300">! Component Error: {log.data.component}</p>
                <p className="mt-1 text-red-400">{log.data.error}</p>
              </div>
            )}
            {log.event === 'system_diagnosis' && (
              <div className="p-3 bg-blue-900/50 rounded-lg">
                  <p className="font-bold text-blue-300">~ System Diagnosis</p>
                  {renderDiagnosis(log.data)}
              </div>
            )}
            {log.event === 'message' && log.data.startsWith('Skipping') && (
                 <p className="text-yellow-400 italic">~ {log.data}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SystemStatusLog; 