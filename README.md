# 📂 NeoShare: Local Cloud Server

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Architecture](https://img.shields.io/badge/Architecture-Threaded-2EA44F?style=for-the-badge&logo=serverless&logoColor=white)]()
[![Security](https://img.shields.io/badge/Security-Hardened-DC3545?style=for-the-badge&logo=guard&logoColor=white)]()
[![Zero Deps](https://img.shields.io/badge/Dependencies-Zero-6C757D?style=for-the-badge&logo=python&logoColor=white)]()
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)

**A secure, multi-threaded HTTP file server built from scratch with Zero Dependencies.**

---

## 🚀 Overview

**NeoShare** is a custom implementation of a web server designed to solve the limitations of Python's standard `http.server`.

Unlike the standard library (which blocks during transfers), NeoShare uses a **Threaded Architecture** to handle multiple users simultaneously. It features a modern, responsive UI with **Dark Mode**, **Drag-and-Drop Uploads**, and **Video Streaming** capabilities—all without installing a single external library (No Flask, No Django, No FastAPI).

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **⚡ Multi-Threaded Core** | Implements `ThreadingHTTPServer` to serve multiple clients instantly without blocking/freezing |
| **🛡️ Security Hardened** | Patched against **Directory Traversal** attacks and enforces a **2GB Upload Limit** to prevent RAM exhaustion (DoS) |
| **📤 Modern Uploads** | Custom `multipart/form-data` parser handles Drag-and-Drop uploads seamlessly |
| **🎬 Media Streaming** | Supports HTTP `Range` headers, allowing video seeking and resume capabilities in the browser |
| **📦 Smart Downloads** | Auto-generates `.tar.gz` archives on the fly when downloading entire folders |
| **🎨 Responsive UI** | Auto-detects system theme (Dark/Light mode) and works on Mobile/Desktop |

---

## 🛠️ Technical Stack

* **Backend:** Python 3 (Standard Library only: `http.server`, `socketserver`, `tarfile`, `mimetypes`, `urllib.parse`)
* **Frontend:** HTML5, CSS3 (Custom Properties/Variables), Vanilla JavaScript (Fetch API)
* **Protocols:** HTTP/1.1 (GET, POST, Range Requests, Chunked Transfer)
* **Concurrency:** `ThreadingMixIn` + `ThreadingHTTPServer` (one thread per connection)

---

## 📁 Project Structure

```text
NeoShare-Local-Cloud/
├── server.py       # Threaded HTTP server with custom request handler
├── index.html      # Responsive web UI (dark/light auto-detect)
├── script.js       # Frontend logic: upload, download, navigation, streaming
├── styles.css      # Cyberpunk-themed responsive styling
├── LICENSE         # MIT License
└── README.md
```

---

## ⚙️ How It Works

### Security Hardening
```python
# Path traversal protection
request_path = os.path.normpath(request_path)
if not request_path.startswith(base_path):
    self.send_error(403, "Forbidden: Directory traversal attempt")
    return

# Upload size limit (2GB)
if content_length > 2 * 1024 * 1024 * 1024:
    self.send_error(413, "Payload Too Large: 2GB limit exceeded")
    return
```

### Range Request Streaming (Video Seeking)
```python
# Supports HTTP Range headers for video/audio seeking
range_header = self.headers.get('Range')
if range_header:
    start, end = parse_range(range_header, file_size)
    self.send_response(206)  # Partial Content
    self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
```

### Auto Archive Generation
```python
# Folder download → streaming .tar.gz
with tarfile.open(fileobj=self.wfile, mode='w|gz') as tar:
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            tar.add(os.path.join(root, file), arcname=relative_path)
```

---

## 🚀 Quick Start

Since NeoShare uses **Zero Dependencies**, you don't need `pip install`. Just run it.

```bash
# Clone the repository
git clone https://github.com/HitroBro/NeoShare-Local-Cloud.git

# Enter directory
cd NeoShare-Local-Cloud

# Start Server (Default Port: 8000)
python server.py
```

Open your browser at **http://localhost:8000**

### Custom Port
```bash
python server.py 9000
# Or set environment variable
PORT=9000 python server.py
```

---

## 📸 UI Preview

| Light Mode | Dark Mode |
|------------|-----------|
| Auto-detects `prefers-color-scheme` | Cyberpunk green-on-black theme |

*Responsive design works on mobile, tablet, and desktop.*

---

## 🔧 Use Cases

- **Local file sharing** across devices on LAN
- **Quick media streaming** from laptop to TV/phone
- **Development file server** for testing uploads/downloads
- **Learning HTTP internals** — clean, readable stdlib implementation
- **Air-gapped environments** — no internet, no dependencies

---

## 📄 License

MIT License — Feel free to use, modify, and distribute.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure zero external dependencies are introduced
4. Test on multiple browsers (Chrome, Firefox, Safari)
5. Submit a pull request

---

<p align="center">
  <strong>Built for learning, hardened for production.</strong>
</p>

<p align="center">
  <a href="https://github.com/HitroBro/NeoShare-Local-Cloud">
    <img src="https://komarev.com/ghpvc/?username=HitroBro&repo=NeoShare-Local-Cloud&color=2EA44F&style=for-the-badge" alt="Views" />
  </a>
</p>