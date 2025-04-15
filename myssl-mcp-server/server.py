#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# author: Hsiang Chen (hchen90)
# date: 2025-04-15

import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server
import time, hmac, hashlib, requests
from config import load_config, save_config

app = Server("myssl-mcp-server")


def test_openapi_fast_analyze(partnerId, secretKey, domain):
    timestamp = int(time.time())
    expirt = 200
    param = (
        "partnerId="
        + partnerId
        + "&timestamp="
        + str(timestamp)
        + "&expire="
        + str(expirt)
        + "&domain="
        + domain
    )
    print(param)
    signature = hmac.new(
        bytes(secretKey, encoding="utf8"), bytes(param, encoding="utf8"), hashlib.sha1
    ).hexdigest()
    params = {
        "partnerId": partnerId,
        "timestamp": timestamp,
        "expire": expirt,
        "signature": signature,
        "domain": domain,
    }
    response = requests.get(
        "https://api.myssl.com/eeapi/v1/fast_analyze",
        params=params,
        timeout=300,
    )
    response.encoding = "utf-8"
    if response.status_code != 200:
        print("Error:", response.status_code)
        return None
    print("Response:", response.text)
    return response.content


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="fast_analyze",
            description="A tool that scans website by domain (fast analyze).",
            inputSchema={
                "type": "object",
                "required": [
                    "domain",
                ],
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The website domain to use.",
                    },
                },
            },
        ),
        types.Tool(
            name="save_config",
            description="Save the partnerId and secretKey to the config.",
            inputSchema={
                "type": "object",
                "required": [
                    "partnerId",
                    "secretKey",
                ],
                "properties": {
                    "partnerId": {
                        "type": "string",
                        "description": "The partnerId to save.",
                    },
                    "secretKey": {
                        "type": "string",
                        "description": "The secretKey to save.",
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, args: dict) -> list[types.TextContent]:
    if name == "fast_analyze":  # fast_analyze
        config = load_config()

        partnerId = config.get("partnerId")
        secretKey = config.get("secretKey")

        # Check if partnerId and secretKey are provided
        if not partnerId or not secretKey:
            raise ValueError("partnerId and secretKey are required.")

        # Save the provided partnerId and secretKey to the config
        config["partnerId"] = partnerId
        config["secretKey"] = secretKey
        save_config(config)

        domain = args.get("domain", "myssl.com")
        content = test_openapi_fast_analyze(
            partnerId=partnerId,
            secretKey=secretKey,
            domain=domain,
        )
        return [types.TextContent(type="text", text=content.decode("utf-8"))]
    elif name == "save_config":  # save_config
        partnerId = args.get("partnerId")
        secretKey = args.get("secretKey")

        # Check if partnerId and secretKey are provided
        if not partnerId or not secretKey:
            raise ValueError("partnerId and secretKey are required.")

        # Save the provided partnerId and secretKey to the config
        config = load_config()
        config["partnerId"] = partnerId
        config["secretKey"] = secretKey
        save_config(config)
        return [types.TextContent(type="text", text="Config saved successfully.")]
    else:
        raise ValueError(f"Unknown tool: {name}")


@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> int:
    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                options = app.create_initialization_options()
                if isinstance(options, dict):
                    options.pop("transport", None)  # Remove transport key if it exists
                await app.run(streams[0], streams[1], options)

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        import uvicorn

        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as streams:
                options = app.create_initialization_options()
                if isinstance(options, dict):
                    options.pop("transport", None)  # Remove transport key if it exists
                await app.run(streams[0], streams[1], options)

        anyio.run(arun)

    return 0


if __name__ == "__main__":
    main()
