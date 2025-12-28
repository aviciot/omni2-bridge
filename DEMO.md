# OMNI2 API Demo Examples

Quick reference for testing OMNI2 endpoints in Swagger UI: http://localhost:8000/docs

---

## 🧠 How OMNI2 Intelligent Routing Works

OMNI2 is a **generic, self-updating MCP router** powered by Claude AI. Here's how it works:

### Architecture Overview
```
User Question → OMNI2 → Claude AI → MCP Discovery → Tool Selection → Execution → Answer
```

###Dynamic MCP Discovery (No Hardcoding!)
1. **Load MCPs from config** - Reads `mcps.yaml` at startup
2. **Discover tools automatically** - Fetches available tools from each MCP server
3. **Build dynamic catalog** - Creates inventory of ALL tools from ALL enabled MCPs
4. **No code changes needed** - Add new MCP to yaml, system auto-discovers it

### 🤖 Intelligent Routing Process

**Step 1: User Permission Check**
- User sends question with `user_id`
- System loads user from `users.yaml`
- Checks `allowed_mcps` (which MCPs user can access)
- Checks `allowed_domains` (which topics user can ask about)

**Step 2: Build Dynamic System Prompt**
- Lists ALL available MCP tools for that specific user
- Includes tool descriptions dynamically from MCP servers
- Adds user's allowed knowledge domains
- No hardcoded tool names or MCP references!

**Step 3: Claude Decides**
- Claude reads the system prompt with available tools
- Analyzes user's natural language question
- Decides if it needs MCP tools OR can answer directly
- Selects the RIGHT tool(s) from available options

**Step 4: Tool Execution**
- If tool needed: Calls `{mcp_name}__tool_name}` format
- Splits to get MCP server name and tool name
- Executes tool via MCP protocol (HTTP/Stdio/SSE)
- Returns results to Claude

**Step 5: Answer Synthesis**
- Claude receives tool results
- Synthesizes natural language answer
- Returns to user with metadata (tools_used, tool_calls)

### 🔑 Key Features

**✅ 100% Generic**
- No hardcoded MCP names in routing logic
- No hardcoded tool names
- System discovers everything dynamically

**✅ Self-Updating**
- Add new MCP to `mcps.yaml` → System automatically knows about it
- MCP adds new tool → System automatically exposes it
- No code deployment needed!

**✅ Permission-Aware**
- Users only see tools from their `allowed_mcps`
- Claude can't call tools user doesn't have access to
- Domain restrictions for general knowledge questions

**✅ Intelligent Fallback**
- If question doesn't need tools → Direct answer
- If tool fails → Explain error and suggest alternatives
- If user lacks permission → Politely explain what they CAN do

### 📝 Example Flow

**Question**: "Show me the health of transformer_master database"

1. User: `avi.cohen@shift4.com` (admin with `allowed_mcps: "*"`)
2. System discovers: `database_mcp` has `get_database_health` tool
3. Claude sees tool in system prompt
4. Claude decides: "This needs database_mcp__get_database_health"
5. System executes: `database_mcp.get_database_health(database_name="transformer_master")`
6. Tool returns: Health metrics JSON
7. Claude synthesizes: "Your transformer_master database is healthy. CPU: 45%, Memory: 67%..."

**Add New MCP Tomorrow?**
Just add to `mcps.yaml`:
```yaml
- name: slack_mcp
  url: http://slack-mcp:8400/mcp
  enabled: true
```
**Done!** OMNI2 immediately knows about it. No code changes!

---

## 📋 List All MCP Servers

**Endpoint:** `GET /mcp/tools/servers`

### Get all configured MCPs
```
/mcp/tools/servers
```

### Get only enabled MCPs
```
/mcp/tools/servers?enabled_only=true
```

### Get enabled MCPs with health status
```
/mcp/tools/servers?enabled_only=true&include_health=true
```

---

## 🔍 List Available Tools

**Endpoint:** `GET /mcp/tools/list`

### List all tools from all MCPs
```
/mcp/tools/list
```

### List tools from specific MCP
```
/mcp/tools/list?server=github_mcp
```

```
/mcp/tools/list?server=database_mcp
```

---

## 🔧 Call MCP Tools

**Endpoint:** `POST /mcp/tools/call`

