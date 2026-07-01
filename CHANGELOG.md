# Changelog

All notable changes to polytools are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-30

### Added
- **Structured input types** — parameters typed as a `dataclass`, `TypedDict`, `NamedTuple`, or `Enum` now generate proper nested JSON Schema objects (or typed enums), across all four providers. Nesting is recursive and self-referential types are guarded against infinite recursion.
- New tests covering enums, dataclasses, TypedDicts, NamedTuples, nested combinations, and provider integration

### Fixed
- Gemini formatter now preserves `required` lists on nested object schemas

### Changed
- Dropped the author email from package metadata (the GitHub no-reply address was a dead mailto link); author is now name-only

## [0.1.1] - 2026-06-30

### Added
- `py.typed` marker (PEP 561) so downstream type checkers use polytools' inline type hints
- `Typing :: Typed` trove classifier
- `Changelog` project URL

### Fixed
- Corrected `Homepage`, `Repository`, and `Issues` project URLs to point at `aenealabs/polytools`
- `polytools.__version__` now derives from installed package metadata instead of a hardcoded string, so it always matches the released version

### Changed
- Security vulnerability reports now go through GitHub private vulnerability reporting instead of email

## [0.1.0] - 2026-06-30

### Added
- `@tool` decorator — wraps any Python function and exposes cross-provider schema methods
- `Tool.to_openai()` — OpenAI Chat Completions function calling format
- `Tool.to_anthropic()` — Anthropic Messages API tools format
- `Tool.to_gemini()` — Google Gemini FunctionDeclaration format
- `Tool.to_mcp()` — Model Context Protocol `tools/list` format
- `Tool.to_all()` — returns all four formats at once
- `Tool.call(args)` — invoke the function with an LLM argument dict
- Full Python type annotation support: primitives, generics, `Optional`, `Union`, `Literal`, `Any`, bare collection types
- Docstring auto-detection for Google, NumPy, and reStructuredText styles
- Parameter descriptions extracted and included in all provider schemas
- Zero external dependencies — pure Python stdlib (3.9+)
- 91 unit tests covering schema generation, docstring parsing, and all four providers

[Unreleased]: https://github.com/aenealabs/polytools/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/aenealabs/polytools/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/aenealabs/polytools/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/aenealabs/polytools/releases/tag/v0.1.0
