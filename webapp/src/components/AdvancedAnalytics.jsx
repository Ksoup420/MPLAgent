import { useState, useEffect } from 'react';
import { BarChart3Icon, TrendingUpIcon, TrendingDownIcon, Target, Clock, Zap, Award, AlertCircle, CheckCircle, ArrowUpIcon, ArrowDownIcon } from 'lucide-react';

const AdvancedAnalytics = () => {
    const [analyticsData, setAnalyticsData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [timeRange, setTimeRange] = useState('7d'); // 1d, 7d, 30d, all
    const [activeMetric, setActiveMetric] = useState('overview');

    // Use relative URL for production, absolute for development
    const API_BASE = import.meta.env.DEV ? 'http://localhost:8002' : '';

    const fetchAnalytics = async () => {
        setLoading(true);
        setError(null);
        
        try {
            // Fetch multiple data sources for comprehensive analytics
            const [sessionsResponse, promptsResponse, evaluationsResponse, performanceResponse] = await Promise.all([
                fetch(`${API_BASE}/api/database/query`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query_type: 'sessions', filters: { timeRange } })
                }),
                fetch(`${API_BASE}/api/database/query`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query_type: 'prompts', filters: { timeRange } })
                }),
                fetch(`${API_BASE}/api/database/query`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query_type: 'evaluations', filters: { timeRange } })
                }),
                fetch(`${API_BASE}/api/database/query`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query_type: 'performance', filters: { timeRange } })
                })
            ]);

            const sessions = await sessionsResponse.json();
            const prompts = await promptsResponse.json();
            const evaluations = await evaluationsResponse.json();
            const performance = await performanceResponse.json();

            // Process and combine data for advanced analytics
            const processedData = processAnalyticsData(sessions.results, prompts.results, evaluations.results, performance.results);
            setAnalyticsData(processedData);
        } catch (e) {
            setError(e.message);
            console.error('Failed to fetch analytics:', e);
        } finally {
            setLoading(false);
        }
    };

    const processAnalyticsData = (sessions, prompts, evaluations, performanceData) => {
        // Calculate comprehensive metrics
        const totalSessions = sessions?.length || 0;
        const totalPrompts = prompts?.length || 0;
        const totalEvaluations = evaluations?.length || 0;
        
        // Calculate success rates
        const successfulEvaluations = evaluations?.filter(e => e.overall_score && e.overall_score > 0.7) || [];
        const successRate = totalEvaluations > 0 ? (successfulEvaluations.length / totalEvaluations * 100) : 0;
        
        // Calculate average iteration count per session
        const sessionPromptCounts = sessions?.map(session => {
            const sessionPrompts = prompts?.filter(p => p.original_prompt_id === session.id) || [];
            return sessionPrompts.length;
        }) || [];
        const avgIterations = sessionPromptCounts.length > 0 ? 
            sessionPromptCounts.reduce((a, b) => a + b, 0) / sessionPromptCounts.length : 0;

        // Calculate improvement trends
        const scoreTrends = evaluations?.map(e => ({
            score: e.overall_score || 0,
            date: e.created_at,
            id: e.id
        })).sort((a, b) => new Date(a.date) - new Date(b.date)) || [];

        // Calculate time-based metrics
        const now = new Date();
        const timeFilters = {
            '1d': new Date(now - 24 * 60 * 60 * 1000),
            '7d': new Date(now - 7 * 24 * 60 * 60 * 1000),
            '30d': new Date(now - 30 * 24 * 60 * 60 * 1000)
        };

        const recentSessions = sessions?.filter(s => 
            new Date(s.created_at) > (timeFilters[timeRange] || new Date(0))
        ) || [];

        // Performance insights
        const insights = generateInsights(sessions, prompts, evaluations, successRate, avgIterations);

        return {
            overview: {
                totalSessions,
                totalPrompts,
                totalEvaluations,
                successRate,
                avgIterations,
                avgScore: performanceData?.average_score || 0
            },
            trends: {
                scoreTrends,
                recentActivity: recentSessions.length,
                timeRange
            },
            insights,
            detailed: {
                sessions,
                prompts,
                evaluations,
                performanceData
            }
        };
    };

    const generateInsights = (sessions, prompts, evaluations, successRate, avgIterations) => {
        const insights = [];

        // Success rate insights
        if (successRate > 80) {
            insights.push({
                type: 'success',
                title: 'Excellent Performance',
                description: `${successRate.toFixed(1)}% success rate indicates high-quality prompt refinements.`,
                action: 'Continue current approach and consider documenting best practices.'
            });
        } else if (successRate > 60) {
            insights.push({
                type: 'warning',
                title: 'Good Performance',
                description: `${successRate.toFixed(1)}% success rate shows room for improvement.`,
                action: 'Review failed iterations to identify common issues.'
            });
        } else {
            insights.push({
                type: 'error',
                title: 'Performance Needs Attention',
                description: `${successRate.toFixed(1)}% success rate suggests refinement strategy needs adjustment.`,
                action: 'Consider revising meta-prompts or evaluation criteria.'
            });
        }

        // Iteration efficiency insights
        if (avgIterations < 2) {
            insights.push({
                type: 'info',
                title: 'Low Iteration Count',
                description: `Average ${avgIterations.toFixed(1)} iterations suggests prompts are refined quickly.`,
                action: 'Consider if more iterations could improve quality further.'
            });
        } else if (avgIterations > 4) {
            insights.push({
                type: 'warning',
                title: 'High Iteration Count',
                description: `Average ${avgIterations.toFixed(1)} iterations indicates refinement takes many steps.`,
                action: 'Review meta-prompts for clarity and effectiveness.'
            });
        }

        // Activity insights
        const recentActivity = evaluations?.filter(e => {
            const evalDate = new Date(e.created_at);
            const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
            return evalDate > weekAgo;
        }) || [];

        if (recentActivity.length === 0) {
            insights.push({
                type: 'info',
                title: 'Low Recent Activity',
                description: 'No evaluations in the past week.',
                action: 'Consider running more refinement sessions to gather data.'
            });
        }

        return insights;
    };

    useEffect(() => {
        fetchAnalytics();
    }, [timeRange]);

    const MetricCard = ({ title, value, change, icon: Icon, color = 'blue' }) => {
        const colorClasses = {
            blue: 'bg-blue-600/20 border-blue-500 text-blue-300',
            green: 'bg-green-600/20 border-green-500 text-green-300',
            yellow: 'bg-yellow-600/20 border-yellow-500 text-yellow-300',
            red: 'bg-red-600/20 border-red-500 text-red-300',
            purple: 'bg-purple-600/20 border-purple-500 text-purple-300'
        };

        return (
            <div className={`border p-4 rounded-lg ${colorClasses[color]}`}>
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm font-medium opacity-80">{title}</p>
                        <p className="text-2xl font-bold mt-1">{value}</p>
                        {change !== undefined && (
                            <div className="flex items-center mt-1">
                                {change > 0 ? (
                                    <ArrowUpIcon className="w-3 h-3 mr-1 text-green-400" />
                                ) : change < 0 ? (
                                    <ArrowDownIcon className="w-3 h-3 mr-1 text-red-400" />
                                ) : null}
                                <span className={`text-xs ${change > 0 ? 'text-green-400' : change < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                                    {change > 0 ? '+' : ''}{change}%
                                </span>
                            </div>
                        )}
                    </div>
                    <Icon className="w-8 h-8 opacity-60" />
                </div>
            </div>
        );
    };

    const InsightCard = ({ insight }) => {
        const typeStyles = {
            success: 'bg-green-900/30 border-green-600 text-green-200',
            warning: 'bg-yellow-900/30 border-yellow-600 text-yellow-200',
            error: 'bg-red-900/30 border-red-600 text-red-200',
            info: 'bg-blue-900/30 border-blue-600 text-blue-200'
        };

        const typeIcons = {
            success: CheckCircle,
            warning: AlertCircle,
            error: AlertCircle,
            info: Target
        };

        const Icon = typeIcons[insight.type];

        return (
            <div className={`border p-4 rounded-lg ${typeStyles[insight.type]}`}>
                <div className="flex items-start">
                    <Icon className="w-5 h-5 mr-3 mt-0.5 flex-shrink-0" />
                    <div>
                        <h4 className="font-semibold mb-1">{insight.title}</h4>
                        <p className="text-sm opacity-90 mb-2">{insight.description}</p>
                        <p className="text-xs opacity-75 font-medium">
                            💡 {insight.action}
                        </p>
                    </div>
                </div>
            </div>
        );
    };

    if (loading) {
        return (
            <div className="bg-gray-800/50 p-4 rounded-lg shadow-inner">
                <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-gray-400">Loading advanced analytics...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-gray-800/50 p-4 rounded-lg shadow-inner">
                <div className="text-red-400 bg-red-900/50 p-3 rounded-md">
                    Error loading analytics: {error}
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gray-800/50 p-4 rounded-lg shadow-inner">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold flex items-center">
                    <BarChart3Icon className="w-6 h-6 mr-2" />
                    Advanced Analytics
                </h2>
                
                <div className="flex gap-4">
                    {/* Time Range Selector */}
                    <select
                        value={timeRange}
                        onChange={(e) => setTimeRange(e.target.value)}
                        className="bg-gray-700 border border-gray-600 rounded-md px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    >
                        <option value="1d">Last 24 Hours</option>
                        <option value="7d">Last 7 Days</option>
                        <option value="30d">Last 30 Days</option>
                        <option value="all">All Time</option>
                    </select>
                    
                    <button
                        onClick={fetchAnalytics}
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded-md text-sm"
                    >
                        Refresh
                    </button>
                </div>
            </div>

            {analyticsData && (
                <div className="space-y-6">
                    {/* Key Metrics Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <MetricCard
                            title="Success Rate"
                            value={`${analyticsData.overview.successRate.toFixed(1)}%`}
                            icon={Award}
                            color="green"
                        />
                        <MetricCard
                            title="Avg Iterations"
                            value={analyticsData.overview.avgIterations.toFixed(1)}
                            icon={Zap}
                            color="blue"
                        />
                        <MetricCard
                            title="Total Sessions"
                            value={analyticsData.overview.totalSessions}
                            icon={Target}
                            color="purple"
                        />
                        <MetricCard
                            title="Avg Score"
                            value={analyticsData.overview.avgScore.toFixed(2)}
                            icon={TrendingUpIcon}
                            color="yellow"
                        />
                    </div>

                    {/* Insights Section */}
                    {analyticsData.insights && analyticsData.insights.length > 0 && (
                        <div>
                            <h3 className="text-lg font-semibold mb-4 flex items-center">
                                <Target className="w-5 h-5 mr-2" />
                                Performance Insights
                            </h3>
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                {analyticsData.insights.map((insight, index) => (
                                    <InsightCard key={index} insight={insight} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Trends Visualization */}
                    {analyticsData.trends.scoreTrends.length > 0 && (
                        <div className="bg-gray-700/50 p-4 rounded-lg">
                            <h3 className="text-lg font-semibold mb-4 flex items-center">
                                <TrendingUpIcon className="w-5 h-5 mr-2" />
                                Score Trends
                            </h3>
                            <div className="space-y-2">
                                {analyticsData.trends.scoreTrends.slice(-10).map((trend, index) => (
                                    <div key={trend.id || index} className="flex items-center justify-between py-2 border-b border-gray-600 last:border-b-0">
                                        <span className="text-sm text-gray-300">
                                            Evaluation #{trend.id}
                                        </span>
                                        <div className="flex items-center">
                                            <div className={`px-2 py-1 rounded text-xs ${
                                                trend.score > 0.8 ? 'bg-green-600 text-white' :
                                                trend.score > 0.6 ? 'bg-yellow-600 text-white' :
                                                'bg-red-600 text-white'
                                            }`}>
                                                {(trend.score * 100).toFixed(0)}%
                                            </div>
                                            <span className="text-xs text-gray-500 ml-2">
                                                {new Date(trend.date).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Activity Summary */}
                    <div className="bg-gray-700/50 p-4 rounded-lg">
                        <h3 className="text-lg font-semibold mb-4 flex items-center">
                            <Clock className="w-5 h-5 mr-2" />
                            Activity Summary
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                            <div>
                                <p className="text-2xl font-bold text-blue-300">{analyticsData.overview.totalSessions}</p>
                                <p className="text-sm text-gray-400">Total Sessions</p>
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-green-300">{analyticsData.overview.totalPrompts}</p>
                                <p className="text-sm text-gray-400">Prompts Generated</p>
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-yellow-300">{analyticsData.overview.totalEvaluations}</p>
                                <p className="text-sm text-gray-400">Evaluations Completed</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {!analyticsData && !loading && (
                <div className="text-center py-8 text-gray-400">
                    No analytics data available. Run some refinement sessions to generate insights.
                </div>
            )}
        </div>
    );
};

export default AdvancedAnalytics; 