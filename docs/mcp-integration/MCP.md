# MCP Management API Reference

## Overview
The MCP (Model Context Protocol) management endpoints allow you to discover, monitor, and interact with connected MCP servers.

**Base URL**: `http://localhost:8000`

**API Documentation**: [http://localhost:8000/docs#/](http://localhost:8000/docs#/)

> **Note for LLM Integration**: To get all available MCP endpoints and build dashboard functionalities, refer to the complete API documentation at `http://localhost:8000/docs#/`. This provides the definitive list of endpoints, request/response schemas, and parameters needed for MCP section implementation in the dashboard.

---

## Endpoints

### 1. List All MCP Servers
**GET** `/mcp/tools/servers`

Get all configured MCP servers from the database.

**Query Parameters**:
- `enabled_only` (boolean): Filter to only active servers
- `include_health` (boolean): Include real-time health check

**Response**:
```json
{
  "success": true,
  "data": {
    "servers": [
      {
        "name": "performance_mcp",
        "url": "http://mcp-db-performance:8000",
        "protocol": "http",
        "enabled": true,
        "description": "Database performance monitoring",
        "timeout_seconds": 30,
        "health_status": "healthy",
        "last_health_check": "2024-01-26T10:30:00Z"
      }
    ],
    "summary": {
      "total": 5,
      "enabled": 3,
      "disabled": 2
    }
  }
}
```

---

### 2. Get All MCP Capabilities
**GET** `/mcp/tools/capabilities`

Returns all tools, prompts, and resources exposed by MCP servers.

**Query Parameters**:
- `server` (string, optional): Filter by specific MCP server name

**Response**:
```json
{
  "success": true,
  "data": {
    "performance_mcp": {
      "tools": [
        {
          "name": "analyze_query",
          "description": "Analyze SQL query performance",
          "inputSchema": {...}
        }
      ],
      "prompts": [
        {
          "name": "optimization_guide",
          "description": "SQL optimization recommendations",
          "arguments": [...]
        }
      ],
      "resources": [
        {
          "uri": "config://settings",
          "name": "Configuration",
          "description": "Server configuration",
          "mimeType": "application/json"
        }
      ],
      "metadata": {
        "tool_count": 10,
        "prompt_count": 5,
        "resource_count": 3,
        "connection_age_seconds": 120
      }
    }
  },
  "summary": {
    "total_servers": 1,
    "total_tools": 10,
    "total_prompts": 5,
    "total_resources": 3
  }
}
```

---

### 3. List Tools
**GET** `/mcp/tools/list`

List available tools from MCP servers.

**Query Parameters**:
- `server` (string, optional): Filter by server name

**Response**:
```json
{
  "success": true,
  "data": {
    "servers": {
      "performance_mcp": [
        {
          "name": "analyze_query",
          "description": "Analyze SQL query performance",
          "inputSchema": {...}
        }
      ]
    }
  }
}
```

---

### 4. Call Tool
**POST** `/mcp/tools/call`

Execute a tool on an MCP server.

**Request Body**:
```json
{
  "server": "performance_mcp",
  "tool": "analyze_query",
  "arguments": {
    "query": "SELECT * FROM users",
    "database": "production"
  }
}
```

**Response**:
```json
{
  "success": true,
  "server": "performance_mcp",
  "tool": "analyze_query",
  "result": {
    "execution_plan": "...",
    "recommendations": [...]
  }
}
```

---

### 5. Health Check
**GET** `/mcp/tools/health/{server_name}`

Check health status of a specific MCP server.

**Response**:
```json
{
  "success": true,
  "server": "performance_mcp",
  "health": {
    "healthy": true,
    "tool_count": 10,
    "response_time_ms": 45,
    "last_check": "2024-01-26T10:30:00Z"
  }
}
```

---

### 6. Reload MCPs
**POST** `/mcp/tools/reload`

Manually trigger MCP reload from database.

**Query Parameters**:
- `mcp_name` (string, optional): Reload specific MCP, or all if not provided

**Response**:
```json
{
  "success": true,
  "message": "All MCPs reloaded",
  "loaded_mcps": ["performance_mcp", "informatica_mcp"],
  "count": 2
}
```

---

### 7. Get User-Specific Tools
**GET** `/mcp/tools/mcps/{mcp_name}/tools`

Get tools filtered by user permissions.

**Query Parameters**:
- `user_email` (string): User's email address

**Response**:
```json
{
  "success": true,
  "mcp_name": "performance_mcp",
  "description": "Tools from performance_mcp",
  "tools": [...],
  "total_available": 10,
  "user_allowed": 7
}
```

---

## Usage Examples

### Get All Capabilities
```bash
curl http://localhost:8000/mcp/tools/capabilities
```

### Get Capabilities for Specific MCP
```bash
curl "http://localhost:8000/mcp/tools/capabilities?server=performance_mcp"
```

### List Active Servers
```bash
curl "http://localhost:8000/mcp/tools/servers?enabled_only=true"
```

### Execute a Tool
```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "server": "performance_mcp",
    "tool": "analyze_query",
    "arguments": {"query": "SELECT * FROM users"}
  }'
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `200`: Success
- `404`: MCP server or resource not found
- `500`: Internal server error or MCP communication failure

---

## Circuit Breaker

MCPs have circuit breaker protection. If a server becomes unavailable:

```json
{
  "status": "unavailable",
  "error": "MCP 'performance_mcp' temporarily unavailable (circuit breaker open)",
  "circuit_state": "open",
  "retry_after_seconds": 30
}
```
