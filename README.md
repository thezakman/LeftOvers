# LeftOvers

![Version](https://img.shields.io/badge/version-1.10.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Performance](https://img.shields.io/badge/performance-optimized-brightgreen.svg)

**LeftOvers** is an advanced, high-performance scanner for detecting residual or "forgotten" files on web servers.

![LeftOvers Scanner Tool](LeftOver.png)

**Key Features:**
- **Scan Levels (0-4)** - From ultra-fast critical-only to exhaustive scans
- **Language Filtering** - Filter wordlists by language (English, Portuguese, All)
- **Smart Baseline Detection** - Eliminates false positives by analyzing server behavior
- **Priority Testing** - Tests critical files (certificates, .env, keys) first
- **Performance Metrics** - Detailed scan statistics with `--metrics`
- **Adaptive Threading** - Automatically adjusts performance based on target speed
- **Thread-Safe** - Fully synchronized concurrent operations


## 📋 Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/TheZakMan/LeftOvers.git

# Navigate to directory
cd LeftOvers

# Install dependencies
pip install -r requirements.txt
```

### As a Python Package

```bash
# Install directly from the repository
pip install git+https://github.com/TheZakMan/LeftOvers.git

# Or install locally after cloning
git clone https://github.com/TheZakMan/LeftOvers.git
cd LeftOvers
pip install .

# For development (editable mode)
pip install -e .
```

## 📁 Project Structure

The project is modularized with the following structure:

```
LeftOvers/
├── LeftOvers.py        # Main script/entry point
├── __init__.py         # Package initialization
├── __main__.py         # Allows execution as module
├── app_settings.py     # Global application settings
├── core/               # Core application components
│   ├── __init__.py
│   ├── config.py       # Scanner-specific configuration
│   ├── cli.py          # Command-line interface
│   ├── detection.py    # False positive detection
│   ├── result.py       # Result classes
│   └── scanner.py      # Main scanner implementation
└── utils/              # Utilities
    ├── __init__.py
    ├── console.py      # Console and formatting utilities
    ├── debug_utils.py  # Debugging tools
    ├── file_utils.py   # File operations
    ├── http_handler.py # HTTP request handler
    ├── http_utils.py   # HTTP client and URL processing
    ├── logger.py       # Logging configuration
    ├── report.py       # Report generation
    ├── url_analyzer.py # URL analysis
    └── url_utils.py    # URL manipulation and generation
```

## 🚀 Quick Start

```bash
# Ultra-fast critical files only
leftovers -u http://example.com --level 0

# Quick scan with essential coverage
leftovers -u http://example.com --level 1

# Balanced scan (default)
leftovers -u http://example.com

# Deep scan with metrics
leftovers -u http://example.com --level 3 --metrics

# Exhaustive scan with brute force (Portuguese)
leftovers -u http://example.com --level 4 -b --lang pt-br

# Stealth mode (slow but harder to detect)
leftovers -u http://example.com --rate-limit 2 -ra

# Route through Burp/mitmproxy (pair with -k for the intercepting CA)
leftovers -u http://example.com --proxy http://127.0.0.1:8080 -k

# Full-featured scan with domain wordlist
leftovers -u http://example.com -b -d -br --output results.json
```

### Exit codes (CI/scripting)

| Code | Meaning |
|------|---------|
| `0`  | Completed, **no** findings |
| `1`  | Completed, **findings** found |
| `2`  | Usage / argument / runtime error |
| `130`| Interrupted (Ctrl+C) |

```bash
# Fail a pipeline / branch on findings
if leftovers -u http://example.com --silent; then
  echo "clean"
else
  echo "leftovers found — investigate"
fi
```

## 📖 Usage

### Basic Examples

```bash
# Scan a single URL (uses installed command)
leftovers -u http://example.com

# Run as a module
python -m leftovers -u http://example.com

# Scan multiple URLs from a file
leftovers -l urls.txt

# Scan with specific level
leftovers -u http://example.com --level 2
```

### Scan Levels

The `--level` controls both the extension set **and** the brute-force
wordlist size (with `-b`), so you opt into cost explicitly:

```bash
# Level 0 - Critical Only (~10-15 tests) - Ultra-fast, only critical files
leftovers -u http://example.com --level 0

# Level 1 - Quick - Fast scan; ~40 highest-value brute words with -b
leftovers -u http://example.com --level 1

# Level 2 - Balanced (DEFAULT) - Common extensions incl. archives
#           (zip/rar/tar.gz); curated brute wordlist (~750) with -b
leftovers -u http://example.com --level 2

# Level 3 - Deep - Comprehensive extensions; curated brute wordlist with -b
leftovers -u http://example.com --level 3

# Level 4 - Exhaustive - All extensions + full brute wordlist (~890,
#           incl. noisy permutations). "Test everything."
leftovers -u http://example.com --level 4 -b
```

### Language Filtering

```bash
# English words only (brute force mode)
leftovers -u http://example.com -b --lang en

# Portuguese words only (brute force mode)
leftovers -u http://example.com -b --lang pt-br

# All languages (default)
leftovers -u http://example.com -b --lang all
```

### Advanced Features

```bash
# Enable brute force mode with common backup words
leftovers -u http://example.com -b

# Enable recursive brute force mode (test each path level)
leftovers -u http://example.com -br

# Enable dynamic domain-based wordlist generation
leftovers -u http://example.com -d

# Show performance metrics at the end
leftovers -u http://example.com --metrics

# Enable brute force mode with custom wordlist
leftovers -u http://example.com -b --wordlist wordlists/custom.txt

# Export results to JSON file
python LeftOvers.py -u http://example.com --output results.json

# Create a separate output file for each URL
python LeftOvers.py -l urls.txt --output-per-url --output results.json

# Specify custom number of threads (with adaptive threading)
python LeftOvers.py -u http://example.com --threads 20

# Rate limiting - maximum requests per second (NEW!)
python LeftOvers.py -u http://example.com --rate-limit 10

# Fixed delay between requests in milliseconds (NEW!)
python LeftOvers.py -u http://example.com --delay 200

# Stealth mode - slow scan with user-agent rotation
python LeftOvers.py -u http://example.com --rate-limit 2 -ra

# Disable SSL verification
python LeftOvers.py -u http://example.com --no-ssl-verify

# Ignore results with specific content types
python LeftOvers.py -u http://example.com -ic text/html --ignore-content image/jpeg

# Filter by status codes (only report 200, 403)
python LeftOvers.py -u http://example.com --status 200,403

# Set custom timeout for requests
python LeftOvers.py -u http://example.com --timeout 10

# Add custom HTTP headers
python LeftOvers.py -u http://example.com -H "X-Custom-Header: Value" -H "Authorization: Bearer token"

# Use a custom User-Agent
python LeftOvers.py -u http://example.com -a "Mozilla/5.0 MyCustomAgent"

# Randomly rotate User-Agents
python LeftOvers.py -u http://example.com -ra

# See all available options
python LeftOvers.py --help
```

## 📦 Requirements

- Python 3.7+
- Required Python packages:
  - requests>=2.31.0
  - colorama>=0.4.6
  - rich>=13.4.2
  - tqdm>=4.66.1
  - urllib3>=2.0.4
  - tldextract>=3.4.4
  - pyOpenSSL>=23.2.0
  - cryptography>=41.0.3

## 🔧 Features

### Core Features
- **Scan Levels (0-4)**: Choose between ultra-fast critical-only scans (~15 tests) to exhaustive scans (~10K+ tests)
- **Baseline Detection**: Analyzes server behavior before testing to eliminate false positives
- **Priority Testing**: Tests critical files first (certificate.pfx, .env, private keys, etc.)
- **Language Filtering**: Filter brute force wordlists by language (English, Portuguese, All)
- **Performance Metrics**: Detailed scan statistics with `--metrics` flag

### Intelligent Detection
- **False Positive Filtering**: Advanced baseline comparison with content hash analysis
- **Multi-Format Support**: Tests 280+ file extensions across multiple categories
- **Smart Extension Prioritization**: Automatically prioritizes extensions based on target context
- **Sanity Checking**: Pre-scan analysis to understand server error behavior

### Performance & Optimization
- **Adaptive Threading**: Automatically adjusts thread count based on target latency
- **LRU Cache**: Intelligent caching system with 30-40% better hit rates
- **Rate Limiting**: Control scan speed with `--rate-limit` or `--delay`
- **Thread-Safe Operations**: All concurrent operations properly synchronized
- **Efficient Memory Management**: Handles large files (>10MB) intelligently

### Brute Force Capabilities
- **Standard Mode**: Test directories and files using 740+ common keywords (level-scaled: ~40 quick, ~750 curated, ~890 exhaustive)
- **Recursive Mode**: Test each path level independently
- **Domain Wordlists**: Generates intelligent backup file patterns based on domain analysis
- **Custom Wordlists**: Support for custom wordlist files

### Output & Reporting
- **Rich Interface**: Colored console with progress bars and formatted tables
- **JSON Export**: Machine-readable output for integration with other tools
- **Per-URL Output**: Option to create separate reports for each analyzed URL
- **Custom Filters**: By status code, content size, and content type

### HTTP Features
- **Custom Headers**: Support for custom HTTP headers and cookies
- **User-Agent Rotation**: Random User-Agent rotation to avoid detection
- **SSL Control**: Option to disable SSL verification for trusted targets
- **Timeout Control**: Configurable request timeouts

## 🔍 Configuration

The `app_settings.py` file allows customizing settings such as:
- Maximum thread count
- Maximum file size for full analysis
- User-Agents for rotation
- Request timeouts
- Default keywords for brute force mode

## ⚡ Performance Tips

**Maximize Speed:**
- Use `--threads 30` or higher for fast targets
- Adaptive threading will automatically optimize based on latency
- Disable SSL verification with `--no-ssl-verify` (trusted targets only)
- The LRU cache automatically improves performance on repeated scans

**Minimize Detection:**
- Use `--rate-limit 5` to limit requests per second
- Add `--delay 500` for fixed delays between requests
- Combine with `-ra` for random User-Agent rotation
- Example: `--rate-limit 2 -ra --delay 1000`

**Handle Slow Targets:**
- Start with fewer threads: `--threads 5`
- Increase timeout: `--timeout 15`
- Adaptive threading will automatically reduce threads for slow responses
- Monitor with `-v` to see automatic adjustments

**Optimize Memory Usage:**
- Use `--output-per-url` when scanning many URLs
- Reduce thread count on resource-constrained systems
- The tool automatically handles large files (>10MB) efficiently

## ❓ Troubleshooting

**Tool is running too slowly**
- Try increasing thread count with `--threads` (adaptive threading will optimize automatically)
- Disable SSL verification with `--no-ssl-verify` (only on trusted targets)
- Reduce timeout with `--timeout`
- The tool will automatically adjust threads based on target performance

**Getting too many false positives**
- Use content type filters with `-ic`
- Adjust content size filters with `--min-size` and `--max-size`
- Use specific status option with `--status`

**Tool crashes with memory errors**
- Reduce thread count
- Set a lower value for MAX_FILE_SIZE_MB in app_settings.py
- Use the `--output-per-url` option when analyzing multiple URLs

**Connection issues**
- Increase timeout with `--timeout`
- Check if target is accessible
- Try using a different User-Agent with `-a`

**Target is blocking/rate-limiting your scans**
- Use `--rate-limit 5` to limit to 5 requests per second
- Use `--delay 500` for a fixed 500ms delay between requests
- Combine with `-ra` for User-Agent rotation
- Example stealth mode: `--rate-limit 2 -ra --delay 1000`

**Scans timing out on slow targets**
- Adaptive threading will automatically reduce threads for slow targets
- Manually set lower thread count with `--threads 5`
- Increase timeout with `--timeout 15`

## 🤝 Contributions

Contributions are welcome! Feel free to open issues or submit pull requests.

## 📝 Changelog

### v1.10.0 (Latest)

**🧰 Pentest integration:**
- `--proxy URL` routes all traffic through an HTTP proxy (Burp/mitmproxy);
  pair with `-k` for the intercepting CA.
- Process **exit code now reflects findings** for CI/scripting: `0` = nothing
  found, `1` = findings found, `2` = usage/runtime error, `130` = interrupted.

### v1.9.5

**🧹 List input hardening:**
- `-l/--list` now validates each line, warn-skips malformed URLs (instead of
  failing silently at request time), and deduplicates the list (order-preserving)
  so a repeated URL isn't scanned twice.

### v1.9.4

**🧹 Cleanup & hardening:**
- HTTP client: cap the read even when HEAD is denied/unavailable — a server
  that blocks HEAD could otherwise stream a multi-GB body (unknown extension)
  straight into memory. Small responses are unaffected.
- Domain wordlist: composite-subdomain permutations now split on all separators
  and use every token (`dev-banco_honda` → dev/banco/honda), instead of only
  the first two parts split on a single separator.
- url_utils: removed a dead word-classification branch in brute-force
  generation that did work with no effect on output (and subtly reordered the
  curated wordlist).

### v1.9.3

**🐛 Metrics & stats correctness:**
- `--metrics` table is now populated — `record_request()` was never called, so
  the table previously showed all zeros. Recording is now wired into every
  request and is O(1) + thread-safe (the average was recomputed from a growing
  list on every call — quadratic — and the recorder had no lock).
- List mode no longer writes shared `start_time`/`end_time` from concurrent URL
  workers (data race) and no longer prints per-URL stats computed against the
  global request counter; the correct aggregated "Global Statistics" block
  remains.
- Domain wordlist merge preserves order deterministically (`list(set(...))`
  scrambled the curated priority ordering).

### v1.9.2

**🐛 Robustness (HTTP client & generators):**
- Large-file ranged GETs now accumulate the sampled bytes (a single chunk can
  be short) and **close the stream**, preventing truncated bodies and leaked
  sockets/file descriptors on long scans.
- Exhausted retries on 429/5xx now return the real response instead of raising,
  so rate-limited/erroring targets are reported rather than dropped.
- `is_ip_address()` strips the port, so IP targets on non-default ports
  (`1.2.3.4:8080`) are handled correctly (no malformed permutation URLs).
- Domain wordlist no longer emits malformed words (`domain.~`, `domain..~`) and
  no longer drops compressed DB dumps (`sql.gz`, `db.gz`).
- `format_size()` handles negative sizes gracefully.

### v1.9.1

**🎯 Coverage & Wordlists:**
- Brute-force wordlist now **scales with `--level`**: quick (~40) at levels 0-1,
  curated (~750) at levels 2-3, exhaustive (~890, incl. noisy permutations) at level 4.
- Default level 2 now tests **compressed archives** (zip/rar/tar/gz/tgz/7z/tar.gz) —
  the #1 leftover/backup format.
- Added many missing base-filename words (`bin`, `build`, `src`, `vendor`, …),
  infra/dev terms, and PT-BR business docs; fixed WordPress paths to use real
  hyphenated names (`wp-content`, `wp-includes`, `wp-admin`).
- Added compound archive/db extensions actually generated now (`tar.gz`, `sql.gz`, …).

**🖥️ UI/UX:**
- Always print a compact perf summary (`N requests in Xs (R req/s) · H hits`).
- Top Findings keep the **filename visible** (no more truncating the URL tail).
- Abbreviated content types (`Binary`, `SQL`, `ZIP`, …) instead of raw cuts.
- Clearer summary labels; fixed the status-color legend rendering.

**🐛 Correctness:**
- Removed duplicate HTTP requests for "important"/archive extensions, while
  still reporting protected (401/403) and redirected matches.
- Large files report the real `Content-Length` (fixes size display + `--min/--max-size`).
- Fewer false positives on JSON/API targets; SPA detection no longer drops real
  `.js.bak`/`.json`/bundle findings.
- Domain-only targets probe `index.{ext}` instead of a useless `/.ext` dotfile.
- Fixed a concurrent-write race and an unlocked stats read in the scanner.

### v1.4.9

**🎯 Major Features:**
- **Scan Levels (0-4)**: Progressive complexity levels from critical-only to exhaustive
  - Level 0: ~10-15 tests (critical files only)
  - Level 1: ~500 tests (quick scan)
  - Level 2: ~2-3K tests (balanced, default)
  - Level 3: ~5-6K tests (deep scan)
  - Level 4: ~6-10K tests (exhaustive)
- **Language Filtering**: `--lang` option to filter wordlists (en, pt-br, all)
- **Performance Metrics**: `--metrics` flag shows detailed scan statistics with rich formatting
- **Baseline Detection**: Advanced false positive filtering by analyzing server behavior
- **Priority Testing**: Critical files (certificates, .env, keys) tested first

**🐛 Bug Fixes:**
- Fixed empty extensions list being replaced by DEFAULT_EXTENSIONS
- Removed all duplicates from config.py (extensions, files, words)
- Fixed false positive detection with content hash comparison
- Fixed progress bar calculation and display
- Fixed pkg_resources deprecation (moved to importlib.metadata)

**⚡ Performance Improvements:**
- Reorganized to `leftovers.*` namespace package
- Refactored config helpers into separate module
- Cleaned up 280+ extensions organization
- Sanity check now runs before critical file testing
- Headers only shown when results exist

**🔧 Technical Improvements:**
- Created `core/helpers.py` for configuration management
- Added `utils/validators.py` for input validation
- Added `utils/metrics.py` for performance tracking
- Improved console output formatting with Rich tables
- Better organization of extensions by category

**📊 Statistics:**
- 5 scan levels (0-4)
- 280+ file extensions tested
- 740+ backup keywords (scaled by --level)
- Smart baseline detection
- Zero duplicate tests

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
