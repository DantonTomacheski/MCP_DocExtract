#!/usr/bin/env python3
"""
Cliente de teste para o servidor MCP do DocExtract AI.

Este script envia requisições de teste para o servidor MCP para demonstrar
seu funcionamento.
"""

import requests
import json
import sys


def make_mcp_request(tool_name, parameters):
    """Faz uma requisição MCP para o servidor."""
    url = "http://127.0.0.1:8000/api/mcp"
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": tool_name,
        "parameters": parameters
    }
    
    print(f"\n---- Enviando requisição para {tool_name} ----")
    print(f"Parâmetros: {json.dumps(parameters, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"\nStatus: {response.status_code}")
        if response.status_code == 200:
            print("Resposta:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Erro: {response.text}")
    except Exception as e:
        print(f"Erro ao conectar: {e}")


def main():
    """Função principal que envia várias requisições de teste."""
    print("Cliente de teste para o servidor MCP DocExtract AI")
    print("=================================================\n")
    
    # Testar detect_framework
    make_mcp_request("detect_framework", {
        "url": "https://docs.python.org"
    })
    
    # Testar extract_document
    make_mcp_request("extract_document", {
        "url": "https://docs.python.org",
        "mode": "auto",
        "max_depth": 2
    })
    
    # Testar process_content
    make_mcp_request("process_content", {
        "content": "<div><h1>Título</h1><p>Conteúdo de teste</p><div class='ads'>Anúncio</div></div>",
        "processing_mode": "clean"
    })
    
    print("\nTestes concluídos!")


if __name__ == "__main__":
    main()
