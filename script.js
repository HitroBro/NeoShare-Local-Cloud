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
