import { useState, useEffect } from 'react';
import { ChevronDownIcon, ChevronRightIcon, EyeIcon, BarChart3Icon, SearchIcon, FilterIcon, CalendarIcon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const KnowledgeBaseExplorer = () => {
    const [activeTab, setActiveTab] = useState('sessions');
    const [data, setData] = useState({});
    const [loading, setLoading] = useState({});
    const [error, setError] = useState(null);
    const [selectedSession, setSelectedSession] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [dateFilter, setDateFilter] = useState('all');
    const [expandedItems, setExpandedItems] = useState(new Set());

    // Use relative URL for production, absolute for development
    const API_BASE = import.meta.env.DEV ? 'http://localhost:8002' : '';

    const fetchData = async (queryType, filters = {}) => {
        setLoading(prev => ({ ...prev, [queryType]: true }));
        setError(null);
        
        try {
            const response = await fetch(`${API_BASE}/api/database/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query_type: queryType,
                    filters: filters
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            setData(prev => ({ ...prev, [queryType]: result.results }));
        } catch (e) {
            setError(e.message);
            console.error(`Failed to fetch ${queryType}:`, e);
        } finally {
            setLoading(prev => ({ ...prev, [queryType]: false }));
        }
    };

    useEffect(() => {
        fetchData(activeTab);
    }, [activeTab]);

    const toggleExpanded = (id) => {
        const newExpanded = new Set(expandedItems);
        if (newExpanded.has(id)) {
            newExpanded.delete(id);
        } else {
            newExpanded.add(id);
        }
        setExpandedItems(newExpanded);
    };

    const formatDate = (dateString) => {
        try {
            return new Date(dateString).toLocaleString();
        } catch {
            return dateString;
        }
    };

    const filteredData = (dataArray) => {
        if (!dataArray) return [];
        
        let filtered = dataArray;
        
        // Search filter
        if (searchQuery) {
            filtered = filtered.filter(item => 
                JSON.stringify(item).toLowerCase().includes(searchQuery.toLowerCase())
            );
        }
        
        // Date filter
        if (dateFilter !== 'all') {
            const now = new Date();
            const cutoff = new Date();
            
            switch (dateFilter) {
                case 'today':
                    cutoff.setHours(0, 0, 0, 0);
                    break;
                case 'week':
                    cutoff.setDate(now.getDate() - 7);
                    break;
                case 'month':
                    cutoff.setMonth(now.getMonth() - 1);
                    break;
            }
            
            filtered = filtered.filter(item => {
                const itemDate = new Date(item.created_at || item.updated_at);
                return itemDate >= cutoff;
            });
        }
        
        return filtered;
    };

    const SessionsView = () => {
        const sessions = filteredData(data.sessions);
        
        return (
            <div className="space-y-4">
                <div className="text-sm text-gray-400">
                    Found {sessions.length} session{sessions.length !== 1 ? 's' : ''}
                </div>
                
                {sessions.map((session, index) => (
                    <div key={session.id || index} className="bg-gray-700/50 p-4 rounded-lg border border-gray-600">
                        <div className="flex justify-between items-start">
                            <div className="flex-1">
                                <h3 className="font-semibold text-blue-300">
                                    Session #{session.id} 
                                    {session.user_id && <span className="text-gray-400 ml-2">({session.user_id})</span>}
                                </h3>
                                <p className="text-gray-300 mt-2 text-sm line-clamp-3">{session.text}</p>
                                <div className="text-xs text-gray-500 mt-2">
                                    Created: {formatDate(session.created_at)}
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedSession(session)}
                                className="ml-4 p-2 bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
                                title="View Details"
                            >
                                <EyeIcon className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                ))}
                
                {sessions.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                        No sessions found matching your criteria
                    </div>
                )}
            </div>
        );
    };

    const PromptsView = () => {
        const prompts = filteredData(data.prompts);
        
        return (
            <div className="space-y-4">
                <div className="text-sm text-gray-400">
                    Found {prompts.length} prompt version{prompts.length !== 1 ? 's' : ''}
                </div>
                
                {prompts.map((prompt, index) => (
                    <div key={prompt.id || index} className="bg-gray-700/50 p-4 rounded-lg border border-gray-600">
                        <div className="flex justify-between items-start">
                            <div className="flex-1">
                                <h3 className="font-semibold text-green-300">
                                    Prompt v{prompt.version_number}
                                    <span className="text-gray-400 ml-2">
                                        (Session #{prompt.original_prompt_id})
                                    </span>
                                </h3>
                                
                                <button
                                    onClick={() => toggleExpanded(`prompt-${prompt.id}`)}
                                    className="flex items-center mt-2 text-sm text-gray-400 hover:text-white"
                                >
                                    {expandedItems.has(`prompt-${prompt.id}`) ? 
                                        <ChevronDownIcon className="w-4 h-4 mr-1" /> : 
                                        <ChevronRightIcon className="w-4 h-4 mr-1" />
                                    }
                                    {expandedItems.has(`prompt-${prompt.id}`) ? 'Hide' : 'Show'} prompt text
                                </button>
                                
                                {expandedItems.has(`prompt-${prompt.id}`) && (
                                    <div className="mt-3 p-3 bg-gray-900 rounded-md">
                                        <p className="text-gray-200 whitespace-pre-wrap text-sm">
                                            {prompt.prompt_text}
                                        </p>
                                        {prompt.enhancement_rationale && (
                                            <div className="mt-3 pt-3 border-t border-gray-600">
                                                <h4 className="text-xs font-semibold text-gray-400 mb-1">Enhancement Rationale:</h4>
                                                <p className="text-gray-300 text-xs italic">{prompt.enhancement_rationale}</p>
                                            </div>
                                        )}
                                    </div>
                                )}
                                
                                <div className="text-xs text-gray-500 mt-2">
                                    Created: {formatDate(prompt.created_at)}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
                
                {prompts.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                        No prompts found matching your criteria
                    </div>
                )}
            </div>
        );
    };

    const EvaluationsView = () => {
        const evaluations = filteredData(data.evaluations);
        
        return (
            <div className="space-y-4">
                <div className="text-sm text-gray-400">
                    Found {evaluations.length} evaluation{evaluations.length !== 1 ? 's' : ''}
                </div>
                
                {evaluations.map((evaluation, index) => (
                    <div key={evaluation.id || index} className="bg-gray-700/50 p-4 rounded-lg border border-gray-600">
                        <div className="flex justify-between items-start">
                            <div className="flex-1">
                                <h3 className="font-semibold text-yellow-300">
                                    Evaluation #{evaluation.id}
                                    {evaluation.overall_score && (
                                        <span className="ml-2 px-2 py-1 bg-blue-600 text-white text-xs rounded">
                                            Score: {evaluation.overall_score.toFixed(2)}
                                        </span>
                                    )}
                                </h3>
                                
                                {evaluation.metric_scores && (
                                    <div className="mt-2">
                                        <button
                                            onClick={() => toggleExpanded(`eval-${evaluation.id}`)}
                                            className="flex items-center text-sm text-gray-400 hover:text-white"
                                        >
                                            {expandedItems.has(`eval-${evaluation.id}`) ? 
                                                <ChevronDownIcon className="w-4 h-4 mr-1" /> : 
                                                <ChevronRightIcon className="w-4 h-4 mr-1" />
                                            }
                                            {expandedItems.has(`eval-${evaluation.id}`) ? 'Hide' : 'Show'} metrics
                                        </button>
                                        
                                        {expandedItems.has(`eval-${evaluation.id}`) && (
                                            <div className="mt-3 p-3 bg-gray-900 rounded-md">
                                                <pre className="text-xs text-green-300 whitespace-pre-wrap">
                                                    {JSON.stringify(evaluation.metric_scores, null, 2)}
                                                </pre>
                                            </div>
                                        )}
                                    </div>
                                )}
                                
                                {evaluation.qualitative_feedback && (
                                    <div className="mt-2">
                                        <h4 className="text-xs font-semibold text-gray-400">Feedback:</h4>
                                        <p className="text-gray-300 text-sm mt-1">{evaluation.qualitative_feedback}</p>
                                    </div>
                                )}
                                
                                <div className="text-xs text-gray-500 mt-2">
                                    Created: {formatDate(evaluation.created_at)}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
                
                {evaluations.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                        No evaluations found matching your criteria
                    </div>
                )}
            </div>
        );
    };

    const PerformanceView = () => {
        const performance = data.performance;
        
        if (!performance) {
            return (
                <div className="text-center py-8 text-gray-400">
                    Loading performance data...
                </div>
            );
        }
        
        return (
            <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-blue-600/20 border border-blue-500 p-4 rounded-lg">
                        <h3 className="font-semibold text-blue-300">Total Evaluations</h3>
                        <p className="text-2xl font-bold text-blue-200 mt-2">
                            {performance.total_evaluations || 0}
                        </p>
                    </div>
                    
                    <div className="bg-green-600/20 border border-green-500 p-4 rounded-lg">
                        <h3 className="font-semibold text-green-300">Average Score</h3>
                        <p className="text-2xl font-bold text-green-200 mt-2">
                            {performance.average_score ? performance.average_score.toFixed(2) : 'N/A'}
                        </p>
                    </div>
                    
                    <div className="bg-purple-600/20 border border-purple-500 p-4 rounded-lg">
                        <h3 className="font-semibold text-purple-300">Recent Activity</h3>
                        <p className="text-2xl font-bold text-purple-200 mt-2">
                            {performance.recent_evaluations?.length || 0}
                        </p>
                    </div>
                </div>
                
                {/* Recent Evaluations */}
                {performance.recent_evaluations && performance.recent_evaluations.length > 0 && (
                    <div className="bg-gray-700/50 p-4 rounded-lg border border-gray-600">
                        <h3 className="font-semibold text-gray-200 mb-4">Recent Evaluations</h3>
                        <div className="space-y-3">
                            {performance.recent_evaluations.map((evaluation, index) => (
                                <div key={evaluation.id || index} className="flex justify-between items-center py-2 border-b border-gray-600 last:border-b-0">
                                    <div>
                                        <span className="text-sm text-gray-300">Evaluation #{evaluation.id}</span>
                                        {evaluation.overall_score && (
                                            <span className="ml-2 px-2 py-1 bg-blue-600 text-white text-xs rounded">
                                                {evaluation.overall_score.toFixed(2)}
                                            </span>
                                        )}
                                    </div>
                                    <span className="text-xs text-gray-500">
                                        {formatDate(evaluation.created_at)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    };

    const SessionDetailModal = ({ session, onClose }) => {
        if (!session) return null;
        
        return (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
                    <div className="p-4 border-b border-gray-600 flex justify-between items-center">
                        <h2 className="text-xl font-bold text-blue-300">Session #{session.id} Details</h2>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-white text-xl"
                        >
                            ×
                        </button>
                    </div>
                    
                    <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
                        <div className="space-y-4">
                            <div>
                                <h3 className="font-semibold text-gray-300 mb-2">Original Prompt</h3>
                                <div className="bg-gray-900 p-3 rounded-md">
                                    <p className="text-gray-200 whitespace-pre-wrap">{session.text}</p>
                                </div>
                            </div>
                            
                            {session.user_id && (
                                <div>
                                    <h3 className="font-semibold text-gray-300 mb-2">User ID</h3>
                                    <p className="text-gray-400">{session.user_id}</p>
                                </div>
                            )}
                            
                            <div>
                                <h3 className="font-semibold text-gray-300 mb-2">Timeline</h3>
                                <div className="text-sm text-gray-400">
                                    <p>Created: {formatDate(session.created_at)}</p>
                                    <p>Updated: {formatDate(session.updated_at)}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    const tabs = [
        { id: 'sessions', label: 'Sessions', icon: CalendarIcon },
        { id: 'prompts', label: 'Prompts', icon: SearchIcon },
        { id: 'evaluations', label: 'Evaluations', icon: BarChart3Icon },
        { id: 'performance', label: 'Performance', icon: BarChart3Icon },
    ];

    return (
        <div className="bg-gray-800/50 p-4 rounded-lg shadow-inner">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Knowledge Base Explorer</h2>
                <button
                    onClick={() => fetchData(activeTab)}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded-md text-sm"
                    disabled={loading[activeTab]}
                >
                    {loading[activeTab] ? 'Refreshing...' : 'Refresh'}
                </button>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-gray-600 mb-4 overflow-x-auto">
                {tabs.map(tab => {
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center px-4 py-2 text-sm font-medium whitespace-nowrap ${
                                activeTab === tab.id 
                                    ? 'border-b-2 border-blue-500 text-blue-400' 
                                    : 'text-gray-400 hover:text-white'
                            }`}
                        >
                            <Icon className="w-4 h-4 mr-2" />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Filters */}
            {activeTab !== 'performance' && (
                <div className="flex flex-col sm:flex-row gap-4 mb-4">
                    <div className="flex-1">
                        <div className="relative">
                            <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                            <input
                                type="text"
                                placeholder="Search..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
                            />
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                        <FilterIcon className="w-4 h-4 text-gray-400" />
                        <select
                            value={dateFilter}
                            onChange={(e) => setDateFilter(e.target.value)}
                            className="bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        >
                            <option value="all">All Time</option>
                            <option value="today">Today</option>
                            <option value="week">Past Week</option>
                            <option value="month">Past Month</option>
                        </select>
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="min-h-[400px]">
                {error && (
                    <div className="text-red-400 bg-red-900/50 p-3 rounded-md mb-4">
                        Error: {error}
                    </div>
                )}

                {loading[activeTab] && (
                    <div className="text-center py-8 text-gray-400">
                        Loading {activeTab}...
                    </div>
                )}

                {!loading[activeTab] && !error && (
                    <>
                        {activeTab === 'sessions' && <SessionsView />}
                        {activeTab === 'prompts' && <PromptsView />}
                        {activeTab === 'evaluations' && <EvaluationsView />}
                        {activeTab === 'performance' && <PerformanceView />}
                    </>
                )}
            </div>

            {/* Session Detail Modal */}
            {selectedSession && (
                <SessionDetailModal
                    session={selectedSession}
                    onClose={() => setSelectedSession(null)}
                />
            )}
        </div>
    );
};

export default KnowledgeBaseExplorer; 