### GitHub: Search Repositories
```json
{
  "server": "github_mcp",
  "tool": "search_repositories",
  "arguments": {
    "query": "user:aviciot python",
    "perPage": 5
  }
}
```

### GitHub: Search by Language
```json
{
  "server": "github_mcp",
  "tool": "search_repositories",
  "arguments": {
    "query": "fastmcp language:python stars:>100",
    "perPage": 10,
    "sort": "stars",
    "order": "desc"
  }
}
```

### GitHub: Get File Contents
```json
{
  "server": "github_mcp",
  "tool": "get_file_contents",
  "arguments": {
    "owner": "aviciot",
    "repo": "MetaQuery-MCP",
    "path": "README.md"
  }
}
```

### Oracle: Get Database Health
```json
{
  "server": "database_mcp",
  "tool": "get_database_health",
  "arguments": {
    "database_name": "PROD_DB"
  }
}
```

### Oracle: Get Top Queries
```json
{
  "server": "database_mcp",
  "tool": "get_top_queries",
  "arguments": {
    "database_name": "PROD_DB",
    "limit": 10,
    "order_by": "cpu_time"
  }
}
```

### Oracle: Analyze Query
```json
{
  "server": "database_mcp",
  "tool": "analyze_oracle_query",
  "arguments": {
    "database_name": "PROD_DB",
    "query": "SELECT * FROM users WHERE status = 'active'"
  }
}
```

---

## 🏥 Health Check

**Endpoint:** `GET /mcp/tools/health/{server_name}`

### Check GitHub MCP health
```
/mcp/tools/health/github_mcp
```

### Check Database MCP health
```
/mcp/tools/health/database_mcp
```

---

## 💡 Quick Tips

### Search Query Filters (GitHub)
- `user:USERNAME` - Search user's repos
- `org:ORGNAME` - Search organization repos
- `language:LANG` - Filter by language
- `stars:>N` - Repos with more than N stars
- `topic:TOPIC` - Filter by topic
- `fork:true/false` - Include/exclude forks
- `archived:false` - Exclude archived repos

### Examples:
```
"query": "user:aviciot python"
"query": "org:microsoft language:typescript stars:>1000"
"query": "topic:mcp language:python"
"query": "fastmcp stars:>100 fork:false archived:false"
```

---

## 🎯 Current MCP Status

- ✅ **GitHub MCP** - 2 tools (search_repositories, get_file_contents)
- ✅ **Database MCP** - 8 tools (database monitoring & query analysis)
- ✅ **Analytics MCP** - 11 tools (cost tracking, performance analysis, error monitoring) - **ADMIN ONLY**
- ❌ **Filesystem MCP** - Disabled
- ❌ **Smoketest MCP** - Disabled

---

## 💬 LLM Chat Integration (AI-Powered MCP Routing)

**Endpoint:** `POST /chat/ask`

The chat endpoint uses Claude AI to intelligently route requests to appropriate MCP tools based on natural language questions.

### Test in Swagger UI

1. Go to http://localhost:8000/docs
2. Find the `Chat` section
3. Click on `POST /chat/ask`
4. Click "Try it out"
5. Paste one of the example requests below
6. Click "Execute"

### 🧪 Test Prompts

#### General Knowledge (No Tool Calls)
```json
{
  "user_id": "developer@company.com",
  "message": "What is Python?"
}
```

```json
{
  "user_id": "developer@company.com",
  "message": "Explain what MCP is and how it works"
}
```

```json
{
  "user_id": "developer@company.com",
  "message": "What are the best practices for API design?"
}
```

#### GitHub MCP Tool Calls
```json
{
  "user_id": "developer@company.com",
  "message": "Search GitHub for FastMCP repositories"
}
```

```json
{
  "user_id": "developer@company.com",
  "message": "Find Python projects related to AI agents"
}
```

```json
{
  "user_id": "developer@company.com",
  "message": "Show me popular TypeScript MCP servers on GitHub"
}
```

```json
{
  "user_id": "developer@company.com",
  "message": "Find repositories about Model Context Protocol with more than 100 stars"
}
```

```json
{
  "user_id": "developer@company.com",
  "message": "What's in the README of jlowin/fastmcp repository?"
}
```

#### Database MCP Tool Calls (Testing with Database Performance MCP)

**Test with your email:**
```json
{
  "user_id": "avi.cohen@shift4.com",
  "message": "Check the health of transformer_master database"
}
```

