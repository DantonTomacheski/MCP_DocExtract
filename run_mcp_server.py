#!/usr/bin/env python3
"""
Script para iniciar o servidor MCP do DocExtract AI.

Este script inicializa e executa o servidor MCP que expõe as ferramentas
de extração de documentação via protocolo MCP.
"""

from src.server.mcp_server import MCPServer
from src.server.schemas.tools import mcp_tools

def main():
    """Iniciar o servidor MCP."""
    print("Iniciando servidor MCP para DocExtract AI...")
    print(f"Ferramentas MCP disponíveis:")
    
    # Listar todas as ferramentas disponíveis
    for i, tool in enumerate(mcp_tools, 1):
        print(f"{i}. {tool.name}: {tool.description.strip()}")
    
    print("\nConfigurando o servidor...")
    server = MCPServer(host="127.0.0.1", port=8000)
    
    print(f"Iniciando servidor em http://127.0.0.1:8000")
    print("Pressione CTRL+C para encerrar o servidor.")
    server.start()

if __name__ == "__main__":
    main()
