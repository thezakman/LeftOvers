# LeftOvers

**LeftOvers** is an advanced scanner for detecting leftover or residual files on web servers.

![Screenshot of a comment on a GitHub issue showing an image, added in the Markdown, of an Octocat smiling and raising a tentacle.](LeftOver.png)
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

```bash
# Scan a single URL
python LeftOvers.py -u http://example.com

# Run as a module
python -m LeftOvers -u http://example.com

# Scan multiple URLs from a file
python LeftOvers.py -l urls.txt

# Enable brute-force mode
python LeftOvers.py -u http://example.com -b

# View all available options
python LeftOvers.py --help
```

## 🔧 Features

- **Intelligent Detection**: Advanced algorithms to filter false positives
- **Multi-Format Support**: Tests over 120 common file extensions
- **Brute Force Mode**: Tests directories and files using common keywords
- **Efficient Management**:
  - Intelligently detects and handles large files (>10MB)
  - Avoids result duplication
  - Optimized for low resource consumption
- **Custom Filters**: By status code and content length
- **Rich Interface**: Colored console with progress bars
- **Report Export**: JSON format for integration with other tools

## 🔍 Configuration

The `app_settings.py` file allows you to customize settings such as:
- Maximum number of threads
- Maximum file size to fully analyze
- User-Agents for rotation
- Request timeouts

## 🤝 Contributions

Contributions are welcome! Feel free to open issues or submit pull requests.
