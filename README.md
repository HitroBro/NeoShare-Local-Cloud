\# 📂 NeoShare: Python HTTP File Server

\*\*A modern, zero-dependency local cloud server built from scratch.\*\*



\### 🚀 Overview

NeoShare is a custom-built HTTP server that turns any directory into a modern file-sharing interface. Unlike Python's default `http.server`, NeoShare supports \*\*drag-and-drop uploads\*\*, \*\*dark mode\*\*, and \*\*file streaming\*\*.



\### 🛠 Tech Stack

\* \*\*Backend:\*\* Python 3 (Custom `http.server` implementation)

\* \*\*Frontend:\*\* Vanilla HTML5, CSS3 (Variables), JavaScript (Fetch API)

\* \*\*Protocols:\*\* HTTP/1.1 (GET, POST, Range Requests)



\### ✨ Key Features

\* \*\*Zero Dependencies:\*\* Runs on standard Python libraries (`http.server`, `socket`).

\* \*\*Multipart Uploads:\*\* Custom parser for `multipart/form-data` to handle file uploads without frameworks.

\* \*\*Video Streaming:\*\* Implements `Range` header support to allow seeking/skipping in video players.

\* \*\*Modern UI:\*\* Responsive design with automatic Dark Mode detection.



\### 📦 How to Run

```bash

python server.py -p 8000

