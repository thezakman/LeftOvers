"""
Scanner-specific configurations and constants for the LeftOvers scanner.
"""

# Import global settings
from app_settings import (
    VERSION, 
    DEFAULT_TIMEOUT, 
    DEFAULT_THREADS, 
    MAX_FILE_SIZE_MB,
    USER_AGENTS, 
    DEFAULT_USER_AGENT,
    IGNORE_CONTENT
)
# Default headers for HTTP requests
DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

# ─── Default list of extensions to test ───────────────────

# Organized extensions by categories
TEXT_CONFIG_EXTENSIONS = [
    "txt", "log", "log1", "json", "xml", "yaml", "yml", "csv",
    "properties", "plist", "config", "cfg", "ini", "conf", "env", "settings",
    "lock", "tmpfile", "test", "sample", "md",
]

DATABASE_EXTENSIONS = [
    "sql", "db", "sqlite", "sqlite3", "mdb", "accdb", "dump",
]

BACKUP_EXTENSIONS = [
    "bak", "bak1", "old", "backup", "bkp", "copy", "copy1", "copy2",
    "save", "orig", "temp", "tmp", "dist", "new", "~",
]

ARCHIVE_EXTENSIONS = [
    "zip", "tar", "tgz", "gz", "gzip", "bz2", "xz", "7z", "rar",
    "tar.gz", "tar.bz2",
]

IDE_LEFTOVER_EXTENSIONS = [
    "swp", "swo", "swn", "tmp~", "tmp.swp", "tmp.save", "sml", "autosave", "kate-swp",
]

WEB_EXTENSIONS = [
    "html", "htm", "js", "js.map", "json.map", "xml.map",
    "css", "scss", "sass", "map",
]

CODE_EXTENSIONS = [
    "php", "php~", "php.bak", "php.old", "php.save",
    "jsp", "jsp~", "jsp.bak", "jsp.old", "jsp.save",
    "asp", "asp~", "asp.bak", "asp.old", "asp.save",
    "aspx", "aspx.bak", "aspx.old",
    "rb", "rb~", "rb.bak", "rb.old",
    "py", "py~", "py.bak", "py.old", "py.save",
    "sh", "sh~", "sh.bak", "sh.old", "svc", "ash", "ashx"
]

VERSION_CONTROL_EXTENSIONS = [
    "rej", "patch", "diff", "merge",
]

DOCUMENT_EXTENSIONS = [
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "pdf",
    "rtf", "md", "odt", "ods", "odp",
]

MISC_EXTENSIONS = [
    "exe.bak", "dll.bak", "bin.bak", "img", "iso"
]

# Create the final DEFAULT_EXTENSIONS list from all categories
DEFAULT_EXTENSIONS = [
    *TEXT_CONFIG_EXTENSIONS,
    *DATABASE_EXTENSIONS,
    *BACKUP_EXTENSIONS,
    *ARCHIVE_EXTENSIONS,
    *IDE_LEFTOVER_EXTENSIONS,
    *WEB_EXTENSIONS,
    *CODE_EXTENSIONS,
    *VERSION_CONTROL_EXTENSIONS,
    *DOCUMENT_EXTENSIONS,
    *MISC_EXTENSIONS,
]

# ─── Default list of common backup words/directories to test ───────────────────

# Organize backup words by categories
DEFAULT_FILES_WORDS = [
    "readme", "README", "composer", "package", "debug", "test",
    "logging", "trace", "ws", "swagger", "contents", "content",
    "assets",
]

BACKUP_DIRECTORY_WORDS = [
    "anterior", "antigo", "archive", "archived", "archives", "atual",
    "back", "backup", "bkp", "copia", "copy", "deletar", "dev",
    "devel", "development", "guardar", "hml", "historical", "history",
    "homolog", "homologacao", "latest", "lixo", "log", "logs",
    "new", "novo", "old", "old_version", "orig", "original", "prd",
    "prod", "production", "rascunho", "release", "reserva", "salvo",
    "seguranca", "stable", "staging", "temp", "temporario", "tmp",
    "versao", "producao",
]

WEB_RELATED_WORDS = [
    "backend", "conteudo", "deploy", "frontend", "htdocs", "html",
    "httpdocs", "inetpub", "pagina", "portal", "public", "public_html",
    "publicacao", "site", "sistema", "static", "web", "webpage",
    "webroot", "website", "www", "www-data", "hospedagem",
]

VERSION_CONTROL_WORDS = [
    ".git", ".svn", "bk", "cvs", "git", "hg", "svn",
]

DATE_VERSION_WORDS = [
    "1.0", "2.0", "2020", "2021", "2022", "2023", "2024", "2025",
    "apr", "aug", "dec", "feb", "jan", "jul", "jun", "mar",
    "may", "nov", "oct", "sep", "v1", "v2", "v3",
    "abril", "agosto", "dezembro", "fevereiro", "janeiro", "julho",
    "junho", "maio", "marco", "novembro", "outubro", "setembro",
]

PTBR_COMMON_WORDS = [
    "acesso", "ajuda", "api", "aplicacao", "aplicativo", "aprovado",
    "configuracao", "dados", "desenvolvedor", "documentacao",
    "emergencia", "importante", "informacao", "interno",
    "manutencao", "pendente", "privado", "projeto",
    "recuperacao", "restrito", "secreto", "segredo", "senha",
    "servico", "servidor", "suporte", "teste", "usuario",
    "webservice", "webservices", "revisado",
]

PTBR_BUSINESS_WORDS = [
    "admin", "administrativo", "balanco", "boleto", "cadastro",
    "carteira", "cliente", "cobranca", "comercial", "compra",
    "contabil", "contabilidade", "credito", "debito", "despesa",
    "diretoria", "estoque", "extrato", "fatura", "financeiro",
    "fiscal", "fluxo", "formulario", "fornecedor", "gerencia",
    "investimento", "lucro", "nfe", "nfse", "orcamento", "pagar",
    "pagamento", "pesquisa", "prejuizo", "produto", "receber",
    "receita", "registro", "relatorio", "relatorios", "resultado",
    "transacao", "venda", "vendas",
]

PTBR_CORPORATE_WORDS = [
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
]

PTBR_TECHNICAL_WORDS = [
    "anexo", "autenticacao", "caixa", "certificado", "correio",
    "criptografia", "digitalizar", "download", "email", "entrada",
    "enviado", "extranet", "fila", "firewall", "impressao",
    "impressora", "intranet", "mensagem", "proxy", "rede", "saida",
    "scanner", "token", "upload", "uploads", "vpn",
]

DATABASE_CONFIG_WORDS = [
    "config", "conf", "data", "database", "db", "dist", "dump",
    "exportacao", "hidden", "importacao", "install", "internal",
    "modelo", "padrao", "private", "secret", "settings", "setup"
]

# Create the final DEFAULT_BACKUP_WORDS list from all categories
DEFAULT_BACKUP_WORDS = [
    *DEFAULT_FILES_WORDS,
    *BACKUP_DIRECTORY_WORDS,
    *WEB_RELATED_WORDS,
    *VERSION_CONTROL_WORDS,
    *DATE_VERSION_WORDS,
    *PTBR_COMMON_WORDS,
    *PTBR_BUSINESS_WORDS,
    *PTBR_CORPORATE_WORDS,
    *PTBR_TECHNICAL_WORDS,
    *DATABASE_CONFIG_WORDS,
]