```json
{
  "user_id": "avi.cohen@shift4.com",
  "message": "Show me the top 10 slowest queries in mysql_devdb03_avi"
}
```

```json
{
  "user_id": "avi.cohen@shift4.com",
  "message": "Get current active sessions for transformer_master database"
}
```

```json
{
  "user_id": "avi.cohen@shift4.com",
  "message": "Analyze the query: SELECT * FROM users WHERE created_at > SYSDATE - 7"
}
```

```json
{
  "user_id": "avi.cohen@shift4.com",
  "message": "What's the buffer cache hit ratio for my production database?"
}
```

```json
{
  "user_id": "avi.cohen@shift4.com",
  "message": "Show me wait events and blocking sessions in transformer_master"
}
```

**Test with DBA user:**
```json
{
  "user_id": "dba@company.com",
  "message": "Check the health of the database"
}
```

```json
{
  "user_id": "dba@company.com",
  "message": "Show me current database sessions"
}
```

```json
{
  "user_id": "dba@company.com",
  "message": "What are the top SQL queries by execution time?"
}
```

#### Analytics MCP Tool Calls (ADMIN ONLY - Internal System Monitoring)

**⚠️ Admin-Only Access:** Only users with admin role (avicoiot@gmail.com) can access Analytics MCP

**Cost & Budget Analytics:**
```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Show me cost summary for today"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "What are the top 5 most expensive queries this week?"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Show me total costs grouped by user for this month"
}
```

**Performance Analytics:**
```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Show me the slowest queries from today"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Which queries required more than 5 iterations?"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "What queries are taking longer than 10 seconds?"
}
```

**Error Analysis:**
```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Show me error summary for today"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "What are the most recent failed queries?"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Which MCP has the highest error rate?"
}
```

**User Activity Analytics:**
```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Who are the most active users this week?"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Show me user activity by role"
}
```

**Tool & MCP Usage Analytics:**
```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "What are the most popular tools?"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Show me MCP health summary"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Which tools have the best success rates?"
}
```

**Token & Caching Analytics:**
```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Show me token usage for today"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "What's the cache hit rate?"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "How effective is prompt caching?"
}
```

**Combined Analytics (Multi-Tool):**
```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "Show me the top 3 most expensive queries and who are the most active users"
}
```

```json
{
  "user_id": "avicoiot@gmail.com",
  "message": "What's the current system health: costs, errors, and performance?"
}
```

**Testing Non-Admin Access (Should Be Blocked):**
```json
{
  "user_id": "developer@company.com",
  "message": "Show me cost summary"
}
```
*Expected: Should NOT see analytics tools, will explain they don't have access*

```json
{
  "user_id": "dba@company.com",
  "message": "What are the most expensive queries?"
}
```
*Expected: Should be blocked from analytics tools*

#### Permission Testing
```json
{
  "user_id": "qa@company.com",
  "message": "Check database health"
}
```
*Expected: Should explain that QA user doesn't have access to Database MCP*

```json
{
  "user_id": "analyst@company.com",
  "message": "Search GitHub for data visualization tools"
}
```
*Expected: Should work - analyst has GitHub MCP access*

```json
{
  "user_id": "unknown@test.com",
  "message": "What are best TV shows in 2024?"
}
```
*Expected: Uses default_user permissions, answers with general knowledge*

#### Complex Multi-Step Reasoning
```json
{
  "user_id": "developer@company.com",
  "message": "Find the most popular Python MCP server on GitHub and tell me what it does"
}
```

```json
{
  "user_id": "developer@company.com",
  "message": "Compare FastMCP repositories written in Python vs TypeScript"
}
```

```json
{
  "user_id": "developer@company.com",
  "message": "What MCP tools are available to me and what can they do?"
}
```

### 📊 Response Format

Successful response:
```json
{
  "success": true,
  "answer": "Here is the answer to your question...",
  "tool_calls": 3,
  "tools_used": ["database_mcp.list_available_databases", "database_mcp.get_database_health", "database_mcp.get_database_health"],
  "iterations": 2,
  "error": null,
  "warning": null
}
```

