import { useState, useEffect } from 'react';
import { InfoIcon, Target, AlertTriangle, Sparkles } from 'lucide-react';

const StructuredPromptInput = ({ onPromptChange, isLoading = false, onRefine }) => {
    const [promptData, setPromptData] = useState({
        context: '',
        objective: '',
        constraints: '',
        format: 'professional', // professional, casual, technical
        length: 'medium' // short, medium, long
    });
    const [mode, setMode] = useState('structured'); // structured, unified
    const [generatedPrompt, setGeneratedPrompt] = useState('');

    // Generate unified prompt when structured data changes
    useEffect(() => {
        if (mode === 'structured') {
            const generated = generateUnifiedPrompt(promptData);
            setGeneratedPrompt(generated);
            onPromptChange(generated);
        }
    }, [promptData, mode, onPromptChange]);

    const generateUnifiedPrompt = (data) => {
        const { context, objective, constraints, format, length } = data;
        
        if (!objective.trim()) return '';
        
        let prompt = '';
        
        // Add context if provided
        if (context.trim()) {
            prompt += `**Context:**\n${context.trim()}\n\n`;
        }
        
        // Add main objective
        prompt += `**Objective:**\n${objective.trim()}\n\n`;
        
        // Add constraints if provided
        if (constraints.trim()) {
            prompt += `**Requirements & Constraints:**\n${constraints.trim()}\n\n`;
        }
        
        // Add format and length guidance
        const formatGuides = {
            professional: 'Please respond in a professional, formal tone.',
            casual: 'Please respond in a casual, conversational tone.',
            technical: 'Please provide a detailed, technical response with specific implementation details.'
        };
        
        const lengthGuides = {
            short: 'Keep the response concise and to the point.',
            medium: 'Provide a balanced response with adequate detail.',
            long: 'Provide a comprehensive, detailed response with examples and explanations.'
        };
        
        prompt += `**Style Guidelines:**\n- ${formatGuides[format]}\n- ${lengthGuides[length]}`;
        
        return prompt;
    };

    const updateField = (field, value) => {
        setPromptData(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const handleUnifiedPromptChange = (value) => {
        setGeneratedPrompt(value);
        onPromptChange(value);
    };

    const clearAll = () => {
        setPromptData({
            context: '',
            objective: '',
            constraints: '',
            format: 'professional',
            length: 'medium'
        });
        setGeneratedPrompt('');
        onPromptChange('');
    };

    const loadTemplate = (template) => {
        const templates = {
            analysis: {
                context: 'I need to analyze a complex dataset/document/situation',
                objective: 'Provide insights, patterns, and actionable recommendations',
                constraints: '- Focus on the most important findings\n- Include supporting evidence\n- Suggest next steps',
                format: 'professional',
                length: 'medium'
            },
            creative: {
                context: 'I\'m working on a creative project that needs innovative ideas',
                objective: 'Generate creative concepts, ideas, or solutions',
                constraints: '- Think outside the box\n- Consider multiple perspectives\n- Make it engaging and original',
                format: 'casual',
                length: 'medium'
            },
            technical: {
                context: 'I\'m developing a technical solution or implementing a system',
                objective: 'Provide technical guidance, code examples, or implementation details',
                constraints: '- Include specific technical details\n- Provide working examples\n- Consider best practices and potential issues',
                format: 'technical',
                length: 'long'
            },
            learning: {
                context: 'I\'m trying to learn or understand a new concept',
                objective: 'Explain the concept clearly with examples and practical applications',
                constraints: '- Use simple, clear language\n- Include real-world examples\n- Build from basic to advanced concepts',
                format: 'casual',
                length: 'medium'
            }
        };
        
        if (templates[template]) {
            setPromptData(templates[template]);
        }
    };

    const isPromptComplete = promptData.objective.trim().length > 0;

    return (
        <div className="bg-gray-800 p-4 rounded-lg shadow-inner">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Prompt Engineering Studio</h2>
                <div className="flex gap-2">
                    {/* Mode Toggle */}
                    <div className="flex bg-gray-700 rounded-md">
                        <button
                            onClick={() => setMode('structured')}
                            className={`px-3 py-1 text-sm rounded-l-md transition-colors ${
                                mode === 'structured' 
                                    ? 'bg-blue-600 text-white' 
                                    : 'text-gray-300 hover:text-white'
                            }`}
                        >
                            Structured
                        </button>
                        <button
                            onClick={() => setMode('unified')}
                            className={`px-3 py-1 text-sm rounded-r-md transition-colors ${
                                mode === 'unified' 
                                    ? 'bg-blue-600 text-white' 
                                    : 'text-gray-300 hover:text-white'
                            }`}
                        >
                            Unified
                        </button>
                    </div>
                </div>
            </div>

            {mode === 'structured' ? (
                <div className="space-y-4">
                    {/* Quick Templates */}
                    <div className="flex flex-wrap gap-2 mb-4">
                        <span className="text-sm text-gray-400">Quick templates:</span>
                        {['analysis', 'creative', 'technical', 'learning'].map(template => (
                            <button
                                key={template}
                                onClick={() => loadTemplate(template)}
                                className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-xs rounded-md capitalize transition-colors"
                            >
                                {template}
                            </button>
                        ))}
                        <button
                            onClick={clearAll}
                            className="px-2 py-1 bg-red-600 hover:bg-red-700 text-xs rounded-md transition-colors"
                        >
                            Clear All
                        </button>
                    </div>

                    {/* Context Field */}
                    <div>
                        <label className="flex items-center text-sm font-semibold text-gray-300 mb-2">
                            <InfoIcon className="w-4 h-4 mr-2" />
                            Context (Optional)
                            <span className="ml-2 text-xs text-gray-500">Background information, setting, or relevant details</span>
                        </label>
                        <textarea
                            value={promptData.context}
                            onChange={(e) => updateField('context', e.target.value)}
                            className="w-full h-20 bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
                            placeholder="Provide relevant background information, context, or setting for your request..."
                        />
                    </div>

                    {/* Objective Field */}
                    <div>
                        <label className="flex items-center text-sm font-semibold text-gray-300 mb-2">
                            <Target className="w-4 h-4 mr-2" />
                            Objective (Required)
                            <span className="ml-2 text-xs text-gray-500">What you want to achieve or accomplish</span>
                        </label>
                        <textarea
                            value={promptData.objective}
                            onChange={(e) => updateField('objective', e.target.value)}
                            className={`w-full h-24 bg-gray-700 border rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm ${
                                promptData.objective.trim() ? 'border-green-500' : 'border-red-500'
                            }`}
                            placeholder="Clearly state what you want to achieve, create, solve, or understand..."
                        />
                        {!promptData.objective.trim() && (
                            <p className="text-xs text-red-400 mt-1">Objective is required to generate a prompt</p>
                        )}
                    </div>

                    {/* Constraints Field */}
                    <div>
                        <label className="flex items-center text-sm font-semibold text-gray-300 mb-2">
                            <AlertTriangle className="w-4 h-4 mr-2" />
                            Requirements & Constraints (Optional)
                            <span className="ml-2 text-xs text-gray-500">Limitations, requirements, specific guidelines</span>
                        </label>
                        <textarea
                            value={promptData.constraints}
                            onChange={(e) => updateField('constraints', e.target.value)}
                            className="w-full h-20 bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
                            placeholder="List any specific requirements, limitations, or guidelines. For example:&#10;- Must be under 500 words&#10;- Include examples&#10;- Focus on practical applications"
                        />
                    </div>

                    {/* Style Options */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-semibold text-gray-300 mb-2">Response Style</label>
                            <select
                                value={promptData.format}
                                onChange={(e) => updateField('format', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
                            >
                                <option value="professional">Professional</option>
                                <option value="casual">Casual</option>
                                <option value="technical">Technical</option>
                            </select>
                        </div>
                        
                        <div>
                            <label className="block text-sm font-semibold text-gray-300 mb-2">Response Length</label>
                            <select
                                value={promptData.length}
                                onChange={(e) => updateField('length', e.target.value)}
                                className="w-full bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
                            >
                                <option value="short">Short & Concise</option>
                                <option value="medium">Medium Detail</option>
                                <option value="long">Comprehensive</option>
                            </select>
                        </div>
                    </div>

                    {/* Generated Prompt Preview */}
                    {generatedPrompt && (
                        <div className="bg-gray-900 p-3 rounded-md border border-gray-600">
                            <label className="flex items-center text-sm font-semibold text-green-300 mb-2">
                                <Sparkles className="w-4 h-4 mr-2" />
                                Generated Prompt Preview
                            </label>
                            <div className="text-sm text-gray-300 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                {generatedPrompt}
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                <div>
                    <label className="block text-sm font-semibold text-gray-300 mb-2">
                        Unified Prompt Input
                    </label>
                    <textarea
                        value={generatedPrompt}
                        onChange={(e) => handleUnifiedPromptChange(e.target.value)}
                        className="w-full h-40 bg-gray-700 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        placeholder="Enter your complete prompt here, or switch to Structured mode for guided input..."
                    />
                </div>
            )}

            {/* Run Refinement Button */}
            <button
                onClick={onRefine}
                disabled={isLoading || !isPromptComplete}
                className="w-full mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 text-white font-bold py-2 px-4 rounded-md transition-colors duration-300 flex items-center justify-center"
            >
                {isLoading ? (
                    <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Refining...
                    </>
                ) : (
                    <>
                        <Sparkles className="w-4 h-4 mr-2" />
                        Run Prompt Refinement
                    </>
                )}
            </button>

            {!isPromptComplete && (
                <p className="text-xs text-yellow-400 mt-2 text-center">
                    Please provide at least an objective to run refinement
                </p>
            )}
        </div>
    );
};

export default StructuredPromptInput; 