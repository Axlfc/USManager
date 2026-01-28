# Changelog

## [1.1.0] - 2025-05-22

### Fixed
- Completed the refactor from `lamp_manager` to `unified_stack_manager`.
- Updated residual references in `package_manager.py` and `rollback.py`.
- Restored mocks in `tests/test_config.py` to ensure environment independence.
- Fixed incorrect indentation in `package_manager.py`.

### Added
- Definitive list of AI modules for Drupal 11 automation.
- Improved `verify-ai` command with comprehensive module check and multi-provider connectivity tests (OpenAI, Ollama, Anthropic, Google).
- Automated blog creation with dynamic AI content generation (using `ai_content_suggestions`) and static fallback on both platforms.
- Unified AI verification and site creation features for both Windows and Linux stacks with full feature parity.

### Documentation
- Updated `README.md` with the new module list and unified commands.
- Enhanced `GUIA_DETALLADA_WINDOWS.md` with technical details on AI blog automation and verification.
- Added "Validation in Windows" section for external testing.
