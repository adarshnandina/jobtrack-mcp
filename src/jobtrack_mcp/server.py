from mcp.server.mcpserver import MCPServer

# Create the MCP server
mcp = MCPServer("jobtrack")


@mcp.tool()
def greet(name: str = "there") -> str:
    """
    Greet a user by their name.
    
    Args:
        name: name of the person to greet.

    Returns:
        A personalized greeting.
    """
    return f"Hello, {name}! Welcome to Jobtrack MCP."


def main() -> None:
    """Start the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()