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
    # Compound archive extensions — extremely common for backups
    # (e.g. site.tar.gz, bin.tar.bz2). Previously referenced by the
    # extension optimizer / "important" set but never actually generated.
    "tar.gz", "tar.bz2", "tar.xz",
]

# DATABASE FILES - Often forgotten on servers
DATABASE_EXTENSIONS = [
    "sql", "dump", "db", "sqlite", "sqlite3", "mdb", "accdb", "dbf",
    "sdf", "mdf", "ldf", "frm", "ibd", "opt", "par", "TRG", "TRN",
    # Compressed database dumps — common leftovers
    "sql.gz", "sql.zip", "sql.bz2", "db.gz", "dump.gz",
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

# LEGACY / NICHE SERVER EXTENSIONS - Older/less common but still found
LEGACY_EXTENSIONS = [
    "inc",          # PHP includes exposed directly
    "phps",         # PHP source view (misconfig exposes source)
    "cfm", "cfc",   # ColdFusion (common in enterprise)
    "pl", "cgi",    # Perl/CGI scripts
    "md",           # README.md, CHANGELOG.md — version disclosure
    "shtml", "shtm", # SSI files
]

# CONFIG DOUBLE-EXTENSION BACKUPS - config files backed up with .bak
CONFIG_BACKUP_EXTENSIONS = [
    "json.bak", "yaml.bak", "yml.bak",
    "xml.bak",  "ini.bak",  "cfg.bak",
    "conf.bak", "env.bak",  "toml.bak",
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
    # DB admin tools left in production
    "adminer.php", "adminer.php.bak",
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
    ".env.example", ".env.sample",
    # WordPress backups (very commonly found)
    "wp-config.php.bak", "wp-config.php.old", "wp-config.bak",
    # IaC state files (contain secrets in plaintext)
    "terraform.tfstate", "terraform.tfstate.backup",
    # OS artifacts (reveal directory structure)
    ".DS_Store", "Thumbs.db", "desktop.ini",
    # Misc
    ".well-known", "robots.txt", "sitemap.xml",
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
    *LEGACY_EXTENSIONS,
    *CONFIG_BACKUP_EXTENSIONS,
    *EXTRAS_EXTENSIONS,
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
    "wp", "wp_engine", "wp_backup",
    # Real WordPress paths use HYPHENS, not underscores — the underscore
    # variants almost never exist on disk. Keep the hyphenated real names.
    "wp-content", "wp-includes", "wp-admin",
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
    # Security tools / admin panels left in production
    "phpinfo", "info", "adminer", "pma", "phpmyadmin", "xmlrpc",
    # Credential/session shortforms
    "creds", "secrets", "cache", "session",
    # DB connection files
    "connect", "connection", "dbconfig", "dbconn",
    # Web shell leftovers
    "shell",
    # DB dumps
    "migration", "mysqldump", "db_dump", "sql_dump",
    # IaC / DevOps artifacts
    "terraform", "ansible", "helm", "values", "pipeline", "deployment",
    # WordPress
    "wp-config",
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
    "saida", "scanner", "token", "upload", "uploads", "vpn", "variaveis",
    "variavel",
    # PT-BR equivalents of new EN words
    "conexao", "migracao", "sessao", "cache", "credenciais", "chaves",
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

# COMMON FILENAME WORDS - Generic base names frequently dumped as archives or
# left as directories (e.g. bin.rar, build.zip, site.tar.gz, files.zip).
# These are NOT business/sector terms — they are the "default" names developers
# reach for when zipping up a folder, which is exactly how leftovers appear.
COMMON_FILENAME_WORDS = [
    # Build / release artifacts
    "bin", "build", "builds", "releases", "snapshot", "snapshots",
    "target", "output", "out", "compiled",
    # Generic content folders
    "files", "file", "media", "downloads", "docs", "doc",
    "document", "documents", "documentos", "anexos",
    # Images / media
    "image", "images", "img", "imagens", "photo", "photos", "foto", "fotos",
    "video", "videos", "gallery", "galeria",
    # Source / code
    "source", "sources", "src", "code", "codigo", "fonte", "fontes",
    "vendor", "vendors", "lib", "libs", "modules", "node_modules",
    # "Whole thing" archive names
    "full", "complete", "completo", "final", "all", "tudo", "todos",
    "geral", "everything", "entire",
    # Site / app roots
    "home", "main", "master", "principal", "root", "base",
    "loja", "store", "shop", "ecommerce", "wwwroot", "webfiles",
    # Backup-of-everything names
    "backups", "dumps", "exports", "imports", "snapshot_db",
    "fullbackup", "full_backup", "sitebackup", "site_backup",
    "dbbackup", "db_backup", "wwwbackup", "www_backup",
]

# INFRA / DEV WORDS - High-value sysadmin and developer artifacts
INFRA_DEV_WORDS = [
    "cgi-bin", "repo", "repos", "repository", "repositorio",
    "apps", "webapp", "administrator", "artifacts",
    # Database dump tool names (produce e.g. mongodump.gz, pg_dump.sql)
    "mongodump", "pg_dump", "pgdump",
]

# BACKUP VARIANT WORDS - Real-world backup naming patterns frequently seen
BACKUP_VARIANT_WORDS = [
    "backup1", "backup2", "backup3", "bkp1", "bkp2",
    "old_site", "site_old", "www_old", "old_www", "backup_site",
    "restore", "restored", "recover",
    "live", "nightly", "daily",
]

# PT-BR BUSINESS DOCUMENT WORDS - Sensitive Brazilian financial/HR documents
# commonly archived and left behind (folha de pagamento, nota fiscal, etc.)
PTBR_DOCS_WORDS = [
    "folha", "folhapagamento", "holerite", "holerites",
    "contracheque", "contracheques", "boletos",
    "notafiscal", "notasfiscais", "recibos", "faturas",
    "comprovantes", "planilhas", "planilha",
    "dre", "razao", "balancete", "balancetes",
    "darf", "sped", "rh", "recursoshumanos",
]

# AGGRESSIVE / NOISY WORDS - Low hit-rate permutations (numbered variants,
# generic placeholders). Included ONLY at scan level 4 ("test everything"),
# since each word costs one request per extension and most never resolve.
AGGRESSIVE_BACKUP_WORDS = [
    # Numbered / suffixed backup permutations
    "backup_old", "bkup", "backupdb", "dbdump", "dump1", "fulldump",
    "backupsite", "site_bkp", "backup_www", "backup_final", "backupfull",
    "baktmp", "backuptmp", "copia_seguranca", "copiaseguranca",
    "copia1", "copia2", "seguranca_copia",
    # Deploy / build permutations
    "dist1", "build1", "release1", "release2", "deploy1", "rollout",
    "package1", "bundle", "bundles", "export1", "export2", "exported",
    "imported", "staging1", "prod1", "prod_old", "prod_backup", "prodbackup",
    "beta1", "alpha1", "rc1", "rc2", "weekly", "monthly", "livesite", "www_live",
    # Site / app permutations
    "website1", "site1", "site2", "website_backup", "websitebackup",
    "pagina1", "paginas", "portal1", "sistema1", "sistema_old", "sistemas",
    "aplicacao1", "app1", "app2", "application1", "webapps",
    "plataforma", "plataformas",
    # Generic placeholders
    "temp1", "temp2", "tmp1", "tmp2", "tmpfile", "testfile",
    "teste1", "teste2", "testes", "sample", "samples", "example", "examples",
    "exemplo", "exemplos", "demo", "demos", "default1", "misc",
    "file1", "file2", "arquivo1", "arquivos1", "novo1", "novos",
    "antigo1", "antigos", "velho", "velhos", "stuff", "coisas",
    "various", "varios", "other", "others", "outros",
    # Virtualization / containers / CI
    "vmdk", "iso", "vm", "docker", "dockerfile1", "k8s", "kubernetes",
    "jenkins", "gitlab", "bitbucket",
    # Web roots / admin tools permutations
    "htdocs1", "public_html1", "wwwroot1", "htdocs_old", "cgibin",
    "phpmyadmin1", "mysqldump1", "snapshot1", "image1", "www_data",
    # Content folder permutations
    "manuais", "documentos1", "docs1", "relatorios1", "relatorio1",
    "contratos1", "audios", "audio", "musica", "musicas", "arquivomorto",
    "privado1", "confidencial", "sigiloso",
    # PT-BR fiscal extras
    "imposto1", "impostos", "das", "escrituracao", "livrocaixa",
    "demonstrativo", "demonstrativos", "nf", "nfs", "recibo",
]

# QUICK_BACKUP_WORDS - Highest-value words only, for fast/low-level brute scans.
QUICK_BACKUP_WORDS = list(dict.fromkeys([
    "backup", "bkp", "old", "www", "site", "web", "public", "public_html",
    "htdocs", "wwwroot", "data", "db", "database", "dump", "sql",
    "backup1", "old_site", "site_old", "www_old", "bin", "src", "build",
    "dist", "release", "files", "upload", "uploads", "admin", "config",
    "test", "dev", "staging", "prod", "temp", "tmp", "new", "copy", "full",
    "home", "index", "wp-content", "app", "api", "logs",
]))

# Create the final DEFAULT_BACKUP_WORDS list from all categories.
# Several categories intentionally overlap (e.g. "admin", "api", "cache" appear
# in both EN and business lists), so the assembled list is deduplicated while
# preserving first-seen order — duplicates would only waste HTTP requests.
#
# Two tiers:
#   DEFAULT_BACKUP_WORDS    - curated, high-signal words (levels 1-3 + default -b)
#   EXHAUSTIVE_BACKUP_WORDS - curated + aggressive permutations (level 4 only)
_ALL_BACKUP_WORD_CATEGORIES = [
    *DEFAULT_FILES_WORDS,
    *COMMON_FILENAME_WORDS,
    *INFRA_DEV_WORDS,
    *BACKUP_VARIANT_WORDS,
    *BACKUP_DIRECTORY_WORDS,
    *WEB_RELATED_WORDS,
    *VERSION_CONTROL_WORDS,
    *DATE_VERSION_WORDS,
    *EN_COMMON_WORDS,
    *PTBR_COMMON_WORDS,
    *PTBR_BUSINESS_WORDS,
    *PTBR_CORPORATE_WORDS,
    *PTBR_TECHNICAL_WORDS,
    *PTBR_DOCS_WORDS,
    *DATABASE_CONFIG_WORDS,
]
DEFAULT_BACKUP_WORDS = list(dict.fromkeys(_ALL_BACKUP_WORD_CATEGORIES))

# Exhaustive tier: curated list plus the aggressive/noisy permutations.
EXHAUSTIVE_BACKUP_WORDS = list(dict.fromkeys(
    [*DEFAULT_BACKUP_WORDS, *AGGRESSIVE_BACKUP_WORDS]
))