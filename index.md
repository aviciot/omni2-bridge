---
layout: default
title: Omni2 - Secure MCP Management Platform
---

<div style="text-align: right; margin-bottom: 20px;">
  <a href="https://github.com/aviciot/omni2-bridge" class="btn" style="background: #24292e; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; display: inline-block;">
    🐙 View on GitHub
  </a>
</div>

<div style="text-align: center; margin: 40px 0;">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/docker-required-blue.svg" alt="Docker">
</div>

## 🎯 What is Omni2?

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin: 30px 0;">
  <h3 style="color: white; border: none; margin-top: 0;">Secure MCP Management & Orchestration Platform</h3>
  <p style="font-size: 1.1em;">Omni2 enables organizations to securely expose, manage, and monitor Model Context Protocol (MCP) servers for both internal teams and external customers with enterprise-grade security and zero-downtime operations.</p>
</div>

### System Architecture Overview

```mermaid
flowchart TB
    subgraph Users[" 👥 Users (Internal & External) "]
        INT[Internal Team<br/>localhost]
        EXT[External Customers<br/>Internet]
    end

    subgraph Gateway[" 🚪 Traefik Gateway (Single Entry Point) "]
        AUTH[🔐 Authentication<br/>JWT Validation]
        ROUTE[🔀 Routing<br/>Load Balancing]
    end

    subgraph Management[" 🎛️ Management Layer "]
        DASH[📊 Admin Dashboard<br/>User & MCP Management]
        OMNI[🤖 Omni2 Core<br/>MCP Orchestration]
        AUDIT[📝 Audit Logging<br/>Compliance]
    end

    subgraph MCPs[" 🔧 MCP Servers (Managed & Secured) "]
        DB[Database MCP<br/>SQL Analysis]
        CODE[Code MCP<br/>Git Operations]
        ETL[ETL MCP<br/>Workflows]
    end

    INT --> Gateway
    EXT --> Gateway
    Gateway --> AUTH
    AUTH --> ROUTE
    ROUTE --> DASH & OMNI
    OMNI --> MCPs
    OMNI --> AUDIT
    
    style Gateway fill:#4CAF50,stroke:#2E7D32,color:#fff
    style Management fill:#2196F3,stroke:#1565C0,color:#fff
    style MCPs fill:#FF9800,stroke:#E65100,color:#fff
```

**Key Capabilities:**

| Feature | Benefit |
|---------|----------|
| **Centralized Auth** | Single sign-on for all MCPs - no per-MCP authentication needed |
| **Access Control** | Role-based permissions (admin, developer, viewer) |
| **Audit Trail** | Track every MCP call with user, timestamp, and parameters |
| **Health Monitoring** | Real-time status of all MCP servers with automatic alerts |
| **Secure by Default** | MCPs never exposed directly - only via authenticated gateway |
| **Production Ready** | HTTPS, rate limiting, DDoS protection via Cloudflare |

---

## 🚀 Quick Links

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0;">
  <a href="./docs/deployment/QUICK_START" style="text-decoration: none;">
    <div style="background: #f6f8fa; border: 2px solid #0366d6; border-radius: 10px; padding: 25px; text-align: center; transition: transform 0.2s;">
      <h3 style="color: #0366d6; margin-top: 0;">⚡ Quick Start</h3>
      <p style="color: #586069;">Get running in 5 minutes</p>
    </div>
  </a>
  
  <a href="./docs/architecture/TRAEFIK_ARCHITECTURE" style="text-decoration: none;">
    <div style="background: #f6f8fa; border: 2px solid #28a745; border-radius: 10px; padding: 25px; text-align: center; transition: transform 0.2s;">
      <h3 style="color: #28a745; margin-top: 0;">🏗️ Architecture</h3>
      <p style="color: #586069;">System design & diagrams</p>
    </div>
  </a>
  
  <a href="./docs/security/SECURITY_OVERVIEW" style="text-decoration: none;">
    <div style="background: #f6f8fa; border: 2px solid #d73a49; border-radius: 10px; padding: 25px; text-align: center; transition: transform 0.2s;">
      <h3 style="color: #d73a49; margin-top: 0;">🔐 Security</h3>
      <p style="color: #586069;">Multi-layer protection</p>
    </div>
  </a>
  
  <a href="./docs/mcp-integration/ADDING_NEW_MCP" style="text-decoration: none;">
    <div style="background: #f6f8fa; border: 2px solid #6f42c1; border-radius: 10px; padding: 25px; text-align: center; transition: transform 0.2s;">
      <h3 style="color: #6f42c1; margin-top: 0;">🔌 Add MCPs</h3>
      <p style="color: #586069;">Integration guide</p>
    </div>
  </a>
</div>

---

