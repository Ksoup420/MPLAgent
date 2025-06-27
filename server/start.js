#!/usr/bin/env node
/**
 * MPLA Production Server Entry Point
 * Node.js wrapper for Python FastAPI backend to meet Endgame deployment requirements
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const PORT = process.env.PORT || 8080;
const PYTHON_PATH = process.env.PYTHON_PATH || 'python3';

console.log('🚀 Starting MPLA Meta-Prompt Learning Agent...');
console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
console.log(`🌐 Port: ${PORT}`);

// Ensure data directory exists
const dataDir = path.join(__dirname, '..', 'data');
if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
    console.log('📁 Created data directory');
}

// Ensure logs directory exists
const logsDir = path.join(__dirname, '..', 'logs');
if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
    console.log('📝 Created logs directory');
}

// Change to the app root directory
process.chdir(path.join(__dirname, '..'));

// Start the Python FastAPI server
const uvicornArgs = [
    '-m', 'uvicorn',
    'server.app.main:app',
    '--host', '0.0.0.0',
    '--port', PORT.toString(),
    '--log-level', 'info'
];

// Add reload in development
if (process.env.NODE_ENV !== 'production') {
    uvicornArgs.push('--reload');
}

console.log(`🐍 Starting Python server: ${PYTHON_PATH} ${uvicornArgs.join(' ')}`);

const pythonProcess = spawn(PYTHON_PATH, uvicornArgs, {
    stdio: 'inherit',
    env: {
        ...process.env,
        PYTHONPATH: path.join(__dirname, '..', 'mpla_project') + ':' + (process.env.PYTHONPATH || ''),
        MPLA_DATA_DIR: dataDir,
        MPLA_LOGS_DIR: logsDir
    }
});

pythonProcess.on('error', (error) => {
    console.error('❌ Failed to start Python server:', error);
    process.exit(1);
});

pythonProcess.on('close', (code) => {
    console.log(`🐍 Python server exited with code ${code}`);
    process.exit(code);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('🛑 Received SIGINT, shutting down gracefully...');
    pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
    console.log('🛑 Received SIGTERM, shutting down gracefully...');
    pythonProcess.kill('SIGTERM');
});

console.log('✅ MPLA server startup initiated successfully'); 