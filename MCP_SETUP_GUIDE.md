# MPLA MCP & GitHub Integration Setup Guide

## 🎯 Overview

I've implemented both MCP (Model Context Protocol) and GitHub integration for your MPLA project. Here's what was added:

### ✅ What's Now Working

1. **MCP Server**: Full MCP server implementation with 7 tools
2. **GitHub API Integration**: Complete GitHub connectivity
3. **Extended MPLA API**: New endpoints for GitHub and database queries
4. **Environment Configuration**: Proper setup for all integrations

---

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Set Environment Variables

Copy the example environment file:
```bash
cp environment.example .env
```

Edit `.env` with your actual API keys:
```bash
# Required API Keys
GOOGLE_API_KEY=your_actual_google_api_key
OPENAI_API_KEY=your_actual_openai_api_key
GITHUB_TOKEN=your_github_personal_access_token

# Application Settings
NODE_ENV=development
PORT=8080
MPLA_DATA_DIR=./data
```

### 3. Get GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Click "Generate new token" (classic)
3. Select scopes: `repo`, `read:user`, `user:email`
4. Copy the token to your `.env` file

---

## 🛠️ Available MCP Tools

Your MCP server now provides these tools:

### 1. **mpla_run_refinement**
Execute MPLA prompt refinement cycles
```bash
node mcp/client.js refine "Improve this prompt for code generation"
```

### 2. **mpla_database_query** 
Query MPLA knowledge base for analytics
```bash
node mcp/client.js query sessions
node mcp/client.js query performance
```

### 3. **github_create_issue**
Create GitHub issues with MPLA findings
```bash
node mcp/client.js issue owner repo "Bug Report" "Description here"
```

### 4. **github_get_repository**
Analyze GitHub repositories
```bash
node mcp/client.js repo microsoft vscode
```

### 5. **github_search_code**
Search GitHub for prompt patterns
```bash
node mcp/client.js search "prompt engineering"
```

### 6. **mpla_health_check**
Check system status
```bash
node mcp/client.js health
```

### 7. **mpla_get_session_report**
Get detailed session reports

---

## 🔧 Testing the Setup

### Start the MPLA Server
```bash
npm start
```

### Test MCP Integration
```bash
# List available tools
node mcp/client.js list-tools

# Check system health
node mcp/client.js health

# Test GitHub connection
node mcp/client.js repo octocat Hello-World
```

### Test GitHub API Directly
```bash
# Get repository info
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
     http://localhost:8080/api/github/repository/octocat/Hello-World

# Check health with GitHub token status
curl http://localhost:8080/api/health
```

---

## 🔗 Integration Usage

### Using MCP with AI Assistants

Add this to your MCP client configuration:
```json
{
  "mcpServers": {
    "mpla-server": {
      "command": "node",
      "args": ["mcp/server.js"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "MPLA_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### GitHub Integration Features

1. **Repository Analysis**: Get repo stats for prompt engineering insights
2. **Issue Creation**: Automatically create issues from MPLA findings  
3. **Code Search**: Find prompt engineering patterns across GitHub
4. **Integration with MPLA**: All tools work with your existing MPLA system

---

## 🐳 Docker Support

The integrations work with your existing Docker setup:

```bash
# Build with new dependencies
npm run docker:build

# Run with GitHub token
docker run -e GITHUB_TOKEN=your_token mpla-agent
```

---

## 🔍 Troubleshooting

### Common Issues

1. **"GitHub token not configured"**
   - Ensure `GITHUB_TOKEN` is set in your `.env` file
   - Verify the token has proper scopes

2. **"MCP Server connection failed"**
   - Check that Node.js dependencies are installed
   - Verify the MPLA server is running on port 8080

3. **"Database query failed"**
   - Ensure the MPLA database exists (`mpla_v2.db`)
   - Check database permissions

### Debug Commands

```bash
# Check environment variables
node -e "console.log(process.env.GITHUB_TOKEN ? 'GitHub token set' : 'No GitHub token')"

# Test database connection
curl http://localhost:8080/api/health

# Verify MCP server
node mcp/client.js list-tools
```

---

## 🎉 What's Fixed

### ❌ Before
- No MCP implementation (only references in docs)
- No GitHub connectivity
- Limited external integrations

### ✅ Now  
- **Full MCP Server**: 7 working tools with real functionality
- **GitHub Integration**: Complete API access with authentication
- **Extended MPLA API**: New endpoints for GitHub and database queries
- **Proper Environment Setup**: All configurations documented and working
- **Testing Tools**: MCP client for easy testing and debugging

You now have a fully functional MCP server with GitHub integration! The MCPs are working and you can connect to GitHub through both the MCP tools and direct API calls. 