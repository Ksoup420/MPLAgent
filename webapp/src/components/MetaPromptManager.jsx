import { useState, useEffect } from 'react';
import toast, { Toaster } from 'react-hot-toast';

const MetaPromptManager = () => {
    const [prompts, setPrompts] = useState([]);
    const [activeTab, setActiveTab] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [promptContent, setPromptContent] = useState({});
    
    // Use relative URL for production, absolute for development
    const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : '';

    const fetchPrompts = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_BASE}/api/meta-prompts`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setPrompts(data);
            if (data.length > 0) {
                setActiveTab(data[0].name);
                const initialContent = data.reduce((acc, p) => ({ ...acc, [p.name]: p.template }), {});
                setPromptContent(initialContent);
            }
        } catch (e) {
            setError(e.message);
            toast.error(`Failed to fetch prompts: ${e.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchPrompts();
    }, []);

    const handleSave = async (name) => {
        const content = promptContent[name];
        toast.promise(
            fetch(`${API_BASE}/api/meta-prompts/${name}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template: content }),
            }).then(response => {
                if (!response.ok) {
                    throw new Error('Failed to save prompt.');
                }
                return response.json();
            }),
            {
                loading: `Saving ${name}...`,
                success: (data) => {
                    // Update local state after successful save
                    setPrompts(prev => prev.map(p => p.name === name ? data : p));
                    setPromptContent(prev => ({...prev, [name]: data.template}));
                    return `${name} saved successfully!`;
                },
                error: `Failed to save ${name}.`,
            }
        );
    };
    
    const handleSetActive = async (name) => {
        toast.promise(
             fetch(`${API_BASE}/api/meta-prompts/${name}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: true }),
            }).then(response => {
                if (!response.ok) {
                    throw new Error('Failed to activate prompt.');
                }
                 // Refetch all prompts to update active status everywhere
                return fetchPrompts();
            }),
            {
                loading: `Activating ${name}...`,
                success: `${name} activated successfully!`,
                error: `Failed to activate ${name}.`,
            }
        );
    };


    if (isLoading) return <div className="text-center p-4">Loading prompts...</div>;
    if (error) return <div className="text-red-400 p-4">Error: {error}</div>;
    if (!prompts || prompts.length === 0) return <div className="text-center p-4">No meta-prompts available.</div>;

    return (
        <div className="bg-gray-800/50 p-4 rounded-lg shadow-inner mt-4">
            <Toaster position="top-right" />
            <h2 className="text-xl font-bold mb-4">Meta-Prompt Configuration</h2>
            <div className="flex border-b border-gray-600 overflow-x-auto">
                {prompts.map(p => (
                    <button
                        key={p.name}
                        onClick={() => setActiveTab(p.name)}
                        className={`px-4 py-2 text-sm font-medium ${activeTab === p.name ? 'border-b-2 border-blue-500 text-blue-400' : 'text-gray-400 hover:text-white'}`}
                    >
                        {p.name} {p.is_active && <span className="text-green-400">(Active)</span>}
                    </button>
                ))}
            </div>
            <div className="mt-4">
                {prompts && prompts.map(p => (
                    <div key={p.name} className={activeTab === p.name ? 'block' : 'hidden'}>
                        <textarea
                            value={promptContent[p.name] || ''}
                            onChange={(e) => setPromptContent({...promptContent, [p.name]: e.target.value})}
                            className="w-full h-96 bg-gray-900 border border-gray-600 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none font-mono text-sm"
                            placeholder={`Enter meta-prompt for ${p.name}...`}
                        />
                        <div className="flex justify-end gap-4 mt-2">
                            <button 
                                onClick={() => handleSave(p.name)}
                                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md text-sm"
                            >
                                Save Changes
                            </button>
                             <button 
                                onClick={() => handleSetActive(p.name)}
                                disabled={p.is_active}
                                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-500 text-white font-bold py-2 px-4 rounded-md text-sm"
                            >
                                {p.is_active ? 'Active' : 'Set Active'}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default MetaPromptManager; 