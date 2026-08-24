from app.mcp.server import mcp


app = mcp.streamable_http_app(json_response=True, stateless_http=True)
