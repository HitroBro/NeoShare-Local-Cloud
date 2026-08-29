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