**Response Fields:**
- `success`: Whether the request completed successfully
- `answer`: Natural language answer from Claude
- `tool_calls`: Total number of MCP tools executed
- `tools_used`: List of tools called (format: `mcp_name.tool_name`)
- `iterations`: Number of agentic loop iterations (multi-step reasoning)
- `error`: Error message if request failed
- `warning`: Warning message (e.g., "max_iterations_reached")

**Iterations Explained:**
- `1`: Simple question, answered directly or single tool call
- `2-3`: Multi-step reasoning (e.g., list databases → check health of each)
- `4+`: Complex workflow with multiple dependencies
- `10`: Maximum reached (safety limit)

Error response:
```json
{
  "success": false,
  "answer": null,
  "tool_calls": 0,
  "tools_used": [],
  "iterations": 0,
  "error": "Error message here",
  "warning": null
}
```

### 🎨 Features

- **Intelligent Routing**: Claude decides when to use MCP tools vs general knowledge
- **Permission Enforcement**: Users only access MCPs they're allowed to use
- **Tool Execution**: Automatically calls MCP tools and synthesizes results
- **Natural Language**: Ask questions naturally, no need to know tool names
- **Multi-Tool Support**: Can use multiple tools in a single conversation
- **Error Handling**: Graceful fallback when tools fail

### 🔐 User Permissions

| User | Role | Allowed MCPs | Allowed Domains |
|------|------|--------------|-----------------|
| avicoiot@gmail.com | admin | ALL (*) | ALL (*) |
| avi.cohen@shift4.com | super_admin | ALL (*) | ALL (*) |
| dba@company.com | dba | github_mcp, database_mcp | database_help, sql_help, general_knowledge |
| developer@company.com | developer | github_mcp, database_mcp | python_help, code_review, database_help, general_knowledge |
| qa@company.com | qa | github_mcp | python_help, code_review, testing, general_knowledge |
| analyst@company.com | analyst | github_mcp | general_knowledge, data_analysis |
| default_user | read_only | github_mcp | general_knowledge, python_help, code_review |

**🔒 Analytics MCP Access:**
- **ADMIN ONLY** - Only admin role can access Analytics MCP tools
- Provides insights into: costs, performance, errors, user activity, tool usage, token efficiency
- Tracks all OMNI2 system usage via audit logs
- All other roles (developer, dba, qa, analyst, read_only) are explicitly denied access

### 🤖 AI Model

Currently using: **Claude 3.5 Haiku** (fast & cost-effective)

To switch models, edit `docker-compose.yml`:
- `claude-3-5-haiku-20241022` - Current (fastest, cheapest)
- `claude-sonnet-4-5-20250929` - Better quality (Claude 4.5 Sonnet)
- `claude-opus-4-5-20251101` - Best quality (Claude 4.5 Opus, slower)

After changing: `docker compose up -d --force-recreate omni2`

---

## 🧪 Quick Copy-Paste Test Prompts for Database MCP

### Test 1: Database Health Check
```json
{"user_id": "avi.cohen@shift4.com", "message": "Check the health of transformer_master database"}
```
**Expected tool:** `database_mcp__get_database_health`

### Test 2: Top Slow Queries
```json
{"user_id": "avi.cohen@shift4.com", "message": "Show me the top 10 slowest queries"}
```
**Expected tool:** `database_mcp__get_top_queries`

### Test 3: Active Sessions
```json
{"user_id": "avi.cohen@shift4.com", "message": "Show me current active database sessions"}
```
**Expected tool:** `database_mcp__get_session_info`

### Test 4: Query Analysis
```json
{"user_id": "avi.cohen@shift4.com", "message": "Analyze this query: SELECT * FROM users WHERE status = 'active'"}
```
**Expected tool:** `database_mcp__analyze_query` or `database_mcp__analyze_oracle_query`

### Test 5: Buffer Cache Hit Ratio
```json
{"user_id": "avi.cohen@shift4.com", "message": "What's the buffer cache hit ratio?"}
```
**Expected tool:** `database_mcp__get_database_health` (includes buffer cache stats)

### Test 6: Wait Events
```json
{"user_id": "avi.cohen@shift4.com", "message": "Show me wait events and blocking sessions"}
```
**Expected tool:** `database_mcp__get_wait_events` or similar

### Test 7: List All Available DB Tools
```json
{"user_id": "avi.cohen@shift4.com", "message": "What database monitoring tools are available?"}
```
**Expected:** Lists all database_mcp tools (no tool call, just describes them)

