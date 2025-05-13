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
    "rtf", "odt", "ods", "odp",
]

MISC_EXTENSIONS = [
    "exe.bak", "dll.bak", "bin.bak", "img", "iso", "dat", "dcm", "key", 
    "pem", "crt", "cert", "p12", "pfx", "jks", "keystore", "csr", 
    "htpasswd", "passwd", "shadow", "pwd", "secret", "credentials",
    "aws", "env.local", "env.dev", "env.prod", "env.test", 
    "toml", "lock.json", "yarn.lock", "package-lock.json", "composer.lock"
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

DEFAULT_FILES_WORDS = [
    "README", "assets", "composer", "content", "contents", "debug", "logging",
    "package", "readme", "service", "service1", "swagger", "test", "trace", "ws"
]

BACKUP_DIRECTORY_WORDS = [
    "anterior", "antigo", "archive", "archived", "archives", "atual", "back",
    "backup", "bkp", "copy", "copia", "current", "deletar", "delete", "dev",
    "devel", "development", "draft", "guardar", "historical", "history", "hml",
    "homolog", "homologacao", "homologation", "latest", "lixo", "log", "logs",
    "new", "novo", "old", "old_version", "orig", "original", "prd", "prod",
    "producao", "production", "rascunho", "release", "reserva", "salvo", "save",
    "saved", "security", "seguranca", "stable", "staging", "temp", "temporario",
    "temporary", "tmp", "trash", "version", "versao"
]

WEB_RELATED_WORDS = [
    "backend", "conteudo", "deploy", "frontend", "hosting", "hospedagem",
    "htdocs", "html", "httpdocs", "inetpub", "page", "pagina", "portal",
    "public", "public_html", "publication", "publicacao", "site", "sistema",
    "static", "system", "web", "webpage", "webroot", "website", "www", "www-data"
]

VERSION_CONTROL_WORDS = [
    ".git", ".svn", "bk", "cvs", "git", "hg", "svn"
]

DATE_VERSION_WORDS = [
    "1.0", "2.0", "2020", "2021", "2022", "2023", "2024", "2025", "abr", "abril",
    "ago", "agosto", "apr", "april", "aug", "august", "dec", "december", "dez",
    "dezembro", "feb", "february", "fev", "fevereiro", "jan", "janeiro", "jul",
    "july", "jun", "junho", "june", "mai", "maio", "mar", "march", "marco", "may",
    "nov", "november", "novembro", "oct", "october", "out", "outubro", "sep",
    "september", "set", "setembro", "v1", "v2", "v3"
]

PTBR_COMMON_WORDS = [
    "acesso", "ajuda", "api", "aplicacao", "aplicativo", "aprovado", "configuracao",
    "dados", "desenvolvedor", "documentacao", "emergencia", "importante",
    "informacao", "interno", "manutencao", "pendente", "privado", "projeto",
    "recuperacao", "restrito", "revisado", "secreto", "segredo", "senha",
    "servico", "servidor", "suporte", "teste", "usuario", "webservice", "webservices"
]

EN_COMMON_WORDS = [
    "access", "account", "accounting", "action", "actions", "activity", "activities",
    "admin", "administrative", "app", "application", "approved", "attachment",
    "authentication", "balance", "billing", "board", "bookkeeping", "box", "branch",
    "budget", "candidate", "certificate", "client", "compliance", "company",
    "configuration", "conf", "config", "contract", "corporate", "credit", "data",
    "database", "db", "debit", "default", "department", "developer", "digitize",
    "dist", "documentation", "download", "dump", "election", "electoral", "email",
    "emergency", "encryption", "entity", "expense", "export", "financial", "fiscal",
    "firewall", "flow", "form", "foundation", "government", "group", "guide",
    "guidelines", "guides", "help", "hidden", "hiring", "id", "important", "import",
    "income", "information", "input", "install", "institutional", "internal",
    "inventory", "intranet", "loss", "mail", "maintenance", "management", "manual",
    "manuals", "memo", "message", "ministry", "model", "network", "nfe", "nfse",
    "norm", "normative", "norms", "note", "notice", "organization", "ordinance",
    "output", "password", "payable", "payment", "pending", "planning", "policy",
    "prefecture", "private", "printing", "printer", "process", "product", "program",
    "programs", "project", "proposal", "proposals", "protocol", "proxy", "purchase",
    "queue", "receivable", "record", "recovery", "register", "registration",
    "regulated", "regulation", "regulatory", "report", "reports", "research",
    "resolution", "restricted", "result", "reviewed", "sale", "sales", "scanner",
    "secret", "secretary", "sent", "server", "service", "settings", "setup",
    "society", "statement", "strategy", "strategic", "supplier", "support", "tax",
    "test", "token", "transaction", "unit", "upload", "uploads", "user", "vpn"
]

PTBR_BUSINESS_WORDS = [
    "admin", "administrativo", "balanco", "boleto", "cadastro", "carteira",
    "cliente", "cobranca", "comercial", "compra", "contabil", "contabilidade",
    "credito", "debito", "despesa", "diretoria", "estoque", "extrato", "fatura",
    "financeiro", "fiscal", "fluxo", "formulario", "fornecedor", "gerencia",
    "investimento", "lucro", "nfe", "nfse", "orcamento", "pagar", "pagamento",
    "pesquisa", "prejuizo", "produto", "receber", "receita", "registro",
    "relatorio", "relatorios", "resultado", "transacao", "venda", "vendas"
]

PTBR_CORPORATE_WORDS = [
    "acao", "acoes", "associacao", "atividade", "atividades", "auditoria",
    "candidato", "cnpj", "comite", "compliance", "concurso", "conselho", "conta",
    "contratacao", "contrato", "corporativo", "cpf", "departamento", "diretrizes",
    "edital", "eleicao", "eleitoral", "empresa", "entidade", "estrategia",
    "estrategico", "filial", "fundacao", "gestao", "governo", "grupo", "guia",
    "guias", "imposto", "institucional", "inscricao", "licitacao", "manual",
    "manuals", "memorando", "ministerio", "norma", "normas", "normativo", "nota",
    "organizacao", "planejamento", "politica", "portaria", "prefeitura", "processo",
    "programa", "programas", "proposta", "propostas", "protocolo", "regulamento",
    "regulamentacao", "resolucao", "rg", "sede", "secretaria", "sociedade", "unidade"
]

PTBR_TECHNICAL_WORDS = [
    "anexo", "autenticacao", "caixa", "certificado", "correio", "criptografia",
    "digitalizar", "download", "email", "entrada", "enviado", "extranet", "fila",
    "firewall", "impressao", "impressora", "intranet", "mensagem", "proxy", "rede",
    "saida", "scanner", "token", "upload", "uploads", "vpn"
]

DATABASE_CONFIG_WORDS = [
    "conf", "config", "data", "database", "db", "dist", "dump", "exportacao",
    "hidden", "importacao", "install", "internal", "modelo", "padrao", "private",
    "settings", "setup"
]

# Create the final DEFAULT_BACKUP_WORDS list from all categories
DEFAULT_BACKUP_WORDS = [
    *DEFAULT_FILES_WORDS,
    *BACKUP_DIRECTORY_WORDS,
    *WEB_RELATED_WORDS,
    *VERSION_CONTROL_WORDS,
    *DATE_VERSION_WORDS,
    *EN_COMMON_WORDS,
    *PTBR_COMMON_WORDS,
    *PTBR_BUSINESS_WORDS,
    *PTBR_CORPORATE_WORDS,
    *PTBR_TECHNICAL_WORDS,
    *DATABASE_CONFIG_WORDS,
]