# foxhire-mcp-server

MCP server that connects Claude Desktop to the [FoxHire.AI](https://foxhire.ai) job search pipeline. Paste a job posting and get AI-powered hiring manager discovery, contact research, and personalized outreach drafts — all from your AI assistant.

## How It Works

This is a local MCP server that acts as an authenticated client to the live FoxHire.AI API. Claude Desktop (or any MCP client) discovers and invokes the tools via stdio. AI operations — contact discovery, research, and email drafting — run server-side using Claude Sonnet with web search.

```
Claude Desktop  <-- MCP (stdio) -->  foxhire-mcp-server  <-- HTTPS -->  FoxHire.AI API (Fly.io)
                                          (local)                             |
                                                                        Claude Sonnet
                                                                        + Web Search
```

## Available Tools

| Tool | Description | Credits |
|------|-------------|---------|
| `list_jobs` | List all jobs in your pipeline with status | 0 |
| `parse_job_posting` | Parse a job URL or raw text into structured data | 0 |
| `discover_contacts` | Find hiring decision makers via AI web search | 1 |
| `research_contact` | Build a personalization brief with outreach angles | 1 |
| `draft_outreach_email` | Generate a personalized cold outreach email | 0 |

## Setup

### Prerequisites

- Python 3.10+
- A [FoxHire.AI](https://foxhire.ai) account with credits
- [Claude Desktop](https://claude.ai/download) or any MCP client

### Install

```bash
git clone https://github.com/dkalinchenko/foxhire-mcp-server.git
cd foxhire-mcp-server
cp .env.example .env
# Edit .env with your FoxHire credentials
```

### Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

**With uv (recommended):**

```json
{
  "mcpServers": {
    "foxhire": {
      "command": "uv",
      "args": ["run", "--with", "mcp", "--with", "httpx", "server.py"],
      "cwd": "/path/to/foxhire-mcp-server",
      "env": {
        "FOXHIRE_EMAIL": "your-email@example.com",
        "FOXHIRE_PASSWORD": "your-password",
        "FOXHIRE_API_URL": "https://foxhire.ai/api"
      }
    }
  }
}
```

**With plain Python:**

```json
{
  "mcpServers": {
    "foxhire": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/foxhire-mcp-server",
      "env": {
        "FOXHIRE_EMAIL": "your-email@example.com",
        "FOXHIRE_PASSWORD": "your-password",
        "FOXHIRE_API_URL": "https://foxhire.ai/api"
      }
    }
  }
}
```

If using plain Python, install dependencies first:

```bash
pip install mcp httpx
```

Restart Claude Desktop completely (quit and reopen) after editing the config.

## Example Usage

```
You: "Parse this job posting: https://jobs.lever.co/example/senior-product-manager"

Claude: Job saved! ID: 42
        Title: Senior Product Manager
        Company: ExampleCo
        Seniority Level: Senior
        Hiring Manager Persona: VP of Product

You: "Find the hiring contacts for job 42"

Claude: Found 2 contacts (Credits remaining: 8):
        [ID: 15] Jane Smith — VP of Product (Confidence: High) ★ SUGGESTED FIRST CONTACT
          LinkedIn: https://linkedin.com/in/janesmith
        [ID: 16] Tom Lee — Director of Product (Confidence: Medium)

You: "Research Jane Smith (contact 15)"

Claude: KEY FINDINGS:
          - Promoted to VP of Product in 2024 after leading the platform team
          - Previously at Stripe as Senior PM
          - Published on Lenny's Newsletter about product-led growth
        OUTREACH ANGLES:
          [Shared PLG background] (thematic)
            Both have deep product-led growth experience
          [Stripe career parallel] (career)
            Similar enterprise transition trajectory

You: "Draft an outreach email for contact 15 using the PLG angle"

Claude: SUBJECT: Product-led growth in enterprise — comparing notes

        Hi Jane, ...
```

## Tech Stack

- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) (`mcp`) — server framework with stdio transport
- [`httpx`](https://www.python-httpx.org/) — async HTTP client
- [FoxHire.AI API](https://foxhire.ai) — FastAPI backend on Fly.io
- Claude Sonnet with web search — powers all AI operations server-side

## License

MIT
