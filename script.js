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
