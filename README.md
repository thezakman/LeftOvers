# LeftOvers

**LeftOvers** is an advanced scanner for detecting leftover or residual files on web servers.

![LeftOvers Scanner Tool](LeftOver.png)

## 📋 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/LeftOvers.git

# Navigate to the directory
cd LeftOvers

# Install dependencies (if you have requirements.txt)
pip install -r requirements.txt
```

## 📁 Project Structure

The project is modularized with the following structure:

```
LeftOvers/
├── LeftOvers.py        # Main script/entry point
├── __init__.py         # Package initialization
├── __main__.py         # Allows running as a module
├── app_settings.py     # Global application settings
├── core/               # Core application components
│   ├── __init__.py
│   ├── config.py       # Scanner-specific configurations
│   ├── cli.py          # Command line interface
│   ├── detection.py    # False positive detection
│   ├── result.py       # Result classes
│   └── scanner.py      # Main scanner implementation
└── utils/              # Utilities
    ├── __init__.py
    ├── console.py      # Console and formatting utilities
    ├── file_utils.py   # File operations
    ├── http_utils.py   # HTTP client and URL processing
    ├── report.py       # Report generation
    ├── url_utils.py    # URL manipulation and generation
    └── logger.py       # Logging configuration
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
# Enable brute-force mode with custom wordlist
python LeftOvers.py -u http://example.com -b --wordlist wordlists/custom.txt

# Export results to JSON file
python LeftOvers.py -u http://example.com --output results.json

# Specify custom number of threads
python LeftOvers.py -u http://example.com --threads 20

# Disable SSL verification
python LeftOvers.py -u http://example.com --no-ssl-verify

# Ignore results with specific content types
python LeftOvers.py -u http://example.com -ci text/html -ci image/jpeg

# Filter by status codes (only report 200, 403)
python LeftOvers.py -u http://example.com -sc 200 -sc 403

# Set custom timeout for requests
python LeftOvers.py -u http://example.com --timeout 10

# View all available options
python LeftOvers.py --help
```

## 📦 Requirements

- Python 3.7+
- Required Python packages:
  - requests
  - colorama
  - tqdm
  - argparse

## 🔧 Features

- **Intelligent Detection**: Advanced algorithms to filter false positives
- **Multi-Format Support**: Tests over 120 common file extensions
- **Brute Force Mode**: Tests directories and files using common keywords
- **Efficient Management**:
  - Intelligently detects and handles large files (>10MB)
  - Avoids result duplication
  - Optimized for low resource consumption
- **Custom Filters**: By status code, content length, and content type
- **Rich Interface**: Colored console with progress bars
- **Report Export**: JSON format for integration with other tools

## 🔍 Configuration

The `app_settings.py` file allows you to customize settings such as:
- Maximum number of threads
- Maximum file size to fully analyze
- User-Agents for rotation
- Request timeouts

## ❓ Troubleshooting

**The tool is running too slowly**
- Try increasing the number of threads with `--threads`
- Disable SSL verification with `--no-ssl-verify` (only on trusted targets)

**Getting too many false positives**
- Enable intelligent detection with `--smart-detection`
- Adjust content length filters with `--min-size` and `--max-size`

**The tool crashes with memory errors**
- Reduce the number of threads
- Set a lower value for MAX_FILE_SIZE_MB in app_settings.py

## 🤝 Contributions

Contributions are welcome! Feel free to open issues or submit pull requests.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
