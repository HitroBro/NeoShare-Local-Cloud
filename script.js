// Theme Engine Initialization
(function initTheme() {
    const savedTheme = localStorage.getItem('neoshare-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }
    
    if (savedTheme) {
        applyTheme(savedTheme);
    } else {
        applyTheme(prefersDark.matches ? 'dark' : 'light');
    }
    
    prefersDark.addEventListener('change', (e) => {
        if (!localStorage.getItem('neoshare-theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
})();


window.addEventListener('storage', (e) => {
    if (e.key === 'neoshare-theme' && e.newValue) {
        document.documentElement.setAttribute('data-theme', e.newValue);
    }
});


// Client-side Validation Helper
function validateFiles(fileList) {
    const MAX_SIZE = 2 * 1024 * 1024 * 1024; // 2 GB
    if (!fileList || fileList.length === 0) {
        return { valid: false, error: 'No files selected' };
    }
    for (let i = 0; i < fileList.length; i++) {
        if (fileList[i].size > MAX_SIZE) {
            return {
                valid: false,
                error: `"${fileList[i].name}" exceeds the 2GB upload limit`
            };
        }
    }
    return { valid: true };
}


// Batch DOM Insertion Utility
function createDocumentFragmentFromList(items, renderCallback) {
    const fragment = document.createDocumentFragment();
    items.forEach(item => {
        const el = renderCallback(item);
        if (el) fragment.appendChild(el);
    });
    return fragment;
}


// Performance Optimization Utilities
function debounce(func, delay = 200) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => func.apply(this, args), delay);
    };
}

function throttle(func, limit = 100) {
    let inThrottle;
    return function (...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}


// Global Keyboard Shortcuts
window.addEventListener('keydown', (e) => {
    // Quick search focus: "/"
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        const search = document.getElementById('searchInput');
        if (search) search.focus();
    }
    // Upload trigger: "u"
    if (e.key === 'u' && document.activeElement.tagName !== 'INPUT') {
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.click();
    }
    // Escape modal
    if (e.key === 'Escape') {
        const modal = document.getElementById('previewModal');
        if (modal && modal.style.display !== 'none') {
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        }
    }
});
