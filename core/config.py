"""
Scanner-specific configurations and constants for the LeftOvers scanner.

This module contains all scanner-specific configurations including:
- File extensions to scan (organized by priority and category)
- Backup words and directory names
- HTTP headers configuration
- Content filtering rules

The configuration is organized hierarchically for better maintainability
and to allow selective scanning based on threat level.
"""

# Import global settings
from leftovers.app_settings import (
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

# Organized extensions by priority for leftover/backup discovery

# HIGH PRIORITY - Most likely to contain sensitive leftovers
CRITICAL_BACKUP_EXTENSIONS = [
    "bak", "backup", "old", "orig", "save", "copy", "tmp", "temp", "~",
    "asp", "aspx", "php", "jsp", "py",
]

# MEDIUM PRIORITY - Configuration and log files
CONFIG_LOG_EXTENSIONS = [
    "txt", "log", "log1", "settings", "lock",
    "csv", "pid", "out", "err", "debug", "trace", "cache",
]

# BACKUP FILE VARIATIONS - Common backup suffixes
BACKUP_SUFFIXES = [
    "bak", "bak1", "bak2", "backup", "old", "old1", "old2", "orig", "original",
    "save", "saved", "copy", "copy1", "copy2", "tmp", "temp", "new", "dist",
    "prev", "previous", "last", "~", ".~", "swp", "swo",
]

# ARCHIVE EXTENSIONS - Compressed files likely to be backups
ARCHIVE_EXTENSIONS = [
    "zip", "rar", "tar", "tgz", "tbz2", "txz",
    "7z", "gz", "gzip", "bz2", "xz", "lzma", "z", "Z", "ace", "arj",
]

# DATABASE FILES - Often forgotten on servers
DATABASE_EXTENSIONS = [
    "sql", "dump", "db", "sqlite", "sqlite3", "mdb", "accdb", "dbf",
    "sdf", "mdf", "ldf", "frm", "ibd", "opt", "par", "TRG", "TRN",
]

# CONFIGURATION FILES - Sensitive configuration leftovers
CONFIG_EXTENSIONS = [
    "env", "config", "cfg", "conf", "ini", "yaml", "yml", "json", "xml",
    "properties", "plist", "toml",
]

# EDITOR/IDE LEFTOVERS - Temporary files left by editors
IDE_LEFTOVER_EXTENSIONS = [
    "swp", "swo", "swn", "tmp~", "tmp.swp", "tmp.save", "sml",
    "autosave", "kate-swp", "bak~", "backup~", ".tmp", ".temp",
]

# SOURCE CODE BACKUPS - Code files with backup extensions
CODE_BACKUP_EXTENSIONS = [
    "php.bak", "php.old", "php.save", "php.tmp", "php~", "php.orig",
    "jsp.bak", "jsp.old", "jsp.save", "jsp~", "jsp.orig",
    "asp.bak", "asp.old", "asp.save", "asp~", "asp.orig",
    "aspx.bak", "aspx.old", "aspx.save", "aspx~", "aspx.orig",
    "py.bak", "py.old", "py.save", "py~", "py.orig", "py.tmp",
    "rb.bak", "rb.old", "rb.save", "rb~", "rb.orig",
    "sh.bak", "sh.old", "sh.save", "sh~", "sh.orig",
    "js.bak", "js.old", "js.save", "js~", "js.orig",
    "ts.bak", "ts.old", "ts.save", "ts~", "ts.orig",
    "css.bak", "css.old", "css.save", "css~", "css.orig",
    "html.bak", "html.old", "html.save", "html~", "html.orig",
    "go.bak", "go.old", "go.save", "go~", "go.orig",
    "java.bak", "java.old", "java.save", "java~", "java.orig",
    "cs.bak", "cs.old", "cs.save", "cs~", "cs.orig",
    "vue.bak", "vue.old", "vue~", "vue.orig",
]

# VERSION CONTROL LEFTOVERS - Files left by VCS operations
VCS_LEFTOVER_EXTENSIONS = [
    "rej", "patch", "diff", "merge", "mine", "theirs",
    "working", "conflict",
]

# SENSITIVE DOCUMENT BACKUPS - Documents that might contain sensitive data
DOCUMENT_BACKUP_EXTENSIONS = [
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "pdf.bak", "doc.bak", "docx.bak", "xls.bak", "xlsx.bak",
    "rtf", "odt", "ods", "odp", "txt.bak", "csv.bak",
]

# SECURITY/CREDENTIAL FILES - Files containing credentials or keys
SECURITY_EXTENSIONS = [
    "key", "pem", "crt", "cert", "p12", "pfx", "jks", "keystore", "csr",
    "htpasswd", "passwd", "shadow", "pwd", "secret", "credentials",
    "token", "auth", "oauth", "session", "cookie", "api_key",
    "private", "public", "rsa", "dsa", "ssh", "gpg", "pgp",
    "ppk", "p7b", "der", "cer", "pub", "ed25519", "asc", "sig",
]

# ENVIRONMENT AND BUILD FILES - Configuration and build artifacts
BUILD_CONFIG_EXTENSIONS = [
    "env.local", "env.dev", "env.prod", "env.test", "env.staging", "env.backup",
    "lock.json", "yarn.lock", "package-lock.json", "composer.lock", "Pipfile.lock",
    "requirements.txt.bak", "pom.xml.bak", "build.gradle.bak", "Makefile.bak",
]

EXTRAS_EXTENSIONS = [
    "wml", "bkl", "wmls", "udl", "bat", "dll", "reg", "cmd", "vbs",
    "hta", "wsf", "cpl", "msc", "lnk", "url", "inf", "ins", "isp",
    "ash", "ashx", "cs", "publishproj", "cvs",
]

# SPECIFIC FILES - Complete filenames that should be tested directly
# Organized by priority - CRITICAL files first
CRITICAL_SPECIFIC_FILES = [
    # Certificates and keys (HIGHEST PRIORITY)
    "certificate.pfx", "private.key", "ca_bundle.crt",
    # SSH private keys
    "id_rsa", "id_rsa.pub", "id_ed25519", "id_ed25519.pub", "id_dsa",
    # Environment files
    ".env", ".env.local", ".env.backup", ".env.prod", ".env.dev",
    ".environment", ".envrc", ".envs",
    # Access tokens
    "accesstoken", "accesstokens.json",
    # Web configuration
    ".htaccess", "web.config", "web.debug.config",
    # PHP config (very common exposure)
    "wp-config.php", "config.php", "phpinfo.php", "info.php",
]

SPECIFIC_FILES = [
    # Server configuration
    "webserver-plugin.xml", "webserver.ini",
    # API documentation
    "swagger-ui", "redoc",
    # Container & CI/CD
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "docker-compose.dev.yml", "docker-compose.prod.yml",
    "Jenkinsfile", ".travis.yml", "Makefile", "Vagrantfile", "Procfile",
    # Build and deployment
    ".dockerignore", ".npmrc",
    # Dependency manifests (often contain version info / indirect secrets)
    "package.json", "composer.json", "requirements.txt",
    "Gemfile", "go.mod", "pom.xml", "build.gradle",
    # App config files (common leak points)
    "application.properties", "application.yml", "application.yaml",
    "database.yml", "database.json", "secrets.yml",
    "bootstrap.yml", "config.yml",
    # Environment config
    "env-config.js", "env.js", "environment.js", "environment.json", "environment.ts",
    # Other files
    ".DS_Store", ".well-known", "robots.txt", "sitemap.xml",
    "log_all", "error_log", "access_log", "log.mdb",
    "latest-logs.zip",
]

# VCS AND GIT FILES - Version control specific files
VCS_SPECIFIC_FILES = [
    ".git/config", ".git/HEAD", ".git/FETCH_HEAD", ".git/index",
    ".svn/entries", ".svn/wc.db",
    ".git", ".gitignore", ".gitattributes", ".gitmodules",
    ".hgignore", ".hgsub", ".hgsubstate",
]

# Create the final DEFAULT_EXTENSIONS list from all categories
DEFAULT_EXTENSIONS = [
    *CRITICAL_BACKUP_EXTENSIONS,
    *CONFIG_LOG_EXTENSIONS,
    *SECURITY_EXTENSIONS,
    *CODE_BACKUP_EXTENSIONS,
    *DATABASE_EXTENSIONS,
    *CONFIG_EXTENSIONS,
    *ARCHIVE_EXTENSIONS,
    *IDE_LEFTOVER_EXTENSIONS,
    *VCS_LEFTOVER_EXTENSIONS,
    *DOCUMENT_BACKUP_EXTENSIONS,
    *BUILD_CONFIG_EXTENSIONS,
    *EXTRAS_EXTENSIONS
]

DEFAULT_FILES_WORDS = [
    "README", "assets", "composer", "content", "contents", "debug", "logging",
    "package", "readme", "service", "service1", "swagger", "test", "trace", "ws",
    "settings", "index", "front", "update", "modelo", "modelos", "localhost"
]

BACKUP_DIRECTORY_WORDS = [
    "alpha", "anterior", "antigo", "archive", "archived", "archives", "atual",
    "back", "backup", "beta", "bkp", "copy", "copia", "current",
    "deletar", "delete", "deprecated", "dev", "devel", "development",
    "draft", "fix", "guardar", "historical", "history", "hml", "hotfix",
    "homolog", "homologacao", "homologation", "latest", "legacy", "legado",
    "lixo", "log", "logs", "new", "novo", "obsoleto", "old", "old_version",
    "orig", "original", "patch", "prd", "prod", "producao", "production",
    "rascunho", "rc", "release", "reserva", "salvo", "save", "saved",
    "security", "seguranca", "stable", "staging", "temp", "temporario",
    "temporary", "tmp", "trash", "version", "versao",
]

WEB_RELATED_WORDS = [
    "backend", "conteudo", "deploy", "frontend", "hosting", "hospedagem",
    "htdocs", "html", "httpdocs", "inetpub", "page", "pagina", "portal",
    "public", "public_html", "publication", "publicacao", "site", "sistema",
    "static", "system", "web", "webpage", "webroot", "website", "www", "www-data",
    "arq", "arquivo", "arquivos", "webserver", "webservice", "wordpress", 
    "wp_engine", "wp_content", "wp_includes", "wp", "wp_backup"
]

VERSION_CONTROL_WORDS = [
    ".git", ".svn", "bk", "cvs", "git", "hg", "svn"
]

DATE_VERSION_WORDS = [
    "1", "2", "1.0", "2.0",
    "2001", "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009",
    "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018",
    "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026",
    "abr", "abril", "ago", "agosto", "apr", "april", "aug", "august",
    "dec", "december", "dez", "dezembro", "feb", "february", "fev", "fevereiro",
    "jan", "janeiro", "jul", "july", "jun", "junho", "june", "mai", "maio",
    "mar", "march", "marco", "may", "nov", "november", "novembro",
    "oct", "october", "out", "outubro", "sep", "september", "set", "setembro",
    "v1", "v2", "v3", "v4", "v5",
]

PTBR_COMMON_WORDS = [
    "acesso", "ajuda", "api", "aplicacao", "aplicativo", "aprovado", "configuracao",
    "dados", "desenvolvedor", "documentacao", "emergencia", "importante",
    "informacao", "interno", "manutencao", "pendente", "privado", "projeto",
    "recuperacao", "restrito", "revisado", "secreto", "segredo", "senha",
    "servico", "servidor", "suporte", "teste", "usuario", "webservices",
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
    "manuals", "memo", "message", "ministry", "model", "network",
    "norm", "normative", "norms", "note", "notice", "organization", "ordinance",
    "output", "password", "payable", "payment", "pending", "planning", "policy",
    "prefecture", "private", "printing", "printer", "process", "product", "program",
    "programs", "project", "proposal", "proposals", "protocol", "proxy", "purchase",
    "queue", "receivable", "record", "recovery", "register", "registration",
    "regulated", "regulation", "regulatory", "report", "reports", "research",
    "resolution", "restricted", "result", "reviewed", "sale", "sales", "scanner",
    "secret", "secretary", "sent", "server", "service", "settings", "setup",
    "society", "statement", "strategy", "strategic", "supplier", "support", "tax",
    "test", "token", "transaction", "unit", "upload", "uploads", "user", "vpn", "wap",
    "api", "dashboard", "panel", "login", "cms",
]

PTBR_BUSINESS_WORDS = [
    "admin", "administrativo", "balanco", "boleto", "cadastro", "carteira",
    "cliente", "cobranca", "comercial", "compra", "contabil", "contabilidade",
    "credito", "debito", "despesa", "diretoria", "estoque", "extrato", "fatura",
    "financeiro", "fiscal", "fluxo", "formulario", "fornecedor", "gerencia",
    "investimento", "lucro", "nfe", "nfse", "orcamento", "orcamentos", "pagar",
    "pagamento", "pesquisa", "prejuizo", "produto", "receber", "receita", "registro",
    "verificar", "relatorio", "relatorios", "resultado", "transacao", "venda", "vendas",
    "valor", "valores", "campanha", "campanhas", "cartao", "cartoes", "comissao", "comissoes",
    "corretora", "corretoras", "cotacao", "cotacoes", "financiamento", "consorcio", "imobiliario",
    "imoveis", "imovel", "investidor", "investidores", "leilao", "leiloes", "lote", "lotes",
    "patrimonio", "prospeccao", "prospeccoes", "seguros", "seguro", "taxa", "taxas", "prolabore",
    "tributo", "tributos", "tributacao", "tributacoes", "tributario", "tributarios", "vencimento",
    "vencimentos", "vendedor", "vendedores", "vitrine", "vitrines",
]

PTBR_CORPORATE_WORDS = [
    "acao", "acoes", "associacao", "atividade", "atividades", "auditoria",
    "candidato", "cnpj", "comite", "compliance", "concurso", "conselho", "conta",
    "contratacao", "contrato", "contratos", "corporativo", "cpf", "departamento", "diretrizes",
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
    "saida", "scanner", "token", "upload", "uploads", "vpn",  "variaveis",
    "variavel",
]

DATABASE_CONFIG_WORDS = [
    # Unique PT-BR database terms (not in other lists)
    "exportacao", "importacao", "padrao",
    # Unique terms
    "sql", "structure",
    # Database technology names (not covered by generic lists)
    "redis", "mongo", "mongodb", "postgres", "postgresql", "mysql",
    "oracle", "mssql", "mariadb", "sqlite", "cassandra", "elasticsearch",
    "memcached", "dynamodb", "couchdb", "influxdb", "neo4j", "etcd",
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