"""
Utilities for debugging LeftOvers scanner.
"""

import os
import urllib.parse
import sys
from typing import List, Tuple, Any

def debug_url_segments(url: str) -> None:
    """
    Analisa uma URL e imprime informações detalhadas sobre seus segmentos para depuração.
    """
    print(f"\n[DEBUG] Analisando URL: {url}")
    
    parsed = urllib.parse.urlparse(url)
    print(f"[DEBUG] Scheme: {parsed.scheme}")
    print(f"[DEBUG] Netloc: {parsed.netloc}")
    print(f"[DEBUG] Path: {parsed.path}")
    
    path = parsed.path.strip('/')
    if not path:
        print("[DEBUG] Caminho vazio, sem segmentos.")
        return
        
    segments = path.split('/')
    print(f"[DEBUG] Segmentos encontrados: {len(segments)}")
    
    for i, segment in enumerate(segments, 1):
        print(f"[DEBUG] Segment {i}: '{segment}'")

def debug_test_urls(test_urls: List[Tuple[str, str]]) -> None:
    """
    Imprime informações sobre as URLs que serão testadas.
    """
    print("\n[DEBUG] URLs que serão testadas:")
    for base_url, test_type in test_urls:
        parsed = urllib.parse.urlparse(base_url)
        path = parsed.path
        print(f"[DEBUG] Tipo: {test_type}, URL: {base_url}")
        
        if test_type.startswith("Segment") and path:
            path_clean = path.strip('/')
            if path_clean:
                segments = path_clean.split('/')
                segment_num = int(test_type.split(' ')[-1])
                if segment_num <= len(segments):
                    print(f"[DEBUG]   Segment {segment_num}: '{segments[segment_num-1]}'")
                else:
                    print(f"[DEBUG]   Segment {segment_num}: Não existe (total: {len(segments)})")

def debug_segment_display(base_url: str, segment_num: int) -> None:
    """
    Função específica para depurar a exibição de segmentos.
    """
    print(f"\n[DEBUG-SEGMENT] Analisando segmento {segment_num} da URL: {base_url}")
    
    parsed = urllib.parse.urlparse(base_url)
    path = parsed.path.strip('/')
    
    if not path:
        print("[DEBUG-SEGMENT] Caminho vazio, sem segmentos.")
        return
    
    segments = path.split('/')
    print(f"[DEBUG-SEGMENT] Segmentos encontrados: {len(segments)}")
    print(f"[DEBUG-SEGMENT] Lista de segmentos: {segments}")
    
    if 1 <= segment_num <= len(segments):
        print(f"[DEBUG-SEGMENT] Segment {segment_num}: '{segments[segment_num-1]}'")
    else:
        print(f"[DEBUG-SEGMENT] Segment {segment_num} não existe (total: {len(segments)})")

def debug_segment_url(url: str, test_type: str) -> None:
    """
    Analisa um URL específico para um tipo de teste e extrai informações de segmentos.
    """
    print(f"\n[DEBUG-SEGMENT-URL] Analisando URL para {test_type}: {url}")
    
    if not test_type.startswith("Segment"):
        print(f"[DEBUG-SEGMENT-URL] O tipo de teste '{test_type}' não é um segmento. Ignorando.")
        return
    
    try:
        segment_num = int(test_type.split(' ')[-1])
        
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            print("[DEBUG-SEGMENT-URL] Caminho vazio, sem segmentos para analisar.")
            return
        
        segments = path.split('/')
        print(f"[DEBUG-SEGMENT-URL] Número total de segmentos: {len(segments)}")
        print(f"[DEBUG-SEGMENT-URL] Lista completa de segmentos: {segments}")
        
        if 1 <= segment_num <= len(segments):
            segment = segments[segment_num - 1]
            print(f"[DEBUG-SEGMENT-URL] Segment {segment_num} é: '{segment}'")
        else:
            print(f"[DEBUG-SEGMENT-URL] Segment {segment_num} não existe. Total de segmentos: {len(segments)}")
    
    except Exception as e:
        print(f"[DEBUG-SEGMENT-URL] Erro na análise de segmento: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python debug_utils.py URL [numero_segmento]")
        sys.exit(1)
    
    url = sys.argv[1]
    debug_url_segments(url)
    
    if len(sys.argv) >= 3:
        try:
            segment_num = int(sys.argv[2])
            debug_segment_display(url, segment_num)
        except ValueError:
            print("[ERRO] O número do segmento deve ser um inteiro.")
