# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in this project, please report it responsibly:

### Private Disclosure (Preferred)

**Email:** ghiahitarth@gmail.com

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes

We will acknowledge receipt within 48 hours and provide a status update within 5 business days.

### Public Disclosure

If you prefer, you may open a GitHub issue with the `security` label. However, for critical vulnerabilities, private disclosure is strongly encouraged.

## Security Features

This project implements the following security measures:

- **Path Traversal Protection:** Double normalization + prefix check (`os.path.abspath()` + `startswith()`)
- **Upload Size Limit:** Hard 2GB cap enforced before reading request body
- **No Directory Traversal:** Chroot-like behavior restricting access to serve root
- **MIME Type Validation:** Safe default for unknown file types
- **No External Dependencies:** Pure Python standard library (zero supply-chain risk)

## Scope

This policy applies to the NeoShare-Local-Cloud server code (`server.py`) only. The frontend assets (`index.html`, `styles.css`, `script.js`) are static and out of scope.

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities.