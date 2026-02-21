import asyncio
import httpx
import json

async def check_metadata():
    url = "http://localhost:8350/mcp"
    headers = {
        "Accept": "text/event-stream, application/json",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Initialize
        r = await client.post(url, headers=headers, json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        })
        
        data = json.loads(r.text.split('data: ')[1].split('\r\n')[0])
        print(json.dumps(data, indent=2))

asyncio.run(check_metadata())
