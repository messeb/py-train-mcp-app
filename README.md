# py-train-mcp-app

MCP app uses the bahn API to query live train departures directly from your AI assistant.

![Train MCP App](./docs/train-mcp-app-screenshot.png)

## MCP App

This is a [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server. MCP lets AI assistants like Claude call external tools and display custom UI, the [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) — so instead of reading departure data as plain text, you get an interactive board rendered right inside Claude Desktop.

When you ask Claude about departures, the MCP server fetches live data and shows it in an embedded form. You can then change the station or filters directly in that form and hit **Search** — no need to type another message to Claude.

## Departures

Ask Claude for the departure board at any station:

```
Show me the next departures at Deutz
```

```
Show me the next departures at Keupstr.
```

The departure board opens as an embedded view. Click any train row to see all stops for that journey with real-time delay information.

## Run it

### uv

```bash
git clone https://github.com/messeb/py-train-mcp-app ~/mcp-servers/py-train-mcp-app
cd ~/mcp-servers/py-train-mcp-app
uv sync
```

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "train-mcp-app": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/absolute/path/to/py-train-mcp-app",
        "server.py",
        "--stdio"
      ]
    }
  }
}
```

Replace `/absolute/path/to/py-train-mcp-app` with the actual clone path.

### Docker

```bash
git clone https://github.com/messeb/py-train-mcp-app
cd py-train-mcp-app
docker build -t py-train-mcp-app .
```

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "train-mcp-app": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "py-train-mcp-app"
      ]
    }
  }
}
```

Restart Claude Desktop. Claude will start the container automatically on launch.
