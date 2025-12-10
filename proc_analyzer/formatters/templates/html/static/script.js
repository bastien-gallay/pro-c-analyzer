// Toggle collapsible sections
document.querySelectorAll('.collapsible').forEach(button => {
    button.addEventListener('click', function() {
        // Le contenu collapsible est le nextElementSibling du parent (file-header)
        const header = this.closest('.file-header');
        const content = header ? header.nextElementSibling : null;
        if (content && content.classList.contains('collapsible-content')) {
            content.classList.toggle('active');
            this.textContent = content.classList.contains('active') ? 'Masquer' : 'Afficher';
        }
    });
});

// Simple table sorting
document.querySelectorAll('th').forEach(header => {
    header.addEventListener('click', function() {
        const table = this.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const columnIndex = Array.from(this.parentElement.children).indexOf(this);
        const isAsc = this.classList.contains('asc');
        
        // Reset all headers
        table.querySelectorAll('th').forEach(th => th.classList.remove('asc', 'desc'));
        this.classList.add(isAsc ? 'desc' : 'asc');
        
        rows.sort((a, b) => {
            const aText = a.children[columnIndex].textContent.trim();
            const bText = b.children[columnIndex].textContent.trim();
            const aNum = parseFloat(aText);
            const bNum = parseFloat(bText);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAsc ? bNum - aNum : aNum - bNum;
            }
            return isAsc ? bText.localeCompare(aText) : aText.localeCompare(bText);
        });
        
        rows.forEach(row => tbody.appendChild(row));
    });
});

// File filtering functionality
let currentFilter = '';
let currentFilterType = '';

// File sorting functionality
let currentSortCriteria = 'filename';
let currentSortAscending = true;

function filterFiles(filterText) {
    currentFilter = filterText.toLowerCase().trim();
    currentFilterType = '';
    const fileSections = document.querySelectorAll('.file-section');
    const fileTitles = document.querySelectorAll('.file-title');
    
    // Reset summary cards
    document.querySelectorAll('.summary-card').forEach(card => {
        card.classList.remove('active');
    });
    
    fileSections.forEach(section => {
        const title = section.querySelector('.file-title');
        const fileName = title ? title.textContent.toLowerCase() : '';
        
        if (currentFilter === '' || fileName.includes(currentFilter)) {
            section.style.display = '';
            if (title && currentFilter !== '') {
                title.classList.add('filter-active');
            } else if (title) {
                title.classList.remove('filter-active');
            }
        } else {
            section.style.display = 'none';
            if (title) {
                title.classList.remove('filter-active');
            }
        }
    });
}

function filterFilesByType(filterType) {
    currentFilterType = filterType;
    currentFilter = '';
    const fileSections = document.querySelectorAll('.file-section');
    
    // Reset summary cards
    document.querySelectorAll('.summary-card').forEach(card => {
        card.classList.remove('active');
    });
    
    // Activate clicked card
    const clickedCard = document.querySelector(`[data-filter-type="${filterType}"]`);
    if (clickedCard) {
        clickedCard.classList.add('active');
    }
    
    // Reset filter input
    const filterInput = document.getElementById('file-filter-input');
    if (filterInput) {
        filterInput.value = '';
    }
    
    fileSections.forEach(section => {
        let shouldShow = false;
        
        switch(filterType) {
            case 'todos':
                shouldShow = section.dataset.hasTodos === 'true';
                break;
            case 'cursor-issues':
                shouldShow = section.dataset.hasCursorIssues === 'true';
                break;
            case 'memory-issues':
                shouldShow = section.dataset.hasMemoryIssues === 'true';
                break;
            case 'high-complexity':
                const avgCyclo = parseFloat(section.dataset.avgCyclomatic || '0');
                shouldShow = avgCyclo > 5;
                break;
            case 'high-cognitive':
                const avgCogn = parseFloat(section.dataset.avgCognitive || '0');
                shouldShow = avgCogn > 8;
                break;
            default:
                shouldShow = true;
        }
        
        section.style.display = shouldShow ? '' : 'none';
        
        const title = section.querySelector('.file-title');
        if (title) {
            if (shouldShow) {
                title.classList.add('filter-active');
            } else {
                title.classList.remove('filter-active');
            }
        }
    });
}

// Filter input handler
const filterInput = document.getElementById('file-filter-input');
if (filterInput) {
    filterInput.addEventListener('input', function() {
        filterFiles(this.value);
    });
}

// Reset filter button
const resetButton = document.getElementById('file-filter-reset');
if (resetButton) {
    resetButton.addEventListener('click', function() {
        if (filterInput) {
            filterInput.value = '';
        }
        currentFilter = '';
        currentFilterType = '';
        document.querySelectorAll('.summary-card').forEach(card => {
            card.classList.remove('active');
        });
        document.querySelectorAll('.file-section').forEach(section => {
            section.style.display = '';
            const title = section.querySelector('.file-title');
            if (title) {
                title.classList.remove('filter-active');
            }
        });
        // Reapply sorting after reset
        sortFiles(currentSortCriteria, currentSortAscending);
    });
}