### Test 8: GitHub + Database Combined
```json
{"user_id": "avi.cohen@shift4.com", "message": "Search GitHub for database performance tools and check my database health"}
```
**Expected tools:** Multiple calls - `github_mcp__search_repositories` + `database_mcp__get_database_health`

---

## 📊 Analytics MCP - System Monitoring & Insights (ADMIN ONLY)

### Overview
The Analytics MCP provides comprehensive insights into OMNI2 usage, costs, performance, and errors. **Strictly limited to admin users only** for security and privacy.

### 🔒 Security Model
- **Access:** Admin role ONLY (avicoiot@gmail.com)
- **Enforcement:** Role-based restrictions in mcps.yaml
- **Database:** Read-only PostgreSQL connection (no write access)
- **Rate Limit:** 30 requests/minute
- **Tags:** `internal`, `analytics`, `admin-only`, `omni2`

### 📈 Available Analytics Tools (11 Total)

#### 1️⃣ Cost & Budget (2 Tools)

**get_cost_summary**
- Total costs with grouping options (by user, date, or MCP)
- Average cost per query
- Token usage breakdown (input/output/cached)
- Time periods: today, week, month, all

**get_top_expensive_queries**
- Identifies highest cost queries
- Shows user, message, iterations, tool calls
- Includes token usage and duration
- Helps identify cost optimization opportunities

#### 2️⃣ Performance Metrics (2 Tools)

**get_slow_queries**
- Queries exceeding duration threshold (default 5000ms)
- Helps identify performance bottlenecks
- Shows iterations, tool calls, and duration
- Filterable by time period

**get_iteration_analysis**
- Tracks queries with high iteration counts
- Default threshold: 5+ iterations
- Indicates complex multi-step workflows
- Helps optimize agentic loop efficiency

#### 3️⃣ Error Analysis (2 Tools)

**get_error_summary**
- Error rates by MCP, tool, or time period
- Success vs failure statistics
- Identifies problematic tools/MCPs
- Filterable by MCP name and tool name

**get_failed_queries**
- Recent failed queries with full details
- Shows error messages and context
- User and MCP information included
- Helps troubleshoot recurring issues

#### 4️⃣ User Activity (1 Tool)

**get_active_users**
- User engagement metrics by time period
- Query counts, error rates, avg duration
- Filterable by role (admin, developer, dba, etc.)
- Identifies power users and usage patterns

#### 5️⃣ Tool & MCP Usage (2 Tools)

**get_tool_popularity**
- Most and least used tools
- Success rates per tool
- Average execution time
- Helps prioritize tool improvements

**get_mcp_health_summary**
- Success rates per MCP server
- Total queries handled by each MCP
- Identifies unreliable MCPs
- Overall system health indicator

#### 6️⃣ Token Efficiency (2 Tools)

**get_token_usage**
- Input vs output token breakdown
- Cached tokens (90% cost savings)
- Filterable by user and time period
- Cost optimization insights

**get_cache_hit_rate**
- Prompt caching effectiveness
- Percentage of cached vs uncached queries
- Shows cost savings from caching
- Helps validate caching strategy

### 🧪 Quick Test Commands for Analytics MCP

**Test 1: Cost Summary**
```json
{"user_id": "avicoiot@gmail.com", "message": "Show me cost summary for today"}
```
**Expected tool:** `omni2_analytics_mcp__get_cost_summary`

**Test 2: Expensive Queries**
```json
{"user_id": "avicoiot@gmail.com", "message": "What are the top 3 most expensive queries?"}
```
**Expected tool:** `omni2_analytics_mcp__get_top_expensive_queries`

**Test 3: Performance Issues**
```json
{"user_id": "avicoiot@gmail.com", "message": "Show me slow queries from this week"}
```
**Expected tool:** `omni2_analytics_mcp__get_slow_queries`

**Test 4: Error Rates**
```json
{"user_id": "avicoiot@gmail.com", "message": "What's the error rate by MCP?"}
```
**Expected tool:** `omni2_analytics_mcp__get_error_summary`

**Test 5: User Activity**
```json
{"user_id": "avicoiot@gmail.com", "message": "Who are the most active users?"}
```
**Expected tool:** `omni2_analytics_mcp__get_active_users`

