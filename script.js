document.addEventListener('DOMContentLoaded', () => {
    const fileList = document.getElementById('fileList');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const currentPath = document.getElementById('current-path').textContent;
    const themeToggle = document.getElementById('themeToggle');
    const themeButton = document.getElementById('themeButton');
    
    // Theme Management
    initTheme();
    
    // Theme toggle switch event listener
    themeToggle.addEventListener('change', () => {
        toggleTheme(themeToggle.checked);
    });
    
    // Theme button event listener
    themeButton.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const isDark = currentTheme === 'dark';
        
        // Toggle theme
        toggleTheme(!isDark);
        
        // Update the toggle switch to match
        themeToggle.checked = !isDark;
    });
    
    // Function to toggle theme
    function toggleTheme(isDark) {
        if (isDark) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            themeButton.innerHTML = '<i class="fas fa-sun"></i> Light Mode';
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
            themeButton.innerHTML = '<i class="fas fa-moon"></i> Dark Mode';
        }
    }
    
    // Initialize theme based on saved preference or system preference
    function initTheme() {
        const savedTheme = localStorage.getItem('theme');
        
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
            const isDark = savedTheme === 'dark';
            themeToggle.checked = isDark;
            themeButton.innerHTML = isDark ? 
                '<i class="fas fa-sun"></i> Light Mode' : 
                '<i class="fas fa-moon"></i> Dark Mode';
        } else {
            // Check for system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDark) {
                document.documentElement.setAttribute('data-theme', 'dark');
                themeToggle.checked = true;
                themeButton.innerHTML = '<i class="fas fa-sun"></i> Light Mode';
                localStorage.setItem('theme', 'dark');
            }
        }
    }

    // Load file list
    loadFiles();

    // Handle file upload form submission
    uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        uploadFiles();
    });

    // Open file selector when clicking on drop zone
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    // Handle drag and drop events
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            uploadFiles();
        }
    });

    // Load file list using AJAX
    function loadFiles() {
        fileList.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Loading files...</div>';
        
        fetch(`${currentPath}?json=1`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                displayFiles(data.entries);
            })
            .catch(error => {
                fileList.innerHTML = `<div class="loading"><i class="fas fa-exclamation-circle"></i> Error loading files: ${error.message}</div>`;
            });
    }

    // Display files in the file list
    function displayFiles(files) {
        if (files.length === 0) {
            fileList.innerHTML = '<div class="loading"><i class="fas fa-folder-open"></i> This folder is empty</div>';
            return;
        }

        fileList.innerHTML = '';
        
        files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            // Icon and file name
            const fileNameDiv = document.createElement('div');
            fileNameDiv.className = 'file-name';
            
            const icon = document.createElement('i');
            if (file.is_dir) {
                icon.className = 'fas fa-folder';
            } else {
                icon.className = 'fas fa-file';
            }
            
            const link = document.createElement('a');
            link.href = encodeURI(file.name === '..' ? '/' + file.path : file.name);
            link.textContent = file.name;
            
            fileNameDiv.appendChild(icon);
            fileNameDiv.appendChild(link);
            
            // File size
            const fileSizeDiv = document.createElement('div');
            fileSizeDiv.className = 'file-size';
            fileSizeDiv.textContent = file.is_dir ? '-' : formatFileSize(file.size);
            
            // Last modified
            const fileModifiedDiv = document.createElement('div');
            fileModifiedDiv.className = 'file-modified';
            fileModifiedDiv.textContent = file.modified ? formatDate(file.modified) : '-';
            
            // Actions
            const fileActionsDiv = document.createElement('div');
            fileActionsDiv.className = 'file-actions';
            
            if (file.is_dir && file.name !== '..') {
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'action-btn download';
                downloadBtn.innerHTML = '<i class="fas fa-download"></i>';
                downloadBtn.title = 'Download as archive';
                downloadBtn.onclick = (e) => {
                    e.preventDefault();
                    window.location.href = `${encodeURI(file.name)}/?download=zip`;
                };
                fileActionsDiv.appendChild(downloadBtn);
            }
            
            fileItem.appendChild(fileNameDiv);
            fileItem.appendChild(fileSizeDiv);
            fileItem.appendChild(fileModifiedDiv);
            fileItem.appendChild(fileActionsDiv);
            
            fileList.appendChild(fileItem);
        });
    }

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Format date
    function formatDate(timestamp) {
        const date = new Date(timestamp * 1000);
        return date.toLocaleString();
    }

    // Upload files
    function uploadFiles() {
        if (fileInput.files.length === 0) return;
        
        const formData = new FormData();
        for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('file', fileInput.files[i]);
        }
        
        // Show loading indicator
        const originalContent = dropZone.innerHTML;
        dropZone.innerHTML = '<i class="fas fa-spinner fa-spin"></i><p>Uploading files...</p>';
        
        fetch(currentPath, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Upload failed');
            }
            // Reset form and reload files
            uploadForm.reset();
            loadFiles();
            
            // Show success message
            dropZone.innerHTML = '<i class="fas fa-check" style="color: var(--success-color);"></i><p>Upload successful!</p>';
            setTimeout(() => {
                dropZone.innerHTML = originalContent;
            }, 2000);
        })
        .catch(error => {
            console.error('Error uploading files:', error);
            
            // Show error message
            dropZone.innerHTML = `<i class="fas fa-exclamation-circle" style="color: var(--danger-color);"></i><p>Upload failed: ${error.message}</p>`;
            setTimeout(() => {
                dropZone.innerHTML = originalContent;
            }, 3000);
        });
    }
});