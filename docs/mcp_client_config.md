# MCP Client Configuration — Dojo MCP Server

## Endpoint

```
POST http://localhost:8070/mcp
```

Protocol: MCP 2025-03-26, Streamable HTTP transport (JSON-RPC 2.0)

## Authentication

| Header       | Value                                                               |
| ------------ | ------------------------------------------------------------------- |
| `X-Api-Key`  | Your configured API key (Settings → AI Assistant)                   |
| `X-Mcp-Role` | `admin`, `instructor`, or `kiosk` (optional, default: `instructor`) |

## Claude Desktop

Create/edit `~/.config/Claude/claude_desktop_config.json`:

### Option A — Direct HTTP (Claude Desktop 4.x+)

```json
{
  "mcpServers": {
    "dojo": {
      "url": "http://localhost:8070/mcp",
      "headers": {
        "X-Api-Key": "YOUR_API_KEY",
        "X-Mcp-Role": "admin"
      }
    }
  }
}
```

### Option B — Via mcp-remote proxy (older Claude Desktop)

```json
{
  "mcpServers": {
    "dojo": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-remote", "http://localhost:8070/mcp"],
      "env": {
        "MCP_HEADERS": "{\"X-Api-Key\": \"YOUR_API_KEY\", \"X-Mcp-Role\": \"admin\"}"
      }
    }
  }
}
```

## VS Code (Copilot MCP)

Add to `.vscode/settings.json`:

```json
{
  "mcp": {
    "servers": {
      "dojo": {
        "type": "http",
        "url": "http://localhost:8070/mcp",
        "headers": {
          "X-Api-Key": "YOUR_API_KEY",
          "X-Mcp-Role": "admin"
        }
      }
    }
  }
}
```

## Available Capabilities

| Capability | Count | Description                                                       |
| ---------- | ----- | ----------------------------------------------------------------- |
| Tools      | 48    | Auto-generated from intent schemas; role-filtered                 |
| Resources  | 3     | `dojo://schedule/today`, `dojo://members/active`, `dojo://agents` |

## Quick Verification

```bash
# Initialize handshake (no auth required)
curl -s -X POST http://localhost:8070/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# List tools (auth required)
curl -s -X POST http://localhost:8070/mcp \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# Call a tool
curl -s -X POST http://localhost:8070/mcp \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"schedule_today","arguments":{}}}'

# Read a resource
curl -s -X POST http://localhost:8070/mcp \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -d '{"jsonrpc":"2.0","id":4,"method":"resources/read","params":{"uri":"dojo://agents"}}'
```