**Test 6: Tool Popularity**
```json
{"user_id": "avicoiot@gmail.com", "message": "Which tools are used most frequently?"}
```
**Expected tool:** `omni2_analytics_mcp__get_tool_popularity`

**Test 7: MCP Health**
```json
{"user_id": "avicoiot@gmail.com", "message": "Show me MCP health summary"}
```
**Expected tool:** `omni2_analytics_mcp__get_mcp_health_summary`

**Test 8: Token Usage**
```json
{"user_id": "avicoiot@gmail.com", "message": "Show me token usage for today"}
```
**Expected tool:** `omni2_analytics_mcp__get_token_usage`

**Test 9: Cache Efficiency**
```json
{"user_id": "avicoiot@gmail.com", "message": "What's the cache hit rate?"}
```
**Expected tool:** `omni2_analytics_mcp__get_cache_hit_rate`

**Test 10: Multi-Tool Analytics**
```json
{"user_id": "avicoiot@gmail.com", "message": "Show me top expensive queries and most active users"}
```
**Expected tools:** Multiple analytics tools in agentic loop

**Test 11: Access Denied (Non-Admin)**
```json
{"user_id": "developer@company.com", "message": "Show me cost summary"}
```
**Expected:** No analytics tools available, LLM explains access denied

### 💡 Analytics Use Cases

1. **Cost Tracking** - Monitor LLM API costs by user, MCP, or time period
2. **Performance Optimization** - Identify slow queries and bottlenecks
3. **Error Detection** - Track failure rates and problematic tools
4. **Capacity Planning** - Understand usage patterns and peak times
5. **Tool ROI** - Identify underutilized or overused tools
6. **User Insights** - See which teams use which features
7. **Cache Effectiveness** - Validate prompt caching savings
8. **SLA Monitoring** - Track response times and reliability
9. **Trend Analysis** - Compare metrics across time periods
10. **Security Auditing** - Review who accessed what and when

### 🎯 Analytics MCP Architecture

```
Admin User → OMNI2 → Analytics MCP → PostgreSQL (read-only)
                          ↓
                  audit_logs table
                  (all queries tracked)
```

- **Port:** 8302
- **Database:** Same PostgreSQL as OMNI2 (read-only connection)
- **Connection Pool:** 2-5 connections
- **Auto-Discovery:** Enabled (hot reload for development)
- **Output Format:** Markdown-formatted tables and summaries

---

## 🧪 Quick Copy-Paste Test Prompts for Database MCP

### Test 1: Database Health Check
```json
{"user_id": "avi.cohen@shift4.com", "message": "Check the health of transformer_master database"}
```
**Expected tool:** `database_mcp__get_database_health`

### Test 2: Top Slow Queries
```json
{"user_id": "avi.cohen@shift4.com", "message": "Show me the top 10 slowest queries"}
```
**Expected tool:** `database_mcp__get_top_queries`

### Test 3: Active Sessions
```json
{"user_id": "avi.cohen@shift4.com", "message": "Show me current active database sessions"}
```
**Expected tool:** `database_mcp__get_session_info`

### Test 4: Query Analysis
```json
{"user_id": "avi.cohen@shift4.com", "message": "Analyze this query: SELECT * FROM users WHERE status = 'active'"}
```
**Expected tool:** `database_mcp__analyze_query` or `database_mcp__analyze_oracle_query`

### Test 5: Buffer Cache Hit Ratio
```json
{"user_id": "avi.cohen@shift4.com", "message": "What's the buffer cache hit ratio?"}
```
**Expected tool:** `database_mcp__get_database_health` (includes buffer cache stats)

### Test 6: Wait Events
```json
{"user_id": "avi.cohen@shift4.com", "message": "Show me wait events and blocking sessions"}
```
**Expected tool:** `database_mcp__get_wait_events` or similar

### Test 7: List All Available DB Tools
```json
{"user_id": "avi.cohen@shift4.com", "message": "What database monitoring tools are available?"}
```
**Expected:** Lists all database_mcp tools (no tool call, just describes them)

### Test 8: GitHub + Database Combined
```json
{"user_id": "avi.cohen@shift4.com", "message": "Search GitHub for database performance tools and check my database health"}
```
**Expected tools:** Multiple calls - `github_mcp__search_repositories` + `database_mcp__get_database_health`

---

## 🚀 Quick Testing Tips
