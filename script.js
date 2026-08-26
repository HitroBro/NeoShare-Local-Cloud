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
