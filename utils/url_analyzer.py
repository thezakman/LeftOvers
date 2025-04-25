#!/usr/bin/env python3
"""
Ferramenta de análise de URL para debugar problemas de segmentação.
"""

import sys
import urllib.parse

def analyze_url(url):
    """Analisa uma URL e mostra todos os seus componentes."""
    print(f"\nAnalisando URL: {url}")
    
    # Parsear a URL
    parsed = urllib.parse.urlparse(url)
    
    # Mostrar componentes básicos
    print("\nComponentes básicos:")
    print(f"Scheme: {parsed.scheme}")
    print(f"Netloc: {parsed.netloc}")
    print(f"Path: {parsed.path}")
    print(f"Params: {parsed.params}")
    print(f"Query: {parsed.query}")
    print(f"Fragment: {parsed.fragment}")
    
    # Analisar o netloc (domínio)
    print("\nAnálise do domínio:")
    netloc = parsed.netloc
    parts = netloc.split('.')
    
    print(f"Partes do domínio: {parts}")
    
    if len(parts) >= 3:
        print(f"Possível subdomínio: {parts[0]}")
        print(f"Domínio principal: {'.'.join(parts[1:])}")
    else:
        print(f"Domínio sem subdomínio: {netloc}")
    
    # Analisar o caminho
    print("\nAnálise do caminho:")
    path = parsed.path.strip('/')
    
    if not path:
        print("Caminho vazio")
    else:
        segments = path.split('/')
        print(f"Número de segmentos: {len(segments)}")
        
        for i, segment in enumerate(segments, 1):
            print(f"Segment {i}: '{segment}'")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python url_analyzer.py URL")
        sys.exit(1)
    
    analyze_url(sys.argv[1])