## ✨ Key Features

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin: 30px 0;">
  <div style="background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h3 style="color: #0366d6; margin-top: 0;">🔐 Enterprise Security</h3>
    <ul style="color: #586069; line-height: 1.8;">
      <li>JWT authentication & API keys</li>
      <li>Role-based access control (RBAC)</li>
      <li>ForwardAuth middleware</li>
      <li>Multi-layer SQL protection</li>
    </ul>
  </div>
  
  <div style="background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h3 style="color: #28a745; margin-top: 0;">⚡ High Performance</h3>
    <ul style="color: #586069; line-height: 1.8;">
      <li>Async Python architecture</li>
      <li>Connection pooling</li>
      <li>Circuit breaker pattern</li>
      <li>~1000 req/sec throughput</li>
    </ul>
  </div>
  
  <div style="background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h3 style="color: #d73a49; margin-top: 0;">🔄 Zero Downtime</h3>
    <ul style="color: #586069; line-height: 1.8;">
      <li>Load balancing</li>
      <li>Health checks & failover</li>
      <li>Rolling deployments</li>
      <li>Automatic retry logic</li>
    </ul>
  </div>
  
  <div style="background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h3 style="color: #6f42c1; margin-top: 0;">📊 Management</h3>
    <ul style="color: #586069; line-height: 1.8;">
      <li>User & permission management</li>
      <li>MCP lifecycle control</li>
      <li>Comprehensive audit logs</li>
      <li>Real-time monitoring</li>
    </ul>
  </div>
  
  <div style="background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h3 style="color: #0366d6; margin-top: 0;">🚪 Traefik Gateway</h3>
    <ul style="color: #586069; line-height: 1.8;">
      <li>Single entry point</li>
      <li>HTTPS termination</li>
      <li>Rate limiting</li>
      <li>Auto-discovery</li>
    </ul>
  </div>
  
  <div style="background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h3 style="color: #28a745; margin-top: 0;">📈 Scalability</h3>
    <ul style="color: #586069; line-height: 1.8;">
      <li>Horizontal scaling</li>
      <li>100+ concurrent users</li>
      <li>Resource management</li>
      <li>Future: Multi-tenancy</li>
    </ul>
  </div>
</div>

---

## 🛠️ Technology Stack

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 30px 0;">
  <div style="background: #f6f8fa; border-left: 4px solid #0366d6; padding: 15px;">
    <strong>Backend</strong><br>
    Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
  </div>
  <div style="background: #f6f8fa; border-left: 4px solid #28a745; padding: 15px;">
    <strong>Gateway</strong><br>
    Traefik v3.6, Docker, Docker Compose
  </div>
  <div style="background: #f6f8fa; border-left: 4px solid #d73a49; padding: 15px;">
    <strong>Frontend</strong><br>
    Next.js 14, TypeScript, Tailwind CSS
  </div>
</div>

---

## 📚 Documentation

<div style="background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 30px; margin: 30px 0;">
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
    <div>
      <h4 style="color: #0366d6; margin-top: 0;">🚀 Getting Started</h4>
      <ul style="line-height: 2;">
        <li><a href="./docs/deployment/QUICK_START">Quick Start Guide</a></li>
        <li><a href="./docs/deployment/PRODUCTION_SETUP">Production Setup</a></li>
        <li><a href="./docs/deployment/TROUBLESHOOTING">Troubleshooting</a></li>
      </ul>
    </div>
    
    <div>
      <h4 style="color: #28a745; margin-top: 0;">🏗️ Architecture</h4>
      <ul style="line-height: 2;">
        <li><a href="./docs/architecture/TRAEFIK_ARCHITECTURE">Traefik Gateway</a></li>
        <li><a href="./docs/architecture/SYSTEM_OVERVIEW">System Overview</a></li>
        <li><a href="./docs/architecture/DATABASE_SCHEMA">Database Schema</a></li>
      </ul>
    </div>
    
    <div>
      <h4 style="color: #d73a49; margin-top: 0;">🔐 Security</h4>
      <ul style="line-height: 2;">
        <li><a href="./docs/security/SECURITY_OVERVIEW">Security Overview</a></li>
        <li><a href="./docs/security/AUTHENTICATION">Authentication</a></li>
        <li><a href="./docs/security/AUTHORIZATION">Authorization</a></li>
      </ul>
    </div>
    
    <div>
      <h4 style="color: #6f42c1; margin-top: 0;">🔌 MCP Integration</h4>
      <ul style="line-height: 2;">
        <li><a href="./docs/mcp-integration/ADDING_NEW_MCP">Adding New MCPs</a></li>
        <li><a href="./docs/mcp-integration/MCP_CONFIGURATION">Configuration</a></li>
        <li><a href="./docs/mcp-integration/BEST_PRACTICES">Best Practices</a></li>
      </ul>
    </div>
  </div>
</div>

---

## 🎯 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/aviciot/omni2-bridge.git
cd omni2-bridge

# 2. Configure environment
cp .env.example .env

# 3. Start services
./start.sh

# 4. Verify
curl http://localhost:8090/health
```

**[Full Setup Guide →](./docs/deployment/QUICK_START)**

---

## 📊 Performance Metrics

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; text-align: center;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px;">
    <h2 style="color: white; border: none; margin: 0;">< 100ms</h2>
    <p style="margin: 10px 0 0 0;">Request Latency (p95)</p>
  </div>
  <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 25px; border-radius: 10px;">
    <h2 style="color: white; border: none; margin: 0;">~1000</h2>
    <p style="margin: 10px 0 0 0;">Requests/Second</p>
  </div>
  <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 25px; border-radius: 10px;">
    <h2 style="color: white; border: none; margin: 0;">100+</h2>
    <p style="margin: 10px 0 0 0;">Concurrent Users</p>
  </div>
  <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; padding: 25px; border-radius: 10px;">
    <h2 style="color: white; border: none; margin: 0;">95%+</h2>
    <p style="margin: 10px 0 0 0;">Test Coverage</p>
  </div>
</div>

---

## 🤝 Contributing

We welcome contributions! Check out our [Contributing Guide](./docs/development/CONTRIBUTING) to get started.

---

## 📧 Contact

<div style="background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 8px; padding: 25px; margin: 30px 0;">
  <strong>Avi Cohen</strong><br>
  📧 Email: <a href="mailto:avicoiot@gmail.com">avicoiot@gmail.com</a><br>
  🐙 GitHub: <a href="https://github.com/aviciot">@aviciot</a><br>
  💼 LinkedIn: <a href="https://www.linkedin.com/in/avi-cohen">Avi Cohen</a>
</div>

<div style="text-align: center; margin: 40px 0; color: #586069;">
  <p>Built with ❤️ to solve real enterprise challenges in AI infrastructure</p>
</div>
