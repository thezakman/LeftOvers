# LeftOvers

**LeftOvers** is an advanced scanner for detecting residual or "forgotten" files on web servers.

![LeftOvers Scanner Tool](LeftOver.png)

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

## 🚀 Usage

### Basic Examples

```bash
# Scan a single URL
python LeftOvers.py -u http://example.com

# Run as a module
python -m LeftOvers -u http://example.com

# Scan multiple URLs from a file
python LeftOvers.py -l urls.txt
```

### Advanced Features

```bash
# Enable brute force mode with common backup words
python LeftOvers.py -u http://example.com -b

# Enable recursive brute force mode (test each path level)
python LeftOvers.py -u http://example.com -br

# Enable dynamic domain-based wordlist generation (NEW!)
python LeftOvers.py -u http://example.com -d

# Enable brute force mode with custom wordlist
python LeftOvers.py -u http://example.com -b --wordlist wordlists/custom.txt

# Export results to JSON file
python LeftOvers.py -u http://example.com --output results.json

# Create a separate output file for each URL
python LeftOvers.py -l urls.txt --output-per-url --output results.json

# Specify custom number of threads
python LeftOvers.py -u http://example.com --threads 20

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

# Test index.{extension} on domain URLs
python LeftOvers.py -u http://example.com --test-index

# See all available options
python LeftOvers.py --help
```

## 📦 Requirements

- Python 3.7+
- Required Python packages:
  - requests>=2.27.1
  - colorama>=0.4.4
  - rich>=12.0.0
  - tqdm>=4.62.3
  - urllib3>=1.26.8
  - tldextract>=3.1.2
  - pyOpenSSL>=22.0.0
  - cryptography>=36.0.0
  - concurrent-futures-pool>=1.0.0

## 🔧 Features

- **Intelligent Detection**: Advanced algorithms to filter false positives
- **Multi-Format Support**: Tests over 120 common file extensions
- **Brute Force Mode**: Test directories and files using common keywords
- **Dynamic Domain Wordlists**: Generates intelligent backup file patterns based on domain analysis
- **Smart Extension Prioritization**: Automatically prioritizes extensions based on target context
- **Efficient Management**:
  - Intelligently detects and handles large files (>10MB)
  - Avoids result duplication
  - Optimized for low resource consumption
- **Custom Filters**: By status code, content size, and content type
- **Rich Interface**: Colored console with progress bars
- **Report Export**: JSON format for integration with other tools
- **Custom Headers**: Support for custom HTTP headers
- **User-Agent Rotation**: Random User-Agent rotation to avoid detection
- **Per-URL Output**: Option to create separate reports for each analyzed URL

## 🔍 Configuration

The `app_settings.py` file allows customizing settings such as:
- Maximum thread count
- Maximum file size for full analysis
- User-Agents for rotation
- Request timeouts
- Default keywords for brute force mode

## ❓ Troubleshooting

**Tool is running too slowly**
- Try increasing thread count with `--threads`
- Disable SSL verification with `--no-ssl-verify` (only on trusted targets)
- Reduce timeout with `--timeout`

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

## 🤝 Contributions

Contributions are welcome! Feel free to open issues or submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