// Click on file title to filter
document.querySelectorAll('.file-title').forEach(title => {
    title.addEventListener('click', function(e) {
        // Ne pas déclencher si on clique sur le bouton collapsible
        if (e.target.closest('.collapsible')) {
            return;
        }
        
        // Reset filter type first
        currentFilterType = '';
        document.querySelectorAll('.summary-card').forEach(card => {
            card.classList.remove('active');
        });
        
        const fileName = this.textContent.replace(/^📄\s+/, '').trim();
        if (filterInput) {
            filterInput.value = fileName;
        }
        filterFiles(fileName);
    });
});

// Click on summary cards to filter
document.querySelectorAll('.summary-card.filterable').forEach(card => {
    card.addEventListener('click', function() {
        const filterType = this.dataset.filterType;
        if (filterType) {
            filterFilesByType(filterType);
        }
    });
});

// File sorting functionality
function sortFiles(criteria, ascending) {
    // Get all visible file sections (respecting current filter)
    const fileSections = Array.from(document.querySelectorAll('.file-section'))
        .filter(section => section.style.display !== 'none');
    
    if (fileSections.length === 0) {
        return;
    }
    
    // Get the parent container (files-container or direct parent)
    const filesContainer = document.getElementById('files-container');
    const parent = filesContainer || (fileSections[0] ? fileSections[0].parentElement : null);
    
    if (!parent) {
        return;
    }
    
    // Sort the file sections
    fileSections.sort((a, b) => {
        let aValue, bValue;
        
        switch(criteria) {
            case 'filename':
                aValue = (a.dataset.filename || '').toLowerCase();
                bValue = (b.dataset.filename || '').toLowerCase();
                return ascending 
                    ? aValue.localeCompare(bValue)
                    : bValue.localeCompare(aValue);
            
            case 'total-lines':
                aValue = parseInt(a.dataset.totalLines || '0', 10);
                bValue = parseInt(b.dataset.totalLines || '0', 10);
                return ascending ? aValue - bValue : bValue - aValue;
            
            case 'non-empty-lines':
                aValue = parseInt(a.dataset.nonEmptyLines || '0', 10);
                bValue = parseInt(b.dataset.nonEmptyLines || '0', 10);
                return ascending ? aValue - bValue : bValue - aValue;
            
            case 'avg-cyclomatic':
                aValue = parseFloat(a.dataset.avgCyclomatic || '0');
                bValue = parseFloat(b.dataset.avgCyclomatic || '0');
                return ascending ? aValue - bValue : bValue - aValue;
            
            case 'avg-cognitive':
                aValue = parseFloat(a.dataset.avgCognitive || '0');
                bValue = parseFloat(b.dataset.avgCognitive || '0');
                return ascending ? aValue - bValue : bValue - aValue;
            
            case 'function-count':
                aValue = parseInt(a.dataset.functionCount || '0', 10);
                bValue = parseInt(b.dataset.functionCount || '0', 10);
                return ascending ? aValue - bValue : bValue - aValue;
            
            case 'total-sql-blocks':
                aValue = parseInt(a.dataset.totalSqlBlocks || '0', 10);
                bValue = parseInt(b.dataset.totalSqlBlocks || '0', 10);
                return ascending ? aValue - bValue : bValue - aValue;
            
            case 'todos-count':
                aValue = parseInt(a.dataset.todosCount || '0', 10);
                bValue = parseInt(b.dataset.todosCount || '0', 10);
                return ascending ? aValue - bValue : bValue - aValue;
            
            case 'cursor-issues-count':
                aValue = parseInt(a.dataset.cursorIssuesCount || '0', 10);
                bValue = parseInt(b.dataset.cursorIssuesCount || '0', 10);
                return ascending ? aValue - bValue : bValue - aValue;
            
            case 'memory-warnings-count':
                aValue = parseInt(a.dataset.memoryWarningsCount || '0', 10);
                bValue = parseInt(b.dataset.memoryWarningsCount || '0', 10);
                return ascending ? aValue - bValue : bValue - aValue;
            
            default:
                return 0;
        }
    });
    
    // Reorder elements in the DOM
    fileSections.forEach(section => {
        parent.appendChild(section);
    });
}

// Sort select handler
const sortSelect = document.getElementById('file-sort-select');
if (sortSelect) {
    sortSelect.addEventListener('change', function() {
        currentSortCriteria = this.value;
        sortFiles(currentSortCriteria, currentSortAscending);
    });
}

// Sort order button handler
const sortOrderButton = document.getElementById('file-sort-order');
if (sortOrderButton) {
    sortOrderButton.addEventListener('click', function() {
        currentSortAscending = !currentSortAscending;
        const icon = document.getElementById('file-sort-order-icon');
        const text = document.getElementById('file-sort-order-text');
        if (icon) {
            icon.textContent = currentSortAscending ? '↑' : '↓';
        }
        if (text) {
            text.textContent = currentSortAscending ? 'Croissant' : 'Décroissant';
        }
        sortFiles(currentSortCriteria, currentSortAscending);
    });
}

// Apply sorting when filtering changes
const originalFilterFiles = filterFiles;
filterFiles = function(filterText) {
    originalFilterFiles(filterText);
    sortFiles(currentSortCriteria, currentSortAscending);
};

const originalFilterFilesByType = filterFilesByType;
filterFilesByType = function(filterType) {
    originalFilterFilesByType(filterType);
    sortFiles(currentSortCriteria, currentSortAscending);
};

// Apply initial sort on page load
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure all elements are rendered
    setTimeout(() => {
        sortFiles(currentSortCriteria, currentSortAscending);
    }, 100);
});

