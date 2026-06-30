# Changelog

All notable changes to polytools are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/aenealabs/polytools/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/aenealabs/polytools/releases/tag/v0.1.0
