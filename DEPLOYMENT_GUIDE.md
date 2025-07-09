# MPLA Production Deployment Guide

## 🚀 Overview

This guide covers deploying the Meta-Prompt Learning Agent (MPLA) to production using Endgame cloud hosting platform with Docker containerization.

## 📋 Prerequisites

### Required Environment Variables
```bash
GOOGLE_API_KEY="your-google-api-key"
OPENAI_API_KEY="your-openai-api-key"
NODE_ENV="production"
PORT="8080"
```

### System Requirements
- **Node.js**: 22.x (for Endgame compatibility)
- **Python**: 3.11+
- **Memory**: Minimum 1GB, Recommended 2GB
- **CPU**: Minimum 0.5 cores, Recommended 1 core
- **Storage**: 2GB for application + logs

## 🐳 Docker Deployment

### Local Testing
```bash
# Build and test locally
npm run docker:build
npm run docker:run

# Access application at http://localhost:8080
```

### Production Build
```bash
# Build production image
docker build -t mpla-agent:latest .

# Run with production configuration
docker run -d \
  --name mpla-production \
  -p 8080:8080 \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e NODE_ENV="production" \
  -v mpla-data:/app/data \
  -v mpla-logs:/app/logs \
  --restart unless-stopped \
  mpla-agent:latest
```

## ☁️ Endgame Cloud Deployment

### Step 1: Authentication
Ensure you have authenticated with Endgame:
```bash
# This will be handled by the Endgame MCP
# Authentication opens dashboard for OAuth setup
```

### Step 2: Deploy Application
```bash
# Automatic deployment via MCP integration
# Includes build process, containerization, and hosting
```

### Configuration Details
- **Runtime**: Node.js 22.x
- **Entry Point**: `server/start.js`
- **Build Command**: `npm install && npm run build:all`
- **Health Check**: `/api/health`
- **Port**: 8080
- **Auto-scaling**: 1-3 instances

## 🔧 Configuration Management

### Environment-Specific Settings

#### Development
```yaml
# .env.development
NODE_ENV=development
MPLA_LOG_LEVEL=debug
MPLA_DATA_DIR=./dev-data
```

#### Production
```yaml
# Environment variables set in hosting platform
NODE_ENV=production
MPLA_LOG_LEVEL=info
MPLA_DATA_DIR=/app/data
MPLA_LOGS_DIR=/app/logs
```

### Database Configuration
- **Type**: SQLite (file-based)
- **Location**: `MPLA_DATA_DIR/mpla_v2.db`
- **Backup**: Automatic via persistent volumes
- **Migration**: Handled by application startup

## 📊 Monitoring & Health Checks

### Health Check Endpoints
- **Primary**: `GET /api/health`
  - Database connectivity
  - API key validation
  - System status
- **Metrics**: `GET /api/metrics`
  - Performance indicators
  - Usage statistics

### Expected Health Response
```json
{
  "status": "healthy",
  "timestamp": "2024-01-18T10:00:00Z",
  "version": "1.0.0",
  "environment": "production",
  "checks": {
    "database": "connected",
    "api_keys": {
      "google_api": "configured",
      "openai_api": "configured"
    }
  },
  "uptime": "available",
  "memory_usage": "normal"
}
```

## 🔐 Security Considerations

### API Key Management
- **Never commit API keys** to version control
- Use environment variables or secrets management
- Rotate keys regularly
- Monitor for unauthorized usage

### Application Security
- Runs as non-root user in container
- CORS configured for specific origins
- Input validation on all endpoints
- Secure headers enabled

### Network Security
- HTTPS termination at load balancer
- Private container networking
- Rate limiting (if needed)

## 🚨 Troubleshooting

### Common Issues

#### 1. Application Won't Start
```bash
# Check logs
docker logs mpla-production

# Common causes:
# - Missing API keys
# - Database permissions
# - Port conflicts
```

#### 2. Health Check Failures
```bash
# Test health endpoint
curl http://localhost:8080/api/health

# Check database connectivity
# Verify API key configuration
```

#### 3. Performance Issues
```bash
# Monitor resource usage
docker stats mpla-production

# Check application logs
# Consider scaling up resources
```

### Log Analysis
```bash
# View application logs
docker logs --follow mpla-production

# Access persistent logs
docker exec -it mpla-production tail -f /app/logs/mpla.log
```

## 📈 Scaling & Performance

### Horizontal Scaling
- Endgame auto-scaling: 1-3 instances
- Load balancing: Automatic
- Session affinity: Not required (stateless)

### Vertical Scaling
- Memory: Start with 1GB, scale to 2GB+ as needed
- CPU: 0.5 cores minimum, 1+ for heavy workloads
- Storage: Monitor database growth

### Performance Optimization
- Keep API keys in memory
- Connection pooling for external APIs
- Database query optimization
- Static asset caching

## 🔄 CI/CD Pipeline

### Automated Deployment Triggers
- Push to `main` branch
- Manual deployment via dashboard
- Health check validation

### Deployment Process
1. **Build**: Install dependencies, compile assets
2. **Test**: Run health checks, basic functionality
3. **Deploy**: Container deployment to cloud
4. **Verify**: Post-deployment health validation
5. **Monitor**: Continuous health monitoring

## 📞 Support & Maintenance

### Regular Maintenance
- Monitor application logs weekly
- Review performance metrics monthly
- Update dependencies quarterly
- API key rotation as needed

### Emergency Procedures
- **Service Down**: Check health endpoint, restart if needed
- **High Memory Usage**: Scale up or restart
- **API Failures**: Verify API keys, check external service status

---

**Deployment Status**: ✅ Production Ready
**Last Updated**: January 18, 2025
**Version**: 1.0.0 