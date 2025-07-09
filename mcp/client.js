#!/usr/bin/env node

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { spawn } from 'child_process';

class MPLAMCPClient {
  constructor() {
    this.client = new Client(
      {
        name: 'mpla-mcp-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      }
    );
  }

  async connect() {
    // Start the MCP server process
    const serverProcess = spawn('node', ['mcp/server.js'], {
      stdio: ['pipe', 'pipe', 'inherit'],
      env: {
        ...process.env,
        GITHUB_TOKEN: process.env.GITHUB_TOKEN,
        MPLA_API_URL: process.env.MPLA_API_URL || 'http://localhost:8080'
      }
    });

    const transport = new StdioClientTransport({
      reader: serverProcess.stdout,
      writer: serverProcess.stdin,
    });

    await this.client.connect(transport);
    console.log('Connected to MPLA MCP Server');
    
    return this;
  }

  async listTools() {
    try {
      const response = await this.client.request({
        method: 'tools/list',
      }, {});
      
      console.log('Available tools:');
      response.tools.forEach(tool => {
        console.log(`- ${tool.name}: ${tool.description}`);
      });
      
      return response.tools;
    } catch (error) {
      console.error('Failed to list tools:', error);
      return [];
    }
  }

  async runMPLARefinement(prompt, settings = {}) {
    try {
      const response = await this.client.request({
        method: 'tools/call',
        params: {
          name: 'mpla_run_refinement',
          arguments: {
            prompt,
            settings
          }
        }
      }, {});
      
      return JSON.parse(response.content[0].text);
    } catch (error) {
      console.error('Failed to run MPLA refinement:', error);
      return { success: false, error: error.message };
    }
  }

  async queryDatabase(queryType, filters = {}) {
    try {
      const response = await this.client.request({
        method: 'tools/call',
        params: {
          name: 'mpla_database_query',
          arguments: {
            query_type: queryType,
            filters
          }
        }
      }, {});
      
      return JSON.parse(response.content[0].text);
    } catch (error) {
      console.error('Failed to query database:', error);
      return { success: false, error: error.message };
    }
  }

  async createGitHubIssue(owner, repo, title, body, labels = []) {
    try {
      const response = await this.client.request({
        method: 'tools/call',
        params: {
          name: 'github_create_issue',
          arguments: {
            owner,
            repo,
            title,
            body,
            labels
          }
        }
      }, {});
      
      return JSON.parse(response.content[0].text);
    } catch (error) {
      console.error('Failed to create GitHub issue:', error);
      return { success: false, error: error.message };
    }
  }

  async getGitHubRepository(owner, repo) {
    try {
      const response = await this.client.request({
        method: 'tools/call',
        params: {
          name: 'github_get_repository',
          arguments: {
            owner,
            repo
          }
        }
      }, {});
      
      return JSON.parse(response.content[0].text);
    } catch (error) {
      console.error('Failed to get GitHub repository:', error);
      return { success: false, error: error.message };
    }
  }

  async searchGitHubCode(query, sort = 'indexed', order = 'desc') {
    try {
      const response = await this.client.request({
        method: 'tools/call',
        params: {
          name: 'github_search_code',
          arguments: {
            query,
            sort,
            order
          }
        }
      }, {});
      
      return JSON.parse(response.content[0].text);
    } catch (error) {
      console.error('Failed to search GitHub code:', error);
      return { success: false, error: error.message };
    }
  }

  async checkHealth() {
    try {
      const response = await this.client.request({
        method: 'tools/call',
        params: {
          name: 'mpla_health_check',
          arguments: {}
        }
      }, {});
      
      return JSON.parse(response.content[0].text);
    } catch (error) {
      console.error('Failed to check health:', error);
      return { success: false, error: error.message };
    }
  }
}

// Example usage
async function example() {
  if (process.argv.length < 3) {
    console.log('Usage: node mcp/client.js <command> [args...]');
    console.log('Commands:');
    console.log('  list-tools - List available MCP tools');
    console.log('  health - Check MPLA system health');
    console.log('  refine <prompt> - Run MPLA refinement');
    console.log('  query <type> - Query MPLA database (sessions, prompts, evaluations, performance)');
    console.log('  repo <owner> <repo> - Get GitHub repository info');
    console.log('  search <query> - Search GitHub code');
    console.log('  issue <owner> <repo> <title> <body> - Create GitHub issue');
    return;
  }

  const client = new MPLAMCPClient();
  await client.connect();

  const command = process.argv[2];

  switch (command) {
    case 'list-tools':
      await client.listTools();
      break;
    
    case 'health':
      const health = await client.checkHealth();
      console.log('Health check result:', JSON.stringify(health, null, 2));
      break;
    
    case 'refine':
      if (process.argv[3]) {
        const result = await client.runMPLARefinement(process.argv[3]);
        console.log('Refinement result:', JSON.stringify(result, null, 2));
      } else {
        console.log('Usage: node mcp/client.js refine <prompt>');
      }
      break;
    
    case 'query':
      if (process.argv[3]) {
        const result = await client.queryDatabase(process.argv[3]);
        console.log('Query result:', JSON.stringify(result, null, 2));
      } else {
        console.log('Usage: node mcp/client.js query <type>');
      }
      break;
    
    case 'repo':
      if (process.argv[3] && process.argv[4]) {
        const result = await client.getGitHubRepository(process.argv[3], process.argv[4]);
        console.log('Repository info:', JSON.stringify(result, null, 2));
      } else {
        console.log('Usage: node mcp/client.js repo <owner> <repo>');
      }
      break;
    
    case 'search':
      if (process.argv[3]) {
        const result = await client.searchGitHubCode(process.argv[3]);
        console.log('Search results:', JSON.stringify(result, null, 2));
      } else {
        console.log('Usage: node mcp/client.js search <query>');
      }
      break;
    
    case 'issue':
      if (process.argv[3] && process.argv[4] && process.argv[5] && process.argv[6]) {
        const result = await client.createGitHubIssue(
          process.argv[3], 
          process.argv[4], 
          process.argv[5], 
          process.argv[6]
        );
        console.log('Issue created:', JSON.stringify(result, null, 2));
      } else {
        console.log('Usage: node mcp/client.js issue <owner> <repo> <title> <body>');
      }
      break;
    
    default:
      console.log('Unknown command:', command);
  }

  process.exit(0);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  example().catch(console.error);
}

export { MPLAMCPClient }; 