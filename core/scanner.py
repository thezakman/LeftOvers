"""
Main implementation of the LeftOvers scanner.
"""

import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any, Set
import urllib.parse

from core.config import (
    VERSION, DEFAULT_TIMEOUT, DEFAULT_THREADS, DEFAULT_EXTENSIONS, 
    DEFAULT_BACKUP_WORDS, DEFAULT_HEADERS, USER_AGENTS
)
from core.result import ScanResult
from core.detection import check_false_positive
from utils.logger import logger, setup_logger
from utils.console import (
    console, print_banner, print_info_panel, 
    create_progress_bar, format_and_print_result, create_url_list_progress
)
from utils.file_utils import load_url_list
from utils.http_utils import HttpClient
from utils.url_utils import generate_test_urls

class LeftOver:
    """Main scanner for finding leftover files on web servers."""
    
    def __init__(self, 
                 extensions: List[str] = None, 
                 timeout: int = DEFAULT_TIMEOUT,
                 threads: int = DEFAULT_THREADS,
                 headers: Dict[str, str] = None,
                 verify_ssl: bool = True,
                 use_color: bool = True,
                 verbose: bool = False,
                 silent: bool = False,
                 output_file: str = None,
                 status_filter: Set[int] = None,
                 min_content_length: int = None,
                 max_content_length: int = None,
                 rotate_user_agent: bool = False,
                 test_index: bool = False,
                 content_ignore: List[str] = None):
        """Initialize the scanner with the provided settings."""
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.timeout = timeout
        self.max_workers = threads
        self.headers = headers or DEFAULT_HEADERS.copy()
        self.verify_ssl = verify_ssl
        self.use_color = use_color
        self.verbose = verbose
        self.silent = silent
        self.output_file = output_file
        self.results = []
        self.rotate_user_agent = rotate_user_agent
        self.test_index = test_index
        
        # Brute force settings (default empty, set by CLI)
        self.brute_mode = False
        self.backup_words = []
        
        # Filters
        self.status_filter = status_filter
        self.min_content_length = min_content_length
        self.max_content_length = max_content_length
        self.content_ignore = content_ignore or []
        
        # Output settings
        self.output_file = output_file
        self.output_per_url = False  # New option
        
        # Set logging level based on verbose and silent flags
        global logger
        logger = setup_logger(verbose, silent)
        
        # HTTP client for requests
        self.http_client = HttpClient(
            headers=self.headers,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
            rotate_user_agent=self.rotate_user_agent
        )
        
        # For false positive detection
        self.error_fingerprints = {}
        self.baseline_responses = {}
        self._size_frequency = {}
        self._main_page = None
        
        # For storing global sanity check results
        self._global_sanity_check_results = {}
        
        # Set to track already tested URLs to avoid duplications
        self.tested_urls = set()
        
        # Set to track found URLs for result deduplication
        self.found_urls = set()

    def print_banner(self):
        """Display the ASCII banner."""
        if self.silent:
            return
            
        print_banner(self.use_color, self.silent)

        info_text = f"Version: {VERSION} | Threads: {self.max_workers} | Extensions: {len(self.extensions)}"

        # Add brute force info if enabled
        if self.brute_mode:
            info_text += f" | Brute Force: Enabled ({len(self.backup_words)} words)"

        print_info_panel(info_text, self.use_color)
    
    def test_url(self, base_url: str, extension: str, test_type: str) -> Optional[ScanResult]:
        """Test a single URL with a given extension."""
        # Check if we're testing only a domain or a specific path
        is_domain_only = base_url.rstrip('/').count('/') <= 2  # Ex: https://example.com
        
        if is_domain_only and self.test_index:
            # If domain and test_index flag is enabled, test index.{extension}
            full_url = f"{base_url.rstrip('/')}/index.{extension}"
        else:
            # Otherwise, add the extension to the end of the URL normally
            full_url = f"{base_url}.{extension}"
        
        # Check if this URL has already been tested to avoid duplications
        if full_url in self.tested_urls:
            return None
            
        # Add to the list of tested URLs
        self.tested_urls.add(full_url)
        
        try:
            result = self.http_client.get(full_url)
            
            if not result["success"]:
                return None
                
            response = result["response"]
            response_time = result["time"]
            
            scan_result = ScanResult(
                url=full_url,
                status_code=response.status_code,
                content_type=response.headers.get('Content-Type', 'N/A'),
                content_length=len(response.content) if response.content else 0,
                response_time=response_time,
                test_type=test_type,
                extension=extension
            )
            
            # Check for false positives
            is_false_positive, reason = check_false_positive(
                scan_result, 
                response.content, 
                self.baseline_responses,
                self._main_page,
                self._size_frequency
            )
            scan_result.false_positive = is_false_positive
            scan_result.false_positive_reason = reason
            
            # Apply status code filters
            if self.status_filter and scan_result.status_code not in self.status_filter:
                return None
                
            # Apply content length filters
            if (self.min_content_length is not None and scan_result.content_length < self.min_content_length) or \
               (self.max_content_length is not None and scan_result.content_length > self.max_content_length):
                return None
                
            # Apply content type filters
            if any(ignore in scan_result.content_type for ignore in self.content_ignore):
                return None
                
            # Check if this URL has already been found previously
            if scan_result.url in self.found_urls:
                return None  # URL already reported, ignore this result
                
            # Add to the list of found URLs
            self.found_urls.add(scan_result.url)
            
            self.results.append(scan_result)
            return scan_result
            
        except Exception as e:
            if self.verbose:
                logger.debug(f"Error testing URL {full_url}: {str(e)}")
            return None
    
    def process_url(self, target_url: str):
        """Process a URL, testing all extensions on all derived targets."""
        # Sempre mostrar informações do alvo, mesmo em modo silencioso
        if self.use_color:
            console.rule(f"[bold blue]Target: {target_url}[/bold blue]", style="blue")
        else:
            title = f"Target: {target_url}"
            print("\n" + "-" * len(title))
            print(title)
            print("-" * len(title))
        
        # Debug: Verificar segmentos da URL antes de processá-la
        if self.verbose:
            from utils.debug_utils import debug_url_segments
            debug_url_segments(target_url)
        
        # Reset size tracker for this target
        self._size_frequency = {}
        
        # Generate base URLs to test
        test_urls, self._main_page, self.baseline_responses = generate_test_urls(
            self.http_client, 
            target_url,
            self.brute_mode, 
            self.backup_words,
            self.verbose
        )
        
        if not test_urls:
            return
        
        # Create a progress bar to display status
        total_tests = len(test_urls) * len(self.extensions)
        
        # Sempre usar barra de progresso, mesmo em modo silencioso
        progress, task = create_progress_bar(total_tests, self.use_color)
        with progress:
            # For each base URL, test all extensions
            for base_url, test_type in test_urls:
                # Sempre mostrar o que está sendo testado, mesmo em modo silencioso
                if self.use_color:
                    # Obter as informações corretas para exibição baseadas no tipo de teste
                    url_display = self._get_display_url(base_url, test_type)
                    console.print(f"[bold yellow]Testing {test_type}:[/bold yellow] {url_display}")
                else:
                    # Versão sem cor com a mesma lógica
                    url_display = self._get_display_url(base_url, test_type)
                    print(f"Testing {test_type}: {url_display}")
                
                # Use a thread pool to test all extensions in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_ext = {
                        executor.submit(self.test_url, base_url, ext, test_type): ext 
                        for ext in self.extensions
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_ext):
                        progress.update(task, advance=1)
                        result = future.result()
                        if result:
                            format_and_print_result(console, result, self.use_color, self.verbose, self.silent)
                
                # Add a blank line after each test group
                if self.use_color:
                    console.print()
                else:
                    print()
    
    def _get_display_url(self, base_url: str, test_type: str) -> str:
        """
        Retorna a representação adequada da URL sendo testada com base no tipo de teste.
        """
        parsed = urllib.parse.urlparse(base_url)
        
        if test_type == "Base URL":
            # Para Base URL, mostrar o domínio completo
            return parsed.netloc
        
        elif test_type == "Full URL":
            # Para Full URL, mostrar domínio + caminho completo
            path = parsed.path.strip('/')
            if path:
                return f"{parsed.netloc}/{path}"
            return parsed.netloc
        
        elif test_type == "Path":
            # Para Path, mostrar apenas o caminho
            path = parsed.path.strip('/')
            if path:
                return f"/{path}"
            return "/"
        
        elif test_type.startswith("Segment"):
            # Extrair o número do segmento do tipo de teste
            try:
                segment_num = int(test_type.split(' ')[-1])
                
                # Extrair o caminho da URL e dividir em segmentos
                original_path = parsed.path.strip('/')
                
                if not original_path:
                    return ""
                
                # Verificar o conteúdo do caminho para depuração
                if self.verbose:
                    print(f"[DEBUG-DISPLAY] URL: {base_url}, Path: {original_path}")
                
                # O problema aqui é que estamos obtendo o caminho da URL base, que é
                # um segmento único (como 'Painel', 'Account' ou 'Login') e não o caminho completo
                # Vamos obter o caminho original da URL completa
                
                # Reconstruir o caminho completo a partir do tipo de segmento
                # Assumindo que a URL original foi armazenada em algum lugar ou pode ser derivada
                
                # A solução mais simples é verificar a última parte do base_url
                # para identificar qual segmento estamos testando
                base_path = original_path  # Este é o caminho no base_url (ex: 'Painel')
                
                if self.verbose:
                    print(f"[DEBUG-DISPLAY] Caminho base: {base_path}")
                
                # Obter o segmento correto da URL original completa
                # Para URLs como `/Painel/Account/Login`, quando testamos o Segment 2,
                # queremos retornar 'Account'
                
                # Neste caso, nosso segmento é simplesmente o próprio caminho base
                # já que estamos testando um segmento específico por vez
                return base_path
                
            except (ValueError, IndexError) as e:
                if self.verbose:
                    print(f"[DEBUG-DISPLAY] Erro ao processar segmento: {str(e)}")
                return ""
        
        elif test_type == "Subdomain":
            # Para Subdomain, mostrar apenas o subdomínio
            hostname = parsed.netloc
            # Remover porta se existir
            if ':' in hostname:
                hostname = hostname.split(':')[0]
                
            parts = hostname.split('.')
            # Se tiver pelo menos 3 partes (subdominio.dominio.tld) ou
            # se tiver pelo menos 2 partes mas não for um TLD composto (como .com.br)
            if len(parts) >= 3 or (len(parts) == 2 and not any(hostname.endswith(f".{tld}") for tld in ['co.uk', 'com.br', 'com.au', 'org.br', 'net.br', 'com.vc'])):
                return parts[0]
            return "[nenhum]"
        
        elif test_type == "Domain":
            # Para Domain, mostrar apenas o domínio de segundo nível (sem TLD)
            hostname = parsed.netloc
            # Remover porta se existir
            if ':' in hostname:
                hostname = hostname.split(':')[0]
                
            parts = hostname.split('.')
            
            # Identificar TLDs compostos comuns
            tlds_compostos = ['co.uk', 'com.br', 'com.au', 'org.br', 'net.br', 'com.vc', 'edu.br', 'gov.br']
            
            # Verificar caso especial para domínios com TLDs compostos
            for tld in tlds_compostos:
                if hostname.endswith(f".{tld}"):
                    # Se for um domínio com subdomínio e TLD composto: sub.dominio.com.br
                    if len(parts) > 3:
                        return parts[-3]  # Retorna 'dominio'
                    # Se for um domínio normal com TLD composto: dominio.com.br
                    else:
                        return parts[0]  # Retorna 'dominio'
            
            # Para domínios normais não compostos
            if len(parts) >= 3:  # sub.dominio.com
                return parts[-2]  # Retorna 'dominio'
            elif len(parts) == 2:  # dominio.com
                return parts[0]  # Retorna 'dominio'
            
            return hostname
            
        elif test_type == "Domain Name":
            # Para Domain Name, mostrar o domínio completo com TLD (sem subdomínio)
            hostname = parsed.netloc
            # Remover porta se existir
            if ':' in hostname:
                hostname = hostname.split(':')[0]
                
            parts = hostname.split('.')
            
            # Identificar TLDs compostos comuns
            tlds_compostos = ['co.uk', 'com.br', 'com.au', 'org.br', 'net.br', 'com.vc', 'edu.br', 'gov.br']
            
            # Verificar caso especial para domínios com TLDs compostos
            for tld in tlds_compostos:
                if hostname.endswith(f".{tld}"):
                    # Se for um domínio com subdomínio e TLD composto: sub.dominio.com.br
                    if len(parts) > 3:
                        return f"{parts[-3]}.{tld}"  # Retorna 'dominio.com.br'
                    # Se for um domínio normal com TLD composto: dominio.com.br
                    else:
                        return hostname  # Retorna 'dominio.com.br'
            
            # Para domínios normais não compostos
            if len(parts) >= 3:  # sub.dominio.com
                return f"{parts[-2]}.{parts[-1]}"  # Retorna 'dominio.com'
            elif len(parts) == 2:  # dominio.com
                return hostname  # Retorna 'dominio.com'
            
            return hostname
    
    def process_url_list(self, url_list_file: str):
        """Process multiple URLs from a file."""
        urls = load_url_list(url_list_file)
        if not urls:
            return
        
        total_urls = len(urls)
        
        # Exibir informações iniciais (mesmo em modo silencioso)
        if self.use_color:
            console.print(f"[bold cyan]Processando {total_urls} URLs da lista: {url_list_file}[/bold cyan]")
        else:
            print(f"Processando {total_urls} URLs da lista: {url_list_file}")
        
        # Usar uma única barra de progresso para todas as URLs (mesmo em modo silencioso)
        progress, task_id = create_url_list_progress(total_urls, self.use_color)
        
        with progress:
            for i, url in enumerate(urls, 1):
                # Atualizar descrição da barra de progresso com URL atual
                progress.update(task_id, description=f"[cyan]URL {i}/{total_urls}: {url}")
                
                # Limpar resultados anteriores se estivermos gerando um arquivo por URL
                if self.output_per_url:
                    self.results = []
                
                # Processar a URL atual (com display desativado para evitar conflito)
                self._process_url_without_progress(url)
                
                # Exportar resultados para esta URL específica se necessário
                if self.output_per_url and self.output_file:
                    from urllib.parse import urlparse
                    from utils.file_utils import export_results
                    
                    # Criar nome de arquivo baseado na URL
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace(':', '_')
                    path = parsed.path.replace('/', '_').strip('_')
                    
                    if path:
                        filename = f"{self.output_file.split('.')[0]}_{domain}_{path}.json"
                    else:
                        filename = f"{self.output_file.split('.')[0]}_{domain}.json"
                    
                    export_results(self.results, filename)
                    
                    if not self.silent:
                        logger.info(f"Resultados para {url} exportados para {filename}")
                
                # Avançar a barra de progresso
                progress.update(task_id, advance=1)

    def _process_url_without_progress(self, target_url: str):
        """Process a URL without using progress bars (for use within URL list processing)."""
        # Sempre mostrar informações do alvo, mesmo em modo silencioso
        if self.use_color:
            console.rule(f"[bold blue]Target: {target_url}[/bold blue]", style="blue")
        else:
            title = f"Target: {target_url}"
            print("\n" + "-" * len(title))
            print(title)
            print("-" * len(title))
        
        # Debug: Verificar segmentos da URL antes de processá-la
        if self.verbose:
            from utils.debug_utils import debug_url_segments
            debug_url_segments(target_url)
        
        # Reset size tracker for this target
        self._size_frequency = {}
        
        # Generate base URLs to test
        test_urls, self._main_page, self.baseline_responses = generate_test_urls(
            self.http_client, 
            target_url,
            self.brute_mode, 
            self.backup_words,
            self.verbose
        )
        
        if not test_urls:
            return
        
        # Sem barra de progresso, processamos diretamente
        for base_url, test_type in test_urls:
            # Sempre mostrar o que está sendo testado, mesmo em modo silencioso
            if self.use_color:
                url_display = self._get_display_url(base_url, test_type)
                console.print(f"[bold yellow]Testing {test_type}:[/bold yellow] {url_display}")
            else:
                url_display = self._get_display_url(base_url, test_type)
                print(f"Testing {test_type}: {url_display}")
            
            # Testar todas as extensões em paralelo
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_ext = {
                    executor.submit(self.test_url, base_url, ext, test_type): ext 
                    for ext in self.extensions
                }
                
                for future in concurrent.futures.as_completed(future_to_ext):
                    result = future.result()
                    if result:
                        format_and_print_result(console, result, self.use_color, self.verbose, self.silent)
            
            # Sempre adicionar uma linha em branco após cada grupo de teste
            if self.use_color:
                console.print()
            else:
                print()

    def print_summary(self):
        """Print a summary of the results found."""
        from utils.report import generate_summary_report
        
        if not self.results or self.silent:
            return
            
        generate_summary_report(self.results, console, self.use_color, self.verbose)
    
    def run(self):
        """Run the scanner with current settings."""
        # Clear tracking sets when starting a new scan
        self.tested_urls.clear()
        self.found_urls.clear()
        
        # ...existing code for running the scan...
        
        # When displaying results, duplicates will already have been filtered
        # ...existing code...
