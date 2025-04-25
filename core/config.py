"""
Scanner-specific configurations and constants for the LeftOvers scanner.
"""

# Import global settings
from app_settings import VERSION, DEFAULT_TIMEOUT, DEFAULT_THREADS, MAX_FILE_SIZE_MB, DEFAULT_USER_AGENT, USER_AGENTS

# Default headers for HTTP requests
DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

# Default list of extensions to test
DEFAULT_EXTENSIONS = [
    # ─── Text / Config / Data ─────────────────────────
    "txt", "log", "log1", "json", "xml", "yaml", "yml", "csv",
    "properties", "plist", "config", "cfg", "ini", "conf", "env", "settings",
    "lock", "tmpfile", "test", "sample",

    # ─── Databases ─────────────────────────────────────
    "sql", "db", "sqlite", "sqlite3", "mdb", "accdb", "dump",

    # ─── Common Backups ────────────────────────────────
    "bak", "bak1", "old", "backup", "bkp", "copy", "copy1", "copy2",
    "save", "orig", "temp", "tmp", "dist", "new", "~",

    # ─── Archives / Compression ────────────────────────
    "zip", "tar", "tgz", "gz", "gzip", "bz2", "xz", "7z", "rar",
    "tar.gz", "tar.bz2",

    # ─── IDE / Editor Leftovers ────────────────────────
    "swp", "swo", "swn", "tmp~", "tmp.swp", "tmp.save", "sml", "autosave", "kate-swp",

    # ─── Web Files / Mapping ───────────────────────────
    "html", "htm", "js", "js.map", "json.map", "xml.map",
    "css", "scss", "sass", "map",

    # ─── Code / Web App Langs (w/ backup variants) ─────
    "php", "php~", "php.bak", "php.old", "php.save",
    "jsp", "jsp~", "jsp.bak", "jsp.old", "jsp.save",
    "asp", "asp~", "asp.bak", "asp.old", "asp.save",
    "aspx", "aspx.bak", "aspx.old",
    "rb", "rb~", "rb.bak", "rb.old",
    "py", "py~", "py.bak", "py.old", "py.save",
    "sh", "sh~", "sh.bak", "sh.old", "svc", "ash", "ashx"

    # ─── Versioning / Patch Artifacts ──────────────────
    "rej", "patch", "diff", "merge",

    # ─── Document / Office Formats ─────────────────────
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "pdf",
    "rtf", "md", "odt", "ods", "odp",

    # ─── Misc Executables / Images / Etc ───────────────
    "exe.bak", "dll.bak", "bin.bak", "img", "iso"
]

# Default list of common backup words/directories to test
DEFAULT_BACKUP_WORDS = [
    # ─── Backup Directories and Names ───────────────────
    "anterior", "antigo", "archive", "archived", "archives", "atual",
    "back", "backup", "bkp", "copia", "copy", "deletar", "dev",
    "devel", "development", "guardar", "hml", "historical", "history",
    "homolog", "homologacao", "latest", "lixo", "log", "logs",
    "new", "novo", "old", "old_version", "orig", "original", "prd",
    "prod", "production", "rascunho", "release", "reserva", "salvo",
    "seguranca", "stable", "staging", "temp", "temporario", "tmp",
    "versao", "producao",

    # ─── Web Related ────────────────────────────────────
    "backend", "conteudo", "deploy", "frontend", "htdocs", "html",
    "httpdocs", "inetpub", "pagina", "portal", "public", "public_html",
    "publicacao", "site", "sistema", "static", "web", "webpage",
    "webroot", "website", "www", "www-data", "hospedagem",

    # ─── Version Control ─────────────────────────────────
    ".git", ".svn", "bk", "cvs", "git", "hg", "svn",

    # ─── Dates and Versions ──────────────────────────────
    "1.0", "2.0", "2020", "2021", "2022", "2023", "2024", "2025",
    "apr", "aug", "dec", "feb", "jan", "jul", "jun", "mar",
    "may", "nov", "oct", "sep", "v1", "v2", "v3",
    "abril", "agosto", "dezembro", "fevereiro", "janeiro", "julho",
    "junho", "maio", "marco", "novembro", "outubro", "setembro",

    # ─── Brazilian Portuguese Common Terms ────────────────
    "acesso", "ajuda", "api", "aplicacao", "aplicativo", "aprovado",
    "configuracao", "dados", "desenvolvedor", "documentacao",
    "emergencia", "importante", "informacao", "interno",
    "manutencao", "pendente", "privado", "projeto",
    "recuperacao", "restrito", "secreto", "segredo", "senha",
    "servico", "servidor", "suporte", "teste", "usuario",
    "webservice", "webservices", "revisado",

    # ─── Business/Financial PT-BR Terms ──────────────────
    "admin", "administrativo", "balanco", "boleto", "cadastro",
    "carteira", "cliente", "cobranca", "comercial", "compra",
    "contabil", "contabilidade", "credito", "debito", "despesa",
    "diretoria", "estoque", "extrato", "fatura", "financeiro",
    "fiscal", "fluxo", "formulario", "fornecedor", "gerencia",
    "investimento", "lucro", "nfe", "nfse", "orcamento", "pagar",
    "pagamento", "pesquisa", "prejuizo", "produto", "receber",
    "receita", "registro", "relatorio", "relatorios", "resultado",
    "transacao", "venda", "vendas",

    # ─── Corporate PT-BR Terms ───────────────────────────
    "acao", "acoes", "atividade", "atividades", "associacao",
    "auditoria", "candidato", "cnpj", "comite", "compliance",
    "conselho", "concurso", "conta", "contrato", "contratacao",
    "corporativo", "cpf", "departamento", "diretrizes", "edital",
    "eleicao", "eleitoral", "empresa", "entidade", "estrategia",
    "estrategico", "filial", "fundacao", "gestao", "governo",
    "grupo", "guias", "guia", "imposto", "institucional",
    "inscricao", "licitacao", "manual", "manuals", "memorando",
    "ministerio", "norma", "normas", "normativo", "nota",
    "organizacao", "planejamento", "politica", "portaria",
    "prefeitura", "processo", "programa", "programas", "propostas",
    "proposta", "protocolo", "regulamento", "regulamentacao", "resolucao",
    "rg", "sede", "secretaria", "sociedade", "unidade",

    # ─── Technical PT-BR Terms ───────────────────────────
    "anexo", "autenticacao", "caixa", "certificado", "correio",
    "criptografia", "digitalizar", "download", "email", "entrada",
    "enviado", "extranet", "fila", "firewall", "impressao",
    "impressora", "intranet", "mensagem", "proxy", "rede", "saida",
    "scanner", "token", "upload", "vpn",

    # ─── Database/Config Terms ────────────────────────────
    "config", "conf", "data", "database", "db", "dist", "dump",
    "exportacao", "hidden", "importacao", "install", "internal",
    "modelo", "padrao", "private", "secret", "settings", "setup"
]