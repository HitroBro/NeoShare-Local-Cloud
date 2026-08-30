/**
 * NeoShare File Server - Modern Web GUI v1.1.0
 */
document.addEventListener('DOMContentLoaded', () => {
    const fileList = document.getElementById('fileList');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const searchInput = document.getElementById('searchInput');
    const searchClearBtn = document.getElementById('searchClearBtn');
    const breadcrumbContainer = document.getElementById('breadcrumbContainer');
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const viewListBtn = document.getElementById('viewListBtn');
    const viewGridBtn = document.getElementById('viewGridBtn');
    const downloadFolderBtn = document.getElementById('downloadFolderBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const previewModal = document.getElementById('previewModal');
    const previewCloseBtn = document.getElementById('previewCloseBtn');

    // Setup Theme Toggle
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('neoshare-theme', next);
        });
    }

    // Setup View Mode Toggle
    if (viewListBtn && viewGridBtn) {
        viewListBtn.addEventListener('click', () => setViewMode('list'));
        viewGridBtn.addEventListener('click', () => setViewMode('grid'));
    }

    // Setup Refresh & Download ZIP
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadDirectory(appState.getState().currentPath, false);
            showToast('Refreshed directory', 'info');
        });
    }

    if (downloadFolderBtn) {
        downloadFolderBtn.addEventListener('click', () => {
            const path = appState.getState().currentPath;
            window.location.href = (path.endsWith('/') ? path : path + '/') + '?download=zip';
        });
    }

    // Setup Search
    if (searchInput) {
        searchInput.addEventListener('input', debounce((e) => {
            const query = e.target.value.trim();
            if (searchClearBtn) {
                searchClearBtn.style.display = query ? 'flex' : 'none';
            }
            appState.setState({
                searchQuery: query,
                filteredEntries: filterEntries(appState.getState().entries, query)
            });
            renderFiles();
        }, 150));
    }

    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', () => {
            if (searchInput) {
                searchInput.value = '';
                searchInput.focus();
            }
            searchClearBtn.style.display = 'none';
            appState.setState({
                searchQuery: '',
                filteredEntries: appState.getState().entries
            });
            renderFiles();
        });
    }

    // Column Sorting
    ['sortName', 'sortSize', 'sortModified'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const col = id.replace('sort', '').toLowerCase();
        el.addEventListener('click', () => {
            const state = appState.getState();
            const asc = state.sortBy === col ? !state.sortAsc : true;
            appState.setState({ sortBy: col, sortAsc: asc });
            updateSortHeaders(col, asc);
            renderFiles();
        });
    });

    function updateSortHeaders(activeCol, asc) {
        ['name', 'size', 'modified'].forEach(col => {
            const cap = col.charAt(0).toUpperCase() + col.slice(1);
            const el = document.getElementById('sort' + cap);
            if (!el) return;
            el.classList.remove('asc', 'desc');
            const icon = el.querySelector('.sort-icon');
            if (col === activeCol) {
                el.classList.add(asc ? 'asc' : 'desc');
                if (icon) icon.className = `fas fa-sort-${asc ? 'up' : 'down'} sort-icon`;
            } else {
                if (icon) icon.className = 'fas fa-sort sort-icon';
            }
        });
    }

    // Modal Close
    if (previewCloseBtn && previewModal) {
        previewCloseBtn.addEventListener('click', () => {
            previewModal.style.display = 'none';
            document.body.classList.remove('modal-open');
        });
        previewModal.addEventListener('click', (e) => {
            if (e.target === previewModal) {
                previewModal.style.display = 'none';
                document.body.classList.remove('modal-open');
            }
        });
    }

    // Upload & Drag-and-drop
    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                handleUpload(fileInput.files);
            }
        });
        setupDragAndDrop(dropZone, handleUpload);
    }

    function handleUpload(files) {
        const val = validateFiles(files);
        if (!val.valid) {
            showToast(val.error, 'error');
            if (dropZone) dropZone.classList.add('shake-error');
            setTimeout(() => dropZone && dropZone.classList.remove('shake-error'), 400);
            return;
        }

        const progressContainer = document.getElementById('uploadProgressContainer');
        const progressBar = document.getElementById('uploadProgressBar');
        const progressText = document.getElementById('uploadProgressPercent');
        const progressName = document.getElementById('uploadProgressName');

        if (progressContainer) {
            progressContainer.style.display = 'block';
            progressName.textContent = `Uploading ${files.length} file(s)...`;
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
        }

        uploadFilesWithProgress(
            files,
            appState.getState().currentPath,
            (percent) => {
                if (progressBar) progressBar.style.width = percent + '%';
                if (progressText) progressText.textContent = percent + '%';
            },
            (res) => {
                if (progressContainer) progressContainer.style.display = 'none';
                showToast(`Successfully uploaded ${files.length} file(s)`, 'success');
                loadDirectory(appState.getState().currentPath, false);
            },
            (err) => {
                if (progressContainer) progressContainer.style.display = 'none';
                showToast(`Upload failed: ${err.message}`, 'error');
            }
        );
    }

    // Render Breadcrumbs
    function renderBreadcrumbs(path) {
        if (!breadcrumbContainer) return;
        breadcrumbContainer.innerHTML = '';

        const clean = path.replace(/\/+/g, '/').replace(/^\/|\/$/g, '');
        const segments = clean ? clean.split('/') : [];

        const rootItem = document.createElement('div');
        rootItem.className = 'breadcrumb-item';
        rootItem.innerHTML = `<a href="/" data-path="/"><i class="fas fa-home"></i> Home</a>`;
        breadcrumbContainer.appendChild(rootItem);

        let cumulative = '';
        segments.forEach((seg, idx) => {
            cumulative += '/' + seg;
            const isLast = idx === segments.length - 1;

            const sep = document.createElement('span');
            sep.className = 'breadcrumb-separator';
            sep.innerHTML = '<i class="fas fa-chevron-right"></i>';
            breadcrumbContainer.appendChild(sep);

            const item = document.createElement('div');
            item.className = 'breadcrumb-item' + (isLast ? ' current' : '');
            if (isLast) {
                item.textContent = decodeURIComponent(seg);
            } else {
                item.innerHTML = `<a href="${cumulative}" data-path="${cumulative}">${decodeURIComponent(seg)}</a>`;
            }
            breadcrumbContainer.appendChild(item);
        });

        breadcrumbContainer.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                loadDirectory(link.getAttribute('data-path'));
            });
        });
    }

    // Get Icon for File
    function getFileIconClass(entry) {
        if (entry.is_dir) return 'fas fa-folder icon-folder';
        const ext = entry.name.split('.').pop().toLowerCase();
        if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(ext)) return 'fas fa-file-image icon-image';
        if (['mp4', 'webm', 'ogg', 'mov', 'mkv'].includes(ext)) return 'fas fa-file-video icon-video';
        if (['mp3', 'wav', 'flac', 'm4a'].includes(ext)) return 'fas fa-file-audio icon-audio';
        if (ext === 'pdf') return 'fas fa-file-pdf icon-pdf';
        if (['zip', 'tar', 'gz', 'bz2', '7z', 'rar'].includes(ext)) return 'fas fa-file-archive icon-archive';
        if (['js', 'py', 'html', 'css', 'json', 'sh', 'c', 'cpp'].includes(ext)) return 'fas fa-file-code icon-code';
        if (['doc', 'docx', 'odt', 'rtf'].includes(ext)) return 'fas fa-file-word icon-doc';
        return 'fas fa-file icon-default';
    }

    function formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + units[i];
    }

    function formatDate(ts) {
        if (!ts) return '-';
        const d = new Date(ts * 1000);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Main Render Function
    function renderFiles() {
        if (!fileList) return;
        const state = appState.getState();
        const sorted = sortEntries(state.filteredEntries, state.sortBy, state.sortAsc);

        renderBreadcrumbs(state.currentPath);

        if (sorted.length === 0) {
            fileList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open empty-state-icon"></i>
                    <p class="empty-state-title">No files found</p>
                    <p class="text-xs">Drag and drop files to upload to this directory</p>
                </div>`;
            return;
        }

        const fragment = document.createDocumentFragment();
        sorted.forEach(entry => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.tabIndex = 0;

            const iconClass = getFileIconClass(entry);
            const current = state.currentPath.endsWith('/') ? state.currentPath : state.currentPath + '/';
            const targetUrl = entry.name === '..' 
                ? (state.currentPath.split('/').slice(0, -1).join('/') || '/')
                : current + encodeURIComponent(entry.name);

            item.innerHTML = `
                <div class="file-name">
                    <i class="${iconClass} file-icon"></i>
                    <a href="${targetUrl}">${entry.name}</a>
                </div>
                <div class="file-size">${entry.is_dir ? '-' : formatFileSize(entry.size)}</div>
                <div class="file-modified">${formatDate(entry.modified)}</div>
                <div class="file-actions"></div>
            `;

            const link = item.querySelector('a');
            if (entry.is_dir) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    loadDirectory(targetUrl);
                });
            } else {
                link.addEventListener('click', (e) => {
                    const ext = entry.name.split('.').pop().toLowerCase();
                    const previewables = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'mp4', 'webm', 'mp3', 'wav', 'txt', 'md', 'json', 'js', 'css', 'html', 'py'];
                    if (previewables.includes(ext)) {
                        e.preventDefault();
                        openPreview(entry, state.currentPath);
                    }
                });
            }

            const actions = item.querySelector('.file-actions');
            if (entry.name !== '..') {
                if (!entry.is_dir) {
                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'action-btn';
                    copyBtn.title = 'Copy Link';
                    copyBtn.innerHTML = '<i class="fas fa-link"></i>';
                    copyBtn.onclick = (e) => {
                        e.stopPropagation();
                        copyFileLink(targetUrl);
                    };
                    actions.appendChild(copyBtn);
                }

                const dlBtn = document.createElement('a');
                dlBtn.className = 'action-btn';
                dlBtn.title = entry.is_dir ? 'Download as ZIP' : 'Download';
                dlBtn.href = entry.is_dir ? targetUrl + '?download=zip' : targetUrl;
                dlBtn.innerHTML = '<i class="fas fa-download"></i>';
                if (!entry.is_dir) dlBtn.setAttribute('download', entry.name);
                actions.appendChild(dlBtn);
            }

            fragment.appendChild(item);
        });

        fileList.innerHTML = '';
        fileList.appendChild(fragment);
    }

    // Subscribe to state changes
    appState.on('change', () => renderFiles());

    // Initial view mode & directory load
    setViewMode(appState.getState().viewMode);
    loadDirectory(window.location.pathname || '/');
    setupListKeyboardNav();
});
