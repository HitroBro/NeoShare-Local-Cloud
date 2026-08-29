// NeoShare Reactive State Manager
class StateManager {
    constructor(initialState = {}) {
        this.state = {
            currentPath: window.location.pathname || '/',
            entries: [],
            filteredEntries: [],
            searchQuery: '',
            sortBy: 'name',
            sortAsc: true,
            viewMode: localStorage.getItem('neoshare-view-mode') || 'list',
            isLoading: false,
            ...initialState
        };
        this.listeners = new Map();
    }

    getState() {
        return this.state;
    }

    setState(patch) {
        this.state = { ...this.state, ...patch };
        this.emit('change', this.state);
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
        return () => this.listeners.get(event).delete(callback);
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(cb => cb(data));
        }
    }
}
const appState = new StateManager();


// Filter & Search Engine
function filterEntries(entries, query) {
    if (!query) return entries;
    const lower = query.toLowerCase();
    return entries.filter(e => e.name.toLowerCase().includes(lower));
}


// Sorting Engine
function sortEntries(entries, sortBy, sortAsc) {
    return [...entries].sort((a, b) => {
        // Always place virtual parent '..' at top
        if (a.name === '..') return -1;
        if (b.name === '..') return 1;

        // Directories first
        if (a.is_dir !== b.is_dir) {
            return a.is_dir ? -1 : 1;
        }

        let comparison = 0;
        if (sortBy === 'name') {
            comparison = a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' });
        } else if (sortBy === 'size') {
            comparison = (a.size || 0) - (b.size || 0);
        } else if (sortBy === 'modified') {
            comparison = (a.modified || 0) - (b.modified || 0);
        }
        return sortAsc ? comparison : -comparison;
    });
}


// View Mode Handler
function setViewMode(mode) {
    appState.setState({ viewMode: mode });
    localStorage.setItem('neoshare-view-mode', mode);
    const list = document.getElementById('fileList');
    const listBtn = document.getElementById('viewListBtn');
    const gridBtn = document.getElementById('viewGridBtn');

    if (list) {
        list.classList.toggle('grid-view', mode === 'grid');
    }
    if (listBtn && gridBtn) {
        listBtn.classList.toggle('active', mode === 'list');
        gridBtn.classList.toggle('active', mode === 'grid');
    }
}


// Media Preview Engine
function openPreview(entry, currentPath) {
    const modal = document.getElementById('previewModal');
    const title = document.getElementById('previewTitle');
    const body = document.getElementById('previewBody');
    const download = document.getElementById('previewDownloadBtn');
    if (!modal || !body) return;

    const fileUrl = (currentPath.endsWith('/') ? currentPath : currentPath + '/') + encodeURIComponent(entry.name);
    title.textContent = entry.name;
    download.href = fileUrl;
    body.innerHTML = '';

    const ext = entry.name.split('.').pop().toLowerCase();
    const images = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'];
    const videos = ['mp4', 'webm', 'ogg'];
    const audios = ['mp3', 'wav', 'ogg', 'm4a', 'flac'];
    const texts = ['txt', 'md', 'json', 'js', 'css', 'html', 'py', 'sh', 'yml', 'yaml', 'c', 'cpp', 'h'];

    if (images.includes(ext)) {
        const img = document.createElement('img');
        img.src = fileUrl;
        img.alt = entry.name;
        body.appendChild(img);
    } else if (videos.includes(ext)) {
        const video = document.createElement('video');
        video.src = fileUrl;
        video.controls = true;
        video.autoplay = true;
        body.appendChild(video);
    } else if (audios.includes(ext)) {
        const audio = document.createElement('audio');
        audio.src = fileUrl;
        audio.controls = true;
        audio.autoplay = true;
        body.appendChild(audio);
    } else if (texts.includes(ext)) {
        fetch(fileUrl)
            .then(res => res.text())
            .then(text => {
                const pre = document.createElement('pre');
                pre.textContent = text;
                body.appendChild(pre);
            })
            .catch(() => {
                body.innerHTML = '<p class="text-danger">Failed to load text preview</p>';
            });
    } else {
        body.innerHTML = `<div class="text-center"><i class="fas fa-file-alt text-4xl mb-3"></i><p>No preview available for this file type.</p></div>`;
    }

    modal.style.display = 'flex';
    modal.classList.add('active');
    document.body.classList.add('modal-open');
}


// Upload Engine with Real-Time Progress
function uploadFilesWithProgress(files, targetPath, onProgress, onSuccess, onError) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', targetPath, true);

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
            const percent = Math.round((e.loaded / e.total) * 100);
            onProgress(percent);
        }
    };

    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            try {
                const json = JSON.parse(xhr.responseText);
                if (onSuccess) onSuccess(json);
            } catch (err) {
                if (onSuccess) onSuccess({ status: 'success' });
            }
        } else {
            if (onError) onError(new Error(`Upload failed with status ${xhr.status}`));
        }
    };

    xhr.onerror = () => {
        if (onError) onError(new Error('Network error during upload'));
    };

    xhr.send(formData);
}


// Drag & Drop Event Wireup
function setupDragAndDrop(dropZone, onDropFiles) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
        window.addEventListener(evt, e => e.preventDefault());
        dropZone.addEventListener(evt, e => e.preventDefault());
    });

    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, () => dropZone.classList.add('dragover'));
    });

    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, () => dropZone.classList.remove('dragover'));
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
            onDropFiles(dt.files);
        }
    });
}
