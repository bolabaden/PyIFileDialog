# Changelog

All notable changes to PyIFileDialog will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-19

### Added
- Initial release of PyIFileDialog
- Native Windows file dialog support without heavy dependencies
- Core dialog functions:
  - `open_file_dialog()` - Select existing files
  - `save_file_dialog()` - Save/create files  
  - `open_folder_dialog()` - Select directories
  - `open_file_and_folder_dialog()` - Hybrid file/folder selection
- Comprehensive file type filtering system
- Multi-selection support for files and folders
- Rich customization options via Windows FileOpenOptions flags
- Complete COM interface definitions for Windows shell APIs
- Robust error handling with meaningful Python exceptions
- Comprehensive documentation with real-world examples
- Type hints throughout for better IDE support

### Changed
- Migrated from GPL v3 to MIT license for broader compatibility
- Updated project metadata and configuration
- Enhanced all module documentation with detailed explanations

### Technical Details
- Pure Python implementation using only ctypes
- Full COM (Component Object Model) integration
- Windows 7+ compatibility
- Python 3.8+ support
- Thread-safe GUID management
- Proper COM object lifecycle management
- Extensive debugging and logging support

### Documentation
- Comprehensive README with architecture explanations
- Real-world usage examples for common scenarios
- Troubleshooting guide and FAQ
- Complete API reference with all parameters
- Integration examples for popular GUI frameworks
- Best practices and performance tips