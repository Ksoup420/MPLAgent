#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { Octokit } from '@octokit/rest';
import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class MPLAMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'mpla-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.octokit = null;
    this.setupEventHandlers();
  }

  setupEventHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'mpla_run_refinement',
            description: 'Execute MPLA prompt refinement cycle with specified parameters',
            inputSchema: {
              type: 'object',
              properties: {
                prompt: {
                  type: 'string',
                  description: 'Initial prompt to refine',
                },
                settings: {
                  type: 'object',
                  description: 'MPLA configuration settings',
                  properties: {
                    max_iterations: { type: 'number', default: 3 },
                    model_temperature: { type: 'number', default: 0.7 },
                    evaluation_mode: { type: 'string', default: 'basic' },
                    providers: {
                      type: 'object',
                      properties: {
                        orchestrator: { type: 'string', default: 'gemini' },
                        enhancer: { type: 'string', default: 'architect' },
                      },
                    },
                  },
                },
              },
              required: ['prompt'],
            },
          },
          {
            name: 'mpla_get_session_report',
            description: 'Get detailed report of MPLA refinement session',
            inputSchema: {
              type: 'object',
              properties: {
                session_id: {
                  type: 'string',
                  description: 'Session ID to retrieve report for',
                },
              },
              required: ['session_id'],
            },
          },
          {
            name: 'mpla_database_query',
            description: 'Query MPLA knowledge base for historical data and analytics',
            inputSchema: {
              type: 'object',
              properties: {
                query_type: {
                  type: 'string',
                  enum: ['sessions', 'prompts', 'evaluations', 'performance'],
                  description: 'Type of data to query',
                },
                filters: {
                  type: 'object',
                  description: 'Query filters (dates, performance thresholds, etc.)',
                },
              },
              required: ['query_type'],
            },
          },
          {
            name: 'github_create_issue',
            description: 'Create a GitHub issue with MPLA analysis results',
            inputSchema: {
              type: 'object',
              properties: {
                owner: { type: 'string', description: 'Repository owner' },
                repo: { type: 'string', description: 'Repository name' },
                title: { type: 'string', description: 'Issue title' },
                body: { type: 'string', description: 'Issue body with MPLA findings' },
                labels: {
                  type: 'array',
                  items: { type: 'string' },
                  description: 'Issue labels',
                },
              },
              required: ['owner', 'repo', 'title', 'body'],
            },
          },
          {
            name: 'github_get_repository',
            description: 'Get repository information and analysis for prompt engineering',
            inputSchema: {
              type: 'object',
              properties: {
                owner: { type: 'string', description: 'Repository owner' },
                repo: { type: 'string', description: 'Repository name' },
              },
              required: ['owner', 'repo'],
            },
          },
          {
            name: 'github_search_code',
            description: 'Search code across GitHub repositories for prompt engineering patterns',
            inputSchema: {
              type: 'object',
              properties: {
                query: { type: 'string', description: 'Search query' },
                sort: { type: 'string', enum: ['indexed', 'updated'], default: 'indexed' },
                order: { type: 'string', enum: ['asc', 'desc'], default: 'desc' },
              },
              required: ['query'],
            },
          },
          {
            name: 'mpla_health_check',
            description: 'Check MPLA system health and component status',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'mpla_run_refinement':
            return await this.runMPLARefinement(args);
          case 'mpla_get_session_report':
            return await this.getMPLASessionReport(args);
          case 'mpla_database_query':
            return await this.queryMPLADatabase(args);
          case 'github_create_issue':
            return await this.createGitHubIssue(args);
          case 'github_get_repository':
            return await this.getGitHubRepository(args);
          case 'github_search_code':
            return await this.searchGitHubCode(args);
          case 'mpla_health_check':
            return await this.checkMPLAHealth(args);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
      } catch (error) {
        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${error.message}`
        );
      }
    });
  }

  async initializeGitHub() {
    if (!this.octokit) {
      const token = process.env.GITHUB_TOKEN;
      if (!token) {
        throw new Error('GITHUB_TOKEN environment variable not set');
      }
      this.octokit = new Octokit({ auth: token });
    }
    return this.octokit;
  }

  async runMPLARefinement(args) {
    const { prompt, settings = {} } = args;
    
    try {
      // Call MPLA API endpoint
      const response = await fetch('http://localhost:8080/api/refine', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          initial_prompt: prompt,
          ...settings,
        }),
      });

      if (!response.ok) {
        throw new Error(`MPLA API returned ${response.status}: ${response.statusText}`);
      }

      // Stream the response and collect results
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let results = [];
      let finalReport = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              if (data.event === 'iteration_complete') {
                results.push(data.data);
              } else if (data.event === 'refinement_complete') {
                finalReport = data.data;
              }
            } catch (e) {
              // Skip malformed JSON
            }
          }
        }
      }

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              session_results: results,
              final_report: finalReport,
              iterations_completed: results.length,
            }, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error.message,
            }, null, 2),
          },
        ],
      };
    }
  }

  async getMPLASessionReport(args) {
    try {
      const response = await fetch(`http://localhost:8080/api/reports/${args.session_id}`);
      
      if (!response.ok) {
        throw new Error(`Failed to get session report: ${response.statusText}`);
      }

      const report = await response.json();
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(report, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error.message,
            }, null, 2),
          },
        ],
      };
    }
  }

  async queryMPLADatabase(args) {
    const { query_type, filters = {} } = args;
    
    try {
      const response = await fetch(`http://localhost:8080/api/database/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query_type,
          filters,
        }),
      });

      if (!response.ok) {
        throw new Error(`Database query failed: ${response.statusText}`);
      }

      const results = await response.json();
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(results, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error.message,
            }, null, 2),
          },
        ],
      };
    }
  }

  async createGitHubIssue(args) {
    const { owner, repo, title, body, labels = [] } = args;
    
    try {
      const octokit = await this.initializeGitHub();
      
      const response = await octokit.rest.issues.create({
        owner,
        repo,
        title,
        body,
        labels,
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              issue: {
                number: response.data.number,
                url: response.data.html_url,
                title: response.data.title,
                state: response.data.state,
              },
            }, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error.message,
            }, null, 2),
          },
        ],
      };
    }
  }

  async getGitHubRepository(args) {
    const { owner, repo } = args;
    
    try {
      const octokit = await this.initializeGitHub();
      
      const response = await octokit.rest.repos.get({
        owner,
        repo,
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              repository: {
                name: response.data.name,
                full_name: response.data.full_name,
                description: response.data.description,
                language: response.data.language,
                stargazers_count: response.data.stargazers_count,
                forks_count: response.data.forks_count,
                open_issues_count: response.data.open_issues_count,
                created_at: response.data.created_at,
                updated_at: response.data.updated_at,
                html_url: response.data.html_url,
              },
            }, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error.message,
            }, null, 2),
          },
        ],
      };
    }
  }

  async searchGitHubCode(args) {
    const { query, sort = 'indexed', order = 'desc' } = args;
    
    try {
      const octokit = await this.initializeGitHub();
      
      const response = await octokit.rest.search.code({
        q: query,
        sort,
        order,
        per_page: 10,
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              total_count: response.data.total_count,
              items: response.data.items.map(item => ({
                name: item.name,
                path: item.path,
                repository: item.repository.full_name,
                html_url: item.html_url,
                score: item.score,
              })),
            }, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error.message,
            }, null, 2),
          },
        ],
      };
    }
  }

  async checkMPLAHealth(args) {
    try {
      const response = await fetch('http://localhost:8080/api/health');
      
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.statusText}`);
      }

      const health = await response.json();
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              health_status: health,
              mcp_server_status: 'running',
              timestamp: new Date().toISOString(),
            }, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error.message,
              mcp_server_status: 'running',
              mpla_api_status: 'unreachable',
            }, null, 2),
          },
        ],
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('MPLA MCP Server running on stdio');
  }
}

const server = new MPLAMCPServer();
server.run().catch(console.error); 