# 📂 NeoShare: Local Cloud Server
**A secure, multi-threaded HTTP file server built from scratch with Zero Dependencies.**

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Architecture-Threaded-green?style=for-the-badge&logo=serverless" />
  <img src="https://img.shields.io/badge/Security-Hardened-red?style=for-the-badge&logo=guard" />
  <img src="https://img.shields.io/badge/Frontend-Vanilla_JS-yellow?style=for-the-badge&logo=javascript" />
</p>

---

### 🚀 Overview
**NeoShare** is a custom implementation of a web server designed to solve the limitations of Python's default `http.server`. 

Unlike the standard library (which blocks during transfers), NeoShare uses a **Threaded Architecture** to handle multiple users simultaneously. It features a modern, responsive UI with **Dark Mode**, **Drag-and-Drop Uploads**, and **Video Streaming** capabilities—all without installing a single external library (No Flask, No Django).

---

### ✨ Key Features

| Feature | Description |
| :--- | :--- |
| **⚡ Multi-Threaded Core** | Implements `ThreadingHTTPServer` to serve multiple clients instantly without blocking/freezing. |
| **🛡️ Security Hardened** | Patched against **Directory Traversal** attacks and enforces a **2GB Upload Limit** to prevent RAM exhaustion (DoS). |
| **📤 Modern Uploads** | Custom `multipart/form-data` parser handles Drag-and-Drop uploads seamlessly. |
| **🎬 Media Streaming** | Supports HTTP `Range` headers, allowing video seeking and resume capabilities in the browser. |
| **📦 Smart Downloads** | Auto-generates `.tar.gz` archives on the fly when downloading entire folders. |
| **🎨 Responsive UI** | Auto-detects system theme (Dark/Light mode) and works on Mobile/Desktop. |

---

### 🛠️ Technical Stack
* **Backend:** Python 3 (Standard Library: `http.server`, `socket`, `tarfile`)
* **Frontend:** HTML5, CSS3 (Variables), Vanilla JavaScript (Fetch API)
* **Protocols:** HTTP/1.1 (GET, POST, Range Requests)

---

### 📦 How to Run
Since NeoShare uses **Zero Dependencies**, you don't need `pip install`. Just run it.

```bash
# Clone the repository
git clone [https://github.com/HitroBro/NeoShare-Local-Cloud.git](https://github.com/HitroBro/NeoShare-Local-Cloud.git)

# Enter directory
cd NeoShare-Local-Cloud

# Start Server (Default Port: 8000)
python server.py