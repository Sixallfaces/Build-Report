// Конфигурация API
        const API_CONFIG = {
        BASE_URL: 'https://build-report.ru/',
        ENDPOINTS: {
            WORKS: 'api/works',
            ALL_WORKS: 'api/all-works',
            MATERIALS: 'api/materials',
            MATERIALS_HISTORY: 'api/materials/history',
            MATERIALS_EXPORT: 'api/materials/export',
            MATERIALS_IMPORT: 'api/materials/import',
            MATERIALS_TEMPLATE: 'api/materials/template',
            FOREMEN: 'api/foremen',
            REPORTS: 'api/reports',
            ALL_REPORTS: 'api/all-reports',
            REPORT: 'api/report',
            LOGIN: 'api/site-login',
            CATEGORIES: 'api/categories',
            ACCUMULATIVE: 'api/accumulative-statement',
            WORK_REPORTS: 'api/work-reports'
        }
    };

    function buildApiUrl(endpoint) {
        if (!endpoint) {
            return API_CONFIG.BASE_URL;
        }

        if (/^https?:\/\//i.test(endpoint)) {
            return endpoint;
        }

        const normalizedBase = API_CONFIG.BASE_URL.replace(/\/+$/, '');
        const normalizedPath = String(endpoint).replace(/^\/+/, '');
        return `${normalizedBase}/${normalizedPath}`;
    }

    

    // Переменные состояния
    let works = [];
    let availableReportWorks = [];
    let materials = [];
    let foremen = [];
    let reports = [];
    let allReports = [];
    let categories = [];
    let currentWorkIdForMaterials = null;
    let currentWorkMaterials = [];
    let currentWorkPricing = {
        unitCost: null,
        totalCost: null
    };
    let currentMaterialIdForQuantity = null;
    let currentMaterialQuantity = 0;
    let currentMaterialUnit = '';
    let currentMaterialIdForPricing = null;
    let currentMaterialQuantityForPricing = 0;
    let currentMaterialPricing = {
        unitCost: null,
        totalCost: null
    };
    let materialHistory = [];
    let materialHistoryLoaded = false;
    let isMaterialHistoryView = false;
    let currentForemanIdForSections = null;
    let currentForemanSections = [];
    let currentEditingReportId = null;
    let accumulativeForemen = [];
    let selectedAccumulativeForemanId = null;

    // Конфигурация сортировки таблиц
    const tableSortStates = new Map();

    const sortableTableConfigs = {
        worksTable: {
            columns: {
                1: { type: 'number' },
                2: { type: 'string' },
                3: { type: 'string' },
                4: { type: 'string' },
                5: { type: 'number' },
                6: { type: 'number' },
                7: { type: 'boolean' }
            },
            getRowId: (row) => {
                const input = row.querySelector('td:nth-child(2) input');
                return input ? parseInt(input.value, 10) : null;
            }
        },
        materialsTable: {
            columns: {
                0: { type: 'number' },
                1: { type: 'string' },
                2: { type: 'string' },
                3: { type: 'string' },
                4: { type: 'number' }
            },
            getRowId: (row) => {
                const input = row.querySelector('td:first-child input');
                return input ? parseInt(input.value, 10) : null;
            }
        },
        materialHistoryTable: {
            columns: {
                0: { type: 'number' },
                1: { type: 'string' },
                2: { type: 'string' },
                3: { type: 'number' },
                4: { type: 'number' },
                5: { type: 'string' },
                6: { type: 'string' },
                7: { type: 'date' }
            }
        },
        foremenTable: {
            columns: {
                0: { type: 'number' },
                1: { type: 'string' },
                2: { type: 'string' },
                3: { type: 'string' },
                4: { type: 'date' },
                5: { type: 'boolean' }
            },
            getRowId: (row) => {
                const input = row.querySelector('td:first-child input');
                return input ? parseInt(input.value, 10) : null;
            }
        },
        reportsTable: {
            columns: {
                0: { type: 'number' },
                1: { type: 'number' },
                2: { type: 'number' },
                3: { type: 'number' },
                4: { type: 'date' },
                5: { type: 'string' },
                6: { type: 'string' }
            }
        },
        accumulativeTable: {
            columns: {
                0: { type: 'string' },
                1: { type: 'string' },
                2: { type: 'string' },
                3: { type: 'number' },
                4: { type: 'number' },
                5: { type: 'number' },
                6: { type: 'number' },
                7: { type: 'number' },
                8: { type: 'number' },
                9: { type: 'number' }
            }
        },
        allReportsTable: {
            columns: {
                0: { type: 'number' },
                1: { type: 'string' },
                2: { type: 'string' },
                3: { type: 'string' },
                4: { type: 'number' },
                5: { type: 'date' },
                6: { type: 'string' },
                7: { type: 'string' }
            }
        }
    };

    function refreshTableSorting(tableId) {
        const config = sortableTableConfigs[tableId] || {};
        const columnConfigs = config.columns || {};
        const options = {};

        if (typeof config.getRowId === 'function') {
            options.getRowId = config.getRowId;
        }

        initializeSortableTable(tableId, columnConfigs, options);
    }

    function initializeSortableTable(tableId, columnConfigs = {}, options = {}) {
        const table = document.getElementById(tableId);
        if (!table) {
            return;
        }

        const tbody = table.querySelector('tbody');
        if (!tbody) {
            return;
        }

        const rows = Array.from(tbody.querySelectorAll('tr'));

        rows.forEach((row, index) => {
            if (typeof options.getRowId === 'function') {
                const rowId = options.getRowId(row, index);
                if (rowId !== null && rowId !== undefined && !Number.isNaN(rowId)) {
                    row.dataset.sortId = rowId;
                } else {
                    delete row.dataset.sortId;
                }
            } else {
                delete row.dataset.sortId;
            }
        });

        const state = {
            currentColumn: -1,
            direction: 0,
            columnConfigs,
            getRowId: options.getRowId,
            originalRows: rows.slice()
        };

        tableSortStates.set(tableId, state);

        const headers = table.querySelectorAll('th.sortable');
        headers.forEach(header => {
            header.dataset.tableId = tableId;
            header.dataset.columnIndex = header.cellIndex;
            header.classList.remove('sorted-asc', 'sorted-desc', 'sorted-default');

            if (header.dataset.sortListenerAttached !== 'true') {
                header.addEventListener('click', handleTableSortClick);
                header.dataset.sortListenerAttached = 'true';
            }
        });
    }

    function handleTableSortClick(event) {
        const header = event.currentTarget;
        const tableId = header.dataset.tableId;
        const columnIndex = parseInt(header.dataset.columnIndex, 10);

        if (Number.isNaN(columnIndex)) {
            return;
        }

        sortTable(tableId, columnIndex);
    }

    function sortTable(tableId, columnIndex) {
        const table = document.getElementById(tableId);
        if (!table) {
            return;
        }

        const tbody = table.querySelector('tbody');
        if (!tbody) {
            return;
        }

        const state = tableSortStates.get(tableId);
        if (!state) {
            return;
        }

        const rows = Array.from(tbody.querySelectorAll('tr'));
        const validRows = rows.filter(row => row.cells[columnIndex]);

        if (validRows.length <= 1) {
            return;
        }

        if (!state.originalRows || state.originalRows.length !== rows.length) {
            state.originalRows = rows.slice();
        }

        if (state.currentColumn !== columnIndex) {
            state.currentColumn = columnIndex;
            state.direction = 1;
        } else {
            if (state.direction === 0) {
                state.direction = 1;
            } else if (state.direction === 1) {
                state.direction = -1;
            } else {
                state.direction = 0;
            }
        }

        if (state.direction === 0) {
            state.originalRows.forEach(row => tbody.appendChild(row));
            updateSortIndicators(tableId, columnIndex, state.direction);
            tableSortStates.set(tableId, state);
            return;
        }

        const columnConfig = state.columnConfigs[columnIndex] || {};
        const sortedRows = validRows.slice().sort((a, b) =>
            compareTableCells(a, b, columnIndex, columnConfig, state.direction)
        );

        sortedRows.forEach(row => tbody.appendChild(row));

        // Добавляем обратно строки, которые не участвуют в сортировке (например, с colspan)
        rows
            .filter(row => !validRows.includes(row))
            .forEach(row => tbody.appendChild(row));

        updateSortIndicators(tableId, columnIndex, state.direction);
        tableSortStates.set(tableId, state);
    }

    function compareTableCells(rowA, rowB, columnIndex, columnConfig, direction) {
        const cellA = rowA.cells[columnIndex];
        const cellB = rowB.cells[columnIndex];

        const valueA = getCellSortValue(cellA, columnConfig);
        const valueB = getCellSortValue(cellB, columnConfig);

        let result;

        switch (columnConfig.type) {
            case 'number':
                result = parseNumber(valueA) - parseNumber(valueB);
                break;
            case 'boolean':
                result = parseBoolean(valueA) - parseBoolean(valueB);
                break;
            case 'date':
                result = parseDate(valueA) - parseDate(valueB);
                break;
            default:
                result = String(valueA ?? '').localeCompare(String(valueB ?? ''), 'ru', {
                    sensitivity: 'base',
                    numeric: false
                });
        }

        if (result === 0) {
            const fallbackA = rowA.dataset && rowA.dataset.sortId
                ? parseInt(rowA.dataset.sortId, 10)
                : rowA.rowIndex;
            const fallbackB = rowB.dataset && rowB.dataset.sortId
                ? parseInt(rowB.dataset.sortId, 10)
                : rowB.rowIndex;
            result = fallbackA - fallbackB;
        }

        return result * direction;
    }

    function getCellSortValue(cell, columnConfig) {
        if (!cell) {
            return '';
        }

        if (columnConfig && typeof columnConfig.getValue === 'function') {
            return columnConfig.getValue(cell);
        }

        if (cell.dataset && cell.dataset.sortValue !== undefined) {
            return cell.dataset.sortValue;
        }

        const formElement = cell.querySelector('input, select, textarea');
        if (formElement) {
            return formElement.value;
        }

        return cell.textContent.trim();
    }

    function parseNumber(value) {
        if (typeof value === 'number') {
            return Number.isFinite(value) ? value : 0;
        }

        if (typeof value === 'string') {
            const normalized = value
                .replace(/\u00A0/g, ' ')
                .replace(/\s+/g, '')
                .replace(',', '.');
            const cleaned = normalized.replace(/[^0-9+\-\.]/g, '');
            const parsed = parseFloat(cleaned);
            return Number.isFinite(parsed) ? parsed : 0;
        }

        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : 0;
    }

    function parseBoolean(value) {
        if (typeof value === 'boolean') {
            return value ? 1 : 0;
        }

        if (typeof value === 'number') {
            return value ? 1 : 0;
        }

        const normalized = String(value || '')
            .toLowerCase()
            .trim();

        if (['1', 'true', 'да', 'yes', 'активно', '✅ доступен'].includes(normalized)) {
            return 1;
        }

        return 0;
    }

    function parseDate(value) {
        if (!value) {
            return 0;
        }

        if (value instanceof Date) {
            return value.getTime();
        }

        if (typeof value === 'number') {
            return value;
        }

        if (typeof value === 'string') {
            const normalized = value.replace(' ', 'T');
            const timestamp = Date.parse(normalized);
            return Number.isNaN(timestamp) ? 0 : timestamp;
        }

        return 0;
    }

    function updateSortIndicators(tableId, columnIndex, direction) {
        const table = document.getElementById(tableId);
        if (!table) {
            return;
        }

        const headers = table.querySelectorAll('th.sortable');
        headers.forEach(header => {
            header.classList.remove('sorted-asc', 'sorted-desc', 'sorted-default');
        });

        const targetHeader = Array.from(headers).find(header =>
            parseInt(header.dataset.columnIndex, 10) === columnIndex
        );

        if (!targetHeader) {
            return;
        }

        if (direction === 1) {
            targetHeader.classList.add('sorted-asc');
        } else if (direction === -1) {
            targetHeader.classList.add('sorted-desc');
        } else {
            targetHeader.classList.add('sorted-default');
        }
    }

    // Переменные для модального окна добавления баланса
    let currentWorkIdForBalance = null;
    let currentWorkBalance = 0;
    
    // Предопределенные значения
    const UNITS = ['шт', 'м', 'м²', 'м³', 'кг', 'т', 'л', 'п.м.', 'комплект'];

    // ФУНКЦИИ АВТОРИЗАЦИИ
    async function login() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorElement = document.getElementById('loginError');
        
        // Базовая валидация
        if (!username || !password) {
            errorElement.textContent = 'Введите логин и пароль';
            errorElement.style.display = 'block';
            return;
        }
        
        try {
            const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.LOGIN), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                let errorMessage = 'Неверный логин или пароль';

                try {
                    const errorData = await response.json();

                    if (errorData?.error) {
                        errorMessage = errorData.error;
                    } else if (errorData?.detail) {
                        errorMessage = Array.isArray(errorData.detail)
                            ? errorData.detail.map(item => item.msg || item).join(', ')
                            : errorData.detail;
                    }
                } catch (parseError) {
                    console.error('Login error parse failed:', parseError);
                }

                errorElement.textContent = errorMessage;
                errorElement.style.display = 'block';
                document.getElementById('password').value = '';
                return;
            }

            const data = await response.json();
            
            if (data.success) {
                // Сохраняем данные авторизации
                localStorage.setItem('authenticated', 'true');
                localStorage.setItem('user', JSON.stringify(data.user));
                localStorage.setItem('token', data.token || '');
                
                // Скрываем форму входа и показываем основной контент
                document.getElementById('loginOverlay').style.display = 'none';
                document.getElementById('mainContent').style.display = 'block';
                
                // Инициализируем приложение
                initializeApp();
            } else {
                errorElement.textContent = data.error || 'Неверный логин или пароль';
                errorElement.style.display = 'block';
                
                // Очищаем поле пароля
                document.getElementById('password').value = '';
            }
        } catch (error) {
            console.error('Login error:', error);
            errorElement.textContent = 'Ошибка подключения к серверу';
            errorElement.style.display = 'block';
            
            // Очищаем поле пароля
            document.getElementById('password').value = '';
        }
    }

    // Проверка авторизации при загрузке страницы
    function checkAuth() {
        const isAuthenticated = localStorage.getItem('authenticated') === 'true';
        
        if (isAuthenticated) {
            // Проверяем, не истек ли токен (если используется)
            const token = localStorage.getItem('token');
            const user = localStorage.getItem('user');
            
            if (token && user) {
                document.getElementById('loginOverlay').style.display = 'none';
                document.getElementById('mainContent').style.display = 'block';
                initializeApp();
            } else {
                // Если данных нет, показываем форму входа
                showLoginForm();
            }
        } else {
            showLoginForm();
        }
    }

    // Функция показа формы входа
    function showLoginForm() {
        document.getElementById('loginOverlay').style.display = 'flex';
        document.getElementById('mainContent').style.display = 'none';
        
        // Очищаем поля формы
        document.getElementById('username').value = '';
        document.getElementById('password').value = '';
        document.getElementById('loginError').style.display = 'none';
        
        // Фокус на поле логина
        document.getElementById('username').focus();
    }

    // Функция выхода
    function logout() {
        localStorage.removeItem('authenticated');
        localStorage.removeItem('user');
        localStorage.removeItem('token');
        showLoginForm();
    }

    // ИСПРАВЛЕННАЯ ФУНКЦИЯ ДЛЯ API ЗАПРОСОВ
    async function makeApiRequest(endpoint, options = {}) {
        const token = localStorage.getItem('token');

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        try {
            const url = buildApiUrl(endpoint);
            const response = await fetch(url, {
                headers,
                ...options
            });
            
            if (response.status === 401) {
                logout();
                return { success: false, error: 'Сессия истекла' };
            }
            
            // Проверяем, что ответ успешный
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`API Error: ${response.status} - ${errorText}`);
                return { 
                    success: false, 
                    error: `HTTP ${response.status}: ${errorText || 'Unknown error'}` 
                };
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('API Request failed:', error);
            return { 
                success: false, 
                error: `Network error: ${error.message}` 
            };
        }
    }

    function getCurrentUsername() {
        try {
            const userRaw = localStorage.getItem('user');
            if (!userRaw) {
                return 'Неизвестный пользователь';
            }
            const user = JSON.parse(userRaw);
            return user?.username || user?.login || user?.name || 'Неизвестный пользователь';
        } catch (error) {
            console.error('Не удалось определить имя пользователя:', error);
            return 'Неизвестный пользователь';
        }
    }


    // Обработчик нажатия Enter в форме входа
    document.addEventListener('DOMContentLoaded', function() {
        // Добавляем обработчики для полей ввода
        document.getElementById('username').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                login();
            }
        });
        
        document.getElementById('password').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                login();
            }
        });
        
        // Проверяем авторизацию при загрузке
        checkAuth();
    });

    // Основная функция инициализации
    function initializeApp() {
        initializeTabs();
        initializeWorksTab();
        initializeWorkMaterialsModal();
        initializeMaterialPricingModal();
        initializeMaterialsTab();
        initializeForemenTab();
        initializeReportsTab();
        initializeAllReportsTab();
        initializeSendReportFeature();
        initializeEditReportFeature();
        initializeAccumulativeTab();

        // Загрузка данных
        loadWorks();
        loadMaterials();
        loadForemen();
        loadReports();
        loadAllReports();
        loadCategories();
    }
    
    // Инициализация вкладок
    function initializeTabs() {
        const tabs = document.querySelectorAll('.tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const tabId = this.getAttribute('data-tab');
                
                // Деактивировать все вкладки
                tabs.forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                // Активировать выбранную вкладку
                this.classList.add('active');
                document.getElementById(tabId).classList.add('active');

                // Загружать данные при переключении на определенные вкладки
                if (tabId === 'accumulative') {
                    loadAccumulativeStatement();
                } else if (tabId === 'materials') {
                    loadMaterials();
                }
            });
        });
    }
    
    // Инициализация вкладки работ
    function initializeWorksTab() {
        document.getElementById('addWork').addEventListener('click', addNewWork);
        document.getElementById('addCategory').addEventListener('click', openCategoryModal);
        document.getElementById('saveAllWorks').addEventListener('click', saveAllWorks);
        document.getElementById('searchWorks').addEventListener('input', filterWorks);

        document.getElementById('exportWorks').addEventListener('click', exportWorksToExcel);
        document.getElementById('importWorks').addEventListener('click', triggerImportWorks);
        document.getElementById('importFileInput').addEventListener('change', handleWorksImport);
    }

    function initializeWorkMaterialsModal() {
        const addButton = document.getElementById('workMaterialAddButton');
        if (addButton) {
            addButton.addEventListener('click', event => {
                event.preventDefault();
                addMaterialToWorkList();
            });
        }

        const pricingInputs = [
            { id: 'workPriceUnit', field: 'unitCost' },
            { id: 'workPriceTotal', field: 'totalCost' }
        ];

        pricingInputs.forEach(({ id, field }) => {
            const input = document.getElementById(id);
            if (!input) return;

            input.addEventListener('input', event => {
                handlePricingInput(field, event.target.value);
                updateWorkPricingInputs(id);
            });

            input.addEventListener('blur', () => {
                updateWorkPricingInputs();
            });
        });

        // Не закрываем модальное окно при клике на фон
        const modal = document.getElementById('workMaterialsModal');
        if (modal) {
            modal.addEventListener('click', event => {
                if (event.target === modal) {
                    event.stopPropagation();
                }
            });
        }
    }

    function initializeMaterialPricingModal() {
        const pricingInputs = [
            { id: 'materialPriceUnit', field: 'unitCost' }
        ];

        pricingInputs.forEach(({ id, field }) => {
            const input = document.getElementById(id);
            if (!input) return;

            input.addEventListener('input', event => {
                handleMaterialPricingInput(field, event.target.value);
                updateMaterialPricingInputs(id);
            });

            input.addEventListener('blur', () => {
                updateMaterialPricingInputs();
            });
        });

        const saveButton = document.getElementById('materialPricingSaveButton');
        if (saveButton) {
            saveButton.addEventListener('click', event => {
                event.preventDefault();
                saveMaterialPricing();
            });
        }

        const modal = document.getElementById('materialPricingModal');
        if (modal) {
            modal.addEventListener('click', event => {
                if (event.target === modal) {
                    event.stopPropagation();
                }
            });
        }
    }

    function initializeMaterialsTab() {
        const addMaterialBtn = document.getElementById('addMaterial');
        const exportMaterialsBtn = document.getElementById('exportMaterials');
        const importMaterialsBtn = document.getElementById('importMaterials');
        const toggleHistoryBtn = document.getElementById('toggleMaterialsHistory');
        const importInput = document.getElementById('materialsImportInput');
        const searchInput = document.getElementById('searchMaterials');

        if (addMaterialBtn) addMaterialBtn.addEventListener('click', addNewMaterial);
        if (exportMaterialsBtn) exportMaterialsBtn.addEventListener('click', exportMaterialsToExcel);
        if (importMaterialsBtn) importMaterialsBtn.addEventListener('click', triggerImportMaterials);
        if (toggleHistoryBtn) toggleHistoryBtn.addEventListener('click', toggleMaterialHistoryView);
        if (importInput) importInput.addEventListener('change', handleMaterialsImport);
        if (searchInput) searchInput.addEventListener('input', filterMaterials);
    }

    // Инициализация вкладки бригадиров
    function initializeForemenTab() {
        document.getElementById('saveAllForemen').addEventListener('click', saveAllForemen);
        document.getElementById('searchForemen').addEventListener('input', filterForemen);
    }
    
    // Инициализация вкладки отчетов
    function initializeReportsTab() {
        document.getElementById('addReport').addEventListener('click', addNewReport);
        document.getElementById('saveAllReports').addEventListener('click', saveAllReports);
        document.getElementById('searchReports').addEventListener('input', filterReports);
    }

    // Инициализация вкладки всех отчетов
    function initializeAllReportsTab() {
        document.getElementById('refreshAllReports').addEventListener('click', loadAllReports);
        document.getElementById('searchAllReports').addEventListener('input', filterAllReports);
    }

    function initializeSendReportFeature() {
        const openButton = document.getElementById('openSendReportModal');
        if (openButton) {
            openButton.addEventListener('click', () => {
                openSendReportModal();
            });
        }

        // Не закрываем модальное окно при клике на фон
        const modal = document.getElementById('sendReportModal');
        if (modal) {
            modal.addEventListener('click', event => {
                if (event.target === modal) {
                    event.stopPropagation();
                }
            });
        }

        const form = document.getElementById('sendReportForm');
        if (form) {
            form.addEventListener('submit', submitSendReport);
        }

        const addWorkButton = document.getElementById('addReportWorkButton');
        if (addWorkButton) {
            addWorkButton.addEventListener('click', () => addReportWorkItem());
        }
    }

    async function openSendReportModal() {
        const modal = document.getElementById('sendReportModal');
        if (!modal) return;

        try {
            if (!Array.isArray(foremen) || foremen.length === 0) {
                await loadForemen();
            }
        } catch (error) {
            console.error('Не удалось обновить список бригадиров перед отправкой отчета:', error);
        }

        try {
            if (!Array.isArray(works) || works.length === 0) {
                await loadWorks();
            }
        } catch (error) {
            console.error('Не удалось обновить список работ перед отправкой отчета:', error);
        }

        const availability = populateSendReportOptions();
        resetSendReportForm();
        updateSendReportAvailabilityMessage(availability);

        const submitButton = document.getElementById('submitReportButton');
        if (submitButton) {
            submitButton.disabled = !(availability.hasForemen && availability.hasWorks);
        }

        modal.style.display = 'flex';
    }

    function closeSendReportModal() {
        const modal = document.getElementById('sendReportModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    function updateReportWorkSelectOptions(selectElement, selectedValue) {
        if (!selectElement) return;

        const currentValue = selectedValue !== undefined ? selectedValue : selectElement.value;
        const options = ['<option value="">Выберите работу</option>'];

        availableReportWorks.forEach(item => {
            const sectionName = item['Раздел'] || item['Категория'] || '';
            const categoryLabel = sectionName ? ` — ${sectionName}` : '';
            options.push(`<option value="${item.id}">${item['Название работы'] || item.id}${categoryLabel}</option>`);
        });

        selectElement.innerHTML = options.join('');

        if (currentValue) {
            selectElement.value = String(currentValue);
            if (selectElement.value !== String(currentValue)) {
                selectElement.value = '';
            }
        }

        selectElement.disabled = availableReportWorks.length === 0;
    }

    function updateReportWorkItemDetails(itemElement) {
        if (!itemElement) return;

        const selectElement = itemElement.querySelector('.report-work-select');
        const detailsElement = itemElement.querySelector('.report-work-details');
        const unitElement = itemElement.querySelector('.report-work-unit');
        const quantityInput = itemElement.querySelector('.report-work-quantity');

        const workId = selectElement ? parseInt(selectElement.value, 10) : NaN;
        if (!Number.isInteger(workId)) {
            if (detailsElement) {
                detailsElement.textContent = 'Выберите работу, чтобы увидеть доступный баланс и единицу измерения.';
            }
            if (unitElement) {
                unitElement.textContent = '';
            }
            if (quantityInput) {
                quantityInput.placeholder = 'Количество';
            }
            return;
        }

        const work = Array.isArray(works) ? works.find(item => item && item.id === workId) : null;
        if (!work) {
            if (detailsElement) {
                detailsElement.textContent = 'Не удалось найти данные о выбранной работе.';
            }
            if (unitElement) {
                unitElement.textContent = '';
            }
            if (quantityInput) {
                quantityInput.placeholder = 'Количество';
            }
            return;
        }

        const unit = work['Единица измерения'] || 'шт';
        const balanceRaw = work['На балансе'];
        const balanceNumber = typeof balanceRaw === 'number' ? balanceRaw : parseFloat(balanceRaw) || 0;
        const formattedBalance = Number.isFinite(balanceNumber)
            ? balanceNumber.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
            : balanceRaw;
        const category = work['Раздел'] || work['Категория'] || '—';

        if (detailsElement) {
            detailsElement.textContent = `Раздел: ${category} • На балансе: ${formattedBalance} ${unit}`;
        }

        if (unitElement) {
            unitElement.textContent = unit;
        }

        if (quantityInput) {
            quantityInput.placeholder = `Количество (${unit})`;
        }
    }

    function updateRemoveReportWorkButtonsState() {
        const container = document.getElementById('reportWorksContainer');
        if (!container) return;

        const items = Array.from(container.querySelectorAll('.report-work-item'));
        const shouldDisable = items.length <= 1;

        items.forEach(item => {
            const button = item.querySelector('.remove-report-work-button');
            if (button) {
                button.disabled = shouldDisable;
                button.style.display = shouldDisable ? 'none' : '';
            }
        });
    }

    function removeReportWorkItem(itemElement) {
        const container = document.getElementById('reportWorksContainer');
        if (!container || !itemElement) return;

        container.removeChild(itemElement);
        updateRemoveReportWorkButtonsState();
    }

    function addReportWorkItem(selectedWorkId) {
        const container = document.getElementById('reportWorksContainer');
        if (!container) return;

        const itemElement = document.createElement('div');
        itemElement.className = 'report-work-item';

        const selectElement = document.createElement('select');
        selectElement.className = 'report-work-select';
        selectElement.required = true;
        updateReportWorkSelectOptions(selectElement, selectedWorkId);
        selectElement.addEventListener('change', () => updateReportWorkItemDetails(itemElement));

        const quantityWrapper = document.createElement('div');
        quantityWrapper.className = 'quantity-input-wrapper';

        const quantityInput = document.createElement('input');
        quantityInput.type = 'number';
        quantityInput.min = '0';
        quantityInput.step = '0.01';
        quantityInput.placeholder = 'Количество';
        quantityInput.required = true;
        quantityInput.className = 'report-work-quantity';

        const unitElement = document.createElement('span');
        unitElement.className = 'report-work-unit';

        quantityWrapper.appendChild(quantityInput);
        quantityWrapper.appendChild(unitElement);

        const detailsElement = document.createElement('p');
        detailsElement.className = 'modal-note report-work-details';
        detailsElement.textContent = 'Выберите работу, чтобы увидеть доступный баланс и единицу измерения.';

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'secondary remove-report-work-button';
        removeButton.textContent = 'Удалить';
        removeButton.addEventListener('click', () => removeReportWorkItem(itemElement));

        itemElement.appendChild(selectElement);
        itemElement.appendChild(quantityWrapper);
        itemElement.appendChild(detailsElement);
        itemElement.appendChild(removeButton);

        container.appendChild(itemElement);

        updateReportWorkItemDetails(itemElement);
        updateRemoveReportWorkButtonsState();
    }

    function resetSendReportForm() {
        const form = document.getElementById('sendReportForm');
        if (form) {
            form.reset();
        }

        const now = new Date();
        const dateInput = document.getElementById('reportDate');
        const timeInput = document.getElementById('reportTime');

        if (dateInput) {
            dateInput.value = now.toISOString().slice(0, 10);
        }

        if (timeInput) {
            timeInput.value = now.toTimeString().slice(0, 8);
        }

        const container = document.getElementById('reportWorksContainer');
        if (container) {
            container.innerHTML = '';
            addReportWorkItem();
        }

        const addButton = document.getElementById('addReportWorkButton');
        if (addButton) {
            addButton.disabled = availableReportWorks.length === 0;
        }

        updateRemoveReportWorkButtonsState();
    }

    function populateSendReportOptions() {
        const foremanSelect = document.getElementById('reportForemanSelect');

        let hasForemen = false;
        let hasWorks = false;

        if (foremanSelect) {
            const availableForemen = (Array.isArray(foremen) ? foremen : [])
                .filter(item => item && (item.is_active === undefined || item.is_active));

            if (availableForemen.length > 0) {
                const options = ['<option value="">Выберите бригадира</option>'].concat(
                    availableForemen
                        .slice()
                        .sort((a, b) => (a.full_name || '').localeCompare(b.full_name || ''))
                        .map(item => {
                            const position = item.position ? ` • ${item.position}` : '';
                            return `<option value="${item.id}">${item.full_name || item.id}${position}</option>`;
                        })
                );
                foremanSelect.innerHTML = options.join('');
                foremanSelect.disabled = false;
                hasForemen = true;
            } else {
                foremanSelect.innerHTML = '<option value="">Нет доступных бригадиров</option>';
                foremanSelect.disabled = true;
            }
        }

        availableReportWorks = (Array.isArray(works) ? works : [])
            .filter(item => item && (item.is_active === undefined ? true : Boolean(item.is_active)))
            .slice()
            .sort((a, b) => (a['Название работы'] || '').localeCompare(b['Название работы'] || ''));

        hasWorks = availableReportWorks.length > 0;

        const container = document.getElementById('reportWorksContainer');
        if (container) {
            container.querySelectorAll('.report-work-select').forEach(select => {
                updateReportWorkSelectOptions(select);
                const itemElement = select.closest('.report-work-item');
                if (itemElement) {
                    updateReportWorkItemDetails(itemElement);
                }
            });
        }

        const addButton = document.getElementById('addReportWorkButton');
        if (addButton) {
            addButton.disabled = !hasWorks;
        }

        return { hasForemen, hasWorks };
    }

    function updateSendReportAvailabilityMessage(availability) {
        const messageElement = document.getElementById('sendReportAvailabilityMessage');
        if (!messageElement) return;

        if (!availability.hasForemen && !availability.hasWorks) {
            messageElement.textContent = 'Нет активных бригадиров и работ. Добавьте данные в соответствующих разделах, чтобы отправить отчет.';
            messageElement.style.display = 'block';
            return;
        }

        if (!availability.hasForemen) {
            messageElement.textContent = 'Нет доступных активных бригадиров. Добавьте или разблокируйте бригадира в разделе «Бригадиры».';
            messageElement.style.display = 'block';
            return;
        }

        if (!availability.hasWorks) {
            messageElement.textContent = 'Нет доступных активных работ. Добавьте работу или включите существующую в разделе «Работы и материалы».';
            messageElement.style.display = 'block';
            return;
        }

        messageElement.textContent = '';
        messageElement.style.display = 'none';
    }

    async function submitSendReport(event) {
        event.preventDefault();

        const foremanSelect = document.getElementById('reportForemanSelect');
        const dateInput = document.getElementById('reportDate');
        const timeInput = document.getElementById('reportTime');
        const container = document.getElementById('reportWorksContainer');
        const submitButton = document.getElementById('submitReportButton');

        if (submitButton) {
            submitButton.disabled = true;
        }

        try {
            const foremanIdValue = foremanSelect ? parseInt(foremanSelect.value, 10) : NaN;

            if (!Number.isInteger(foremanIdValue)) {
                showNotification('Выберите бригадира для отчета', 'error');
                return;
            }

            const now = new Date();
            const reportDate = (dateInput && dateInput.value) ? dateInput.value : now.toISOString().slice(0, 10);
            let reportTime = (timeInput && timeInput.value) ? timeInput.value : now.toTimeString().slice(0, 8);
            if (reportTime.length === 5) {
                reportTime += ':00';
            }

            const workItems = container ? Array.from(container.querySelectorAll('.report-work-item')) : [];
            if (workItems.length === 0) {
                showNotification('Добавьте хотя бы одну работу для отчета', 'error');
                return;
            }

            const worksPayload = [];
            const usedWorkIds = new Set();

            for (const item of workItems) {
                const selectElement = item.querySelector('.report-work-select');
                const quantityInput = item.querySelector('.report-work-quantity');

                const workIdValue = selectElement ? parseInt(selectElement.value, 10) : NaN;
                const quantityValue = quantityInput ? parseFloat(String(quantityInput.value).replace(',', '.')) : NaN;

                if (!Number.isInteger(workIdValue)) {
                    showNotification('Выберите работу для каждого отчета', 'error');
                    return;
                }

                if (usedWorkIds.has(workIdValue)) {
                    showNotification('Каждая работа должна быть выбрана только один раз', 'error');
                    return;
                }

                if (!Number.isFinite(quantityValue) || quantityValue <= 0) {
                    showNotification('Введите количество выполненной работы для каждой выбранной позиции', 'error');
                    return;
                }

                usedWorkIds.add(workIdValue);
                worksPayload.push({ work_id: workIdValue, quantity: quantityValue });
            }

            if (worksPayload.length === 0) {
                showNotification('Добавьте хотя бы одну работу для отчета', 'error');
                return;
            }

            const payload = {
                foreman_id: foremanIdValue,
                report_date: reportDate,
                report_time: reportTime,
                works: worksPayload
            };

            const response = await makeApiRequest(API_CONFIG.ENDPOINTS.WORK_REPORTS, {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            if (!response || !response.success) {
                const errorMessage = response?.error || response?.detail || 'Не удалось отправить отчет';
                showNotification(errorMessage, 'error');
                return;
            }

            showNotification('Отчет успешно отправлен', 'success');
            closeSendReportModal();

            await loadWorks();
            await loadAllReports();
        } catch (error) {
            console.error('Ошибка при отправке отчета:', error);
            showNotification('Ошибка при отправке отчета: ' + error.message, 'error');
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
            }
        }
    }

    function initializeEditReportFeature() {
        // Не закрываем модальное окно при клике на фон
        const modal = document.getElementById('editReportModal');
        if (modal) {
            modal.addEventListener('click', event => {
                if (event.target === modal) {
                    event.stopPropagation();
                }
            });
        }

        const cancelButton = document.getElementById('cancelEditReportButton');
        if (cancelButton) {
            cancelButton.addEventListener('click', closeEditReportModal);
        }

        const workSelect = document.getElementById('editReportWorkSelect');
        if (workSelect) {
            workSelect.addEventListener('change', () => {
                const selectedId = parseInt(workSelect.value, 10);
                updateEditReportWorkDetails(Number.isInteger(selectedId) ? selectedId : null);
            });
        }

        const form = document.getElementById('editReportForm');
        if (form) {
            form.addEventListener('submit', submitEditReportForm);
        }
    }

    function showEditReportError(message) {
        const errorElement = document.getElementById('editReportError');
        if (!errorElement) {
            return;
        }

        if (message) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        } else {
            errorElement.textContent = '';
            errorElement.style.display = 'none';
        }
    }

    function closeEditReportModal() {
        const modal = document.getElementById('editReportModal');
        if (modal) {
            modal.style.display = 'none';
        }

        const form = document.getElementById('editReportForm');
        if (form) {
            form.reset();
        }

        showEditReportError('');
        currentEditingReportId = null;

        const unitElement = document.getElementById('editReportWorkUnit');
        if (unitElement) {
            unitElement.textContent = '';
        }

        const detailsElement = document.getElementById('editReportWorkDetails');
        if (detailsElement) {
            detailsElement.textContent = 'Выберите работу, чтобы увидеть детали.';
        }
    }

    function populateEditReportForemanSelect(selectedId) {
        const select = document.getElementById('editReportForemanSelect');
        if (!select) {
            return;
        }

        const availableForemen = (Array.isArray(foremen) ? foremen : [])
            .filter(item => item && (item.is_active === undefined || item.is_active));

        if (availableForemen.length === 0) {
            select.innerHTML = '<option value="">Нет доступных бригадиров</option>';
            select.disabled = true;
            return;
        }

        const options = ['<option value="">Выберите бригадира</option>'].concat(
            availableForemen
                .slice()
                .sort((a, b) => (a.full_name || '').localeCompare(b.full_name || ''))
                .map(item => {
                    const position = item.position ? ` • ${item.position}` : '';
                    return `<option value="${item.id}">${item.full_name || item.id}${position}</option>`;
                })
        );

        select.innerHTML = options.join('');
        select.disabled = false;

        if (selectedId) {
            select.value = String(selectedId);
            if (select.value !== String(selectedId)) {
                select.value = '';
            }
        }
    }

    function populateEditReportWorkSelect(selectedId) {
        const select = document.getElementById('editReportWorkSelect');
        if (!select) {
            return;
        }

        const availableWorks = (Array.isArray(works) ? works : [])
            .filter(item => item && (item.is_active === undefined ? true : Boolean(item.is_active)));

        if (availableWorks.length === 0) {
            select.innerHTML = '<option value="">Нет доступных работ</option>';
            select.disabled = true;
            return;
        }

        const options = ['<option value="">Выберите работу</option>'].concat(
            availableWorks
                .slice()
                .sort((a, b) => (a['Название работы'] || '').localeCompare(b['Название работы'] || ''))
                .map(item => {
                    const sectionName = item['Раздел'] || item['Категория'] || '';
                    const category = sectionName ? ` • ${sectionName}` : '';
                    return `<option value="${item.id}">${item['Название работы'] || item.id}${category}</option>`;
                })
        );

        select.innerHTML = options.join('');
        select.disabled = false;

        if (selectedId) {
            select.value = String(selectedId);
            if (select.value !== String(selectedId)) {
                select.value = '';
            }
        }
    }

    function updateEditReportWorkDetails(workId) {
        const detailsElement = document.getElementById('editReportWorkDetails');
        const unitElement = document.getElementById('editReportWorkUnit');
        const quantityInput = document.getElementById('editReportQuantity');

        if (!Number.isInteger(workId)) {
            if (detailsElement) {
                detailsElement.textContent = 'Выберите работу, чтобы увидеть детали.';
            }
            if (unitElement) {
                unitElement.textContent = '';
            }
            if (quantityInput) {
                quantityInput.placeholder = 'Количество';
            }
            return;
        }

        const work = Array.isArray(works) ? works.find(item => item && item.id === workId) : null;
        if (!work) {
            if (detailsElement) {
                detailsElement.textContent = 'Не удалось найти данные о выбранной работе.';
            }
            if (unitElement) {
                unitElement.textContent = '';
            }
            if (quantityInput) {
                quantityInput.placeholder = 'Количество';
            }
            return;
        }

        const unit = work['Единица измерения'] || 'шт';
        const balanceRaw = work['На балансе'];
        const balanceNumber = typeof balanceRaw === 'number' ? balanceRaw : parseFloat(balanceRaw);
        const formattedBalance = Number.isFinite(balanceNumber)
            ? balanceNumber.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
            : (balanceRaw || '0');
        const category = work['Раздел'] || work['Категория'] || '—';

        if (detailsElement) {
            detailsElement.textContent = `Раздел: ${category} • На балансе: ${formattedBalance} ${unit}`;
        }

        if (unitElement) {
            unitElement.textContent = unit;
        }

        if (quantityInput) {
            quantityInput.placeholder = `Количество (${unit})`;
        }
    }

    async function editReport(reportId) {
        const modal = document.getElementById('editReportModal');
        if (!modal) {
            showNotification('Окно редактирования недоступно', 'error');
            return;
        }

        showEditReportError('');
        currentEditingReportId = reportId;

        const saveButton = document.getElementById('saveEditReportButton');
        if (saveButton) {
            saveButton.disabled = true;
        }

        try {
            if (!Array.isArray(foremen) || foremen.length === 0) {
                await loadForemen();
            }

            if (!Array.isArray(works) || works.length === 0) {
                await loadWorks();
            }
        } catch (error) {
            console.error('Не удалось обновить данные перед редактированием отчета:', error);
        }

        populateEditReportForemanSelect(null);
        populateEditReportWorkSelect(null);
        updateEditReportWorkDetails(null);

        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.REPORT}/${reportId}`);

            if (!response || !response.success || !response.data) {
                const errorMessage = response?.error || response?.detail || 'Не удалось загрузить данные отчета';
                showNotification(errorMessage, 'error');
                currentEditingReportId = null;
                return;
            }

            const reportData = response.data;

            populateEditReportForemanSelect(reportData.foreman_id);
            populateEditReportWorkSelect(reportData.work_id);

            const workId = Number.isInteger(reportData.work_id) ? reportData.work_id : parseInt(reportData.work_id, 10);
            updateEditReportWorkDetails(Number.isInteger(workId) ? workId : null);

            const quantityInput = document.getElementById('editReportQuantity');
            if (quantityInput) {
                quantityInput.value = reportData.quantity ?? '';
            }

            const dateInput = document.getElementById('editReportDate');
            if (dateInput) {
                dateInput.value = reportData.report_date || '';
            }

            const timeInput = document.getElementById('editReportTime');
            if (timeInput) {
                const timeValue = (reportData.report_time || '').toString();
                timeInput.value = timeValue.length > 8 ? timeValue.slice(0, 8) : timeValue;
            }

            const photoInput = document.getElementById('editReportPhoto');
            if (photoInput) {
                photoInput.value = reportData.photo_report_url || '';
            }

            const foremanSelect = document.getElementById('editReportForemanSelect');
            if (foremanSelect && reportData.foreman_id) {
                foremanSelect.value = String(reportData.foreman_id);
                if (foremanSelect.value !== String(reportData.foreman_id)) {
                    foremanSelect.value = '';
                }
            }

            const workSelect = document.getElementById('editReportWorkSelect');
            if (workSelect && reportData.work_id) {
                workSelect.value = String(reportData.work_id);
                if (workSelect.value !== String(reportData.work_id)) {
                    workSelect.value = '';
                }
            }

            modal.style.display = 'flex';
        } catch (error) {
            console.error('Ошибка загрузки отчета:', error);
            showNotification('Ошибка при загрузке отчета: ' + error.message, 'error');
            currentEditingReportId = null;
        } finally {
            if (saveButton) {
                saveButton.disabled = false;
            }
        }
    }

    async function submitEditReportForm(event) {
        event.preventDefault();

        if (!currentEditingReportId) {
            showNotification('Отчет для редактирования не выбран', 'error');
            return;
        }

        const foremanSelect = document.getElementById('editReportForemanSelect');
        const workSelect = document.getElementById('editReportWorkSelect');
        const quantityInput = document.getElementById('editReportQuantity');
        const dateInput = document.getElementById('editReportDate');
        const timeInput = document.getElementById('editReportTime');
        const photoInput = document.getElementById('editReportPhoto');
        const saveButton = document.getElementById('saveEditReportButton');

        const foremanId = foremanSelect ? parseInt(foremanSelect.value, 10) : NaN;
        const workId = workSelect ? parseInt(workSelect.value, 10) : NaN;
        const quantityValue = quantityInput ? parseFloat(quantityInput.value) : NaN;
        const reportDate = dateInput ? dateInput.value : '';
        const reportTime = timeInput ? timeInput.value : '';
        const photoUrl = photoInput ? photoInput.value.trim() : '';

        if (!Number.isInteger(foremanId)) {
            showEditReportError('Выберите бригадира');
            return;
        }

        if (!Number.isInteger(workId)) {
            showEditReportError('Выберите работу');
            return;
        }

        if (!Number.isFinite(quantityValue) || quantityValue <= 0) {
            showEditReportError('Введите корректное количество (больше 0)');
            return;
        }

        if (!reportDate) {
            showEditReportError('Укажите дату отчета');
            return;
        }

        if (!reportTime) {
            showEditReportError('Укажите время отчета');
            return;
        }

        showEditReportError('');

        const payload = {
            foreman_id: foremanId,
            work_id: workId,
            quantity: quantityValue,
            report_date: reportDate,
            report_time: reportTime
        };

        if (photoUrl) {
            payload.photo_report_url = photoUrl;
        }

        if (saveButton) {
            saveButton.disabled = true;
        }

        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.REPORT}/${currentEditingReportId}`, {
                method: 'PUT',
                body: JSON.stringify(payload)
            });

            if (!response || !response.success) {
                const errorMessage = response?.error || response?.detail || 'Не удалось сохранить изменения отчета';
                showEditReportError(errorMessage);
                return;
            }

            const successMessage = response.message || 'Отчет успешно обновлен';
            showNotification(successMessage, 'success');
            closeEditReportModal();

            await loadWorks();
            await loadAllReports();
        } catch (error) {
            console.error('Ошибка при сохранении отчета:', error);
            showEditReportError('Ошибка при сохранении отчета: ' + error.message);
        } finally {
            if (saveButton) {
                saveButton.disabled = false;
            }
        }
    }

    // ========== РАБОТЫ ==========

    // Загрузка работ
    async function loadWorks() {
        const loadingElement = document.getElementById('worksLoading');
        const tableBody = document.getElementById('worksTableBody');
        
        loadingElement.style.display = 'block';
        tableBody.innerHTML = '';
        
        try {
            const data = await makeApiRequest('/api/all-works');
            
            if (data.success) {
                works = data.data || [];
                displayWorks(works);
            } else {
                showNotification('Ошибка при загрузке работ: ' + data.error, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при загрузке работ: ' + error.message, 'error');
        } finally {
            loadingElement.style.display = 'none';
        }
    }
    
    // Отображение работ
    function displayWorks(worksToDisplay) {
        const tableBody = document.getElementById('worksTableBody');
        tableBody.innerHTML = '';
        
        if (worksToDisplay.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Нет данных о работах</td></tr>';
            refreshTableSorting('worksTable');
            return;
        }
        
        worksToDisplay.forEach(work => {
            const sectionName = work.Раздел || work['Категория'] || '';
            const categoryOptions = categories.map(cat =>
                `<option value="${cat.name}" ${cat.name === sectionName ? 'selected' : ''}>${cat.name}</option>`
            ).join('');
            const fallbackCategoryOption = sectionName && !categories.find(c => c.name === sectionName)
                ? `<option value="${sectionName}" selected>${sectionName}</option>`
                : '';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="checkbox-cell">
                    <input type="checkbox" class="work-checkbox" value="${work.id}">
                </td>
                <td><input type="text" value="${work.id}" readonly></td>
                <td>
                    <select class="editable" data-field="category">
                        ${categoryOptions}
                        ${fallbackCategoryOption}
                    </select>
                </td>
                <td><input type="text" value="${work['Название работы']}" class="editable" data-field="name"></td>
                <td>
                    <select class="editable" data-field="unit">
                        ${UNITS.map(unit => 
                            `<option value="${unit}" ${unit === work['Единица измерения'] ? 'selected' : ''}>${unit}</option>`
                        ).join('')}
                        <option value="${work['Единица измерения']}" ${!UNITS.includes(work['Единица измерения']) ? 'selected' : ''}>${work['Единица измерения']}</option>
                    </select>
                </td>
                <td><input type="number" value="${work['На балансе']}" class="editable" data-field="balance" step="1"></td>
                <td><input type="number" value="${work['Проект'] || 0}" class="editable" data-field="project_total" step="1"></td>
                <td>
                    <select class="editable" data-field="is_active">
                        <option value="1" ${work.is_active ? 'selected' : ''}>Да</option>
                        <option value="0" ${!work.is_active ? 'selected' : ''}>Нет</option>
                    </select>
                </td>
                <td class="action-buttons">
                    <button onclick="saveWork(${work.id})" class="secondary">💾</button>
                    <button onclick="openWorkMaterials(${work.id})" class="secondary" title="Материалы работы">🧾</button>
                    <button onclick="addBalance(${work.id})" class="success" title="Добавить к балансу">➕</button>
                    <button onclick="deleteWork(${work.id})" class="danger">🗑️</button>
                </td>
            `;
            tableBody.appendChild(row);
        });

        initializeWorkCheckboxes();
        refreshTableSorting('worksTable');
    }

    function populateWorkMaterialSelect() {
        const select = document.getElementById('workMaterialSelect');
        if (!select) return;

        const selectedIds = new Set(currentWorkMaterials.map(item => item.material_id));
        const hasMaterials = Array.isArray(materials) && materials.length > 0;
        let options = '<option value="">Выберите материал</option>';

        if (hasMaterials) {
            materials.forEach(material => {
                const labelParts = [];
                labelParts.push(material.name || `ID ${material.id}`);
                if (material.unit) {
                    labelParts.push(material.unit);
                }
                if (material.category) {
                    labelParts.push(material.category);
                }
                const label = labelParts.join(' • ');
                const disabled = selectedIds.has(material.id) ? 'disabled' : '';
                options += `<option value="${material.id}" ${disabled}>${label}</option>`;
            });
        } else {
            options = '<option value="">Нет доступных материалов</option>';
        }

        select.innerHTML = options;
        select.disabled = !hasMaterials;
    }

    function displayWorkMaterialsList() {
        const tbody = document.getElementById('workMaterialsTableBody');
        if (!tbody) return;

        if (!currentWorkMaterials || currentWorkMaterials.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Материалы не назначены</td></tr>';
            return;
        }

        const rowsHtml = currentWorkMaterials.map(item => {
            const availableNumber = Number(item.available_quantity);
            const formattedAvailable = Number.isFinite(availableNumber)
                ? availableNumber.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
                : '0';
            const quantityNumber = Number(item.quantity_per_unit);
            const quantityValue = Number.isFinite(quantityNumber) ? quantityNumber : 0;

            return `
                <tr data-material-id="${item.material_id}">
                    <td>${item.material_name || `ID ${item.material_id}`}</td>
                    <td>${item.unit || ''}</td>
                    <td>${item.category || ''}</td>
                    <td>${formattedAvailable}</td>
                    <td><input type="number" min="0" step="1" value="${quantityValue}" oninput="handleWorkMaterialQuantityChange(${item.material_id}, this.value)"></td>
                    <td class="action-buttons">
                        <button type="button" class="danger" onclick="removeMaterialFromWork(${item.material_id})">🗑️</button>
                    </td>
                </tr>
            `;
        }).join('');

        tbody.innerHTML = rowsHtml;
    }

    function roundMoneyValue(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return null;
        }
        return Math.round((numeric + Number.EPSILON) * 100) / 100;
    }

    function normalizeCostValue(value) {
        if (value === null || value === undefined) {
            return null;
        }
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return null;
        }
        return numeric < 0 ? 0 : roundMoneyValue(numeric);
    }

    function parseMoneyInput(rawValue) {
        if (rawValue === null || rawValue === undefined) {
            return null;
        }
        const normalized = String(rawValue).replace(',', '.').trim();
        if (normalized === '') {
            return null;
        }
        const parsed = parseFloat(normalized);
        if (Number.isNaN(parsed)) {
            return 0;
        }
        return parsed < 0 ? 0 : parsed;
    }

    function formatMoneyValue(value) {
        if (value === null || value === undefined) {
            return '';
        }
        return Number(value).toFixed(2);
    }

    function updateWorkPricingInputs(excludeIds = []) {
        const exclude = Array.isArray(excludeIds) ? new Set(excludeIds) : new Set([excludeIds]);

        const unitInput = document.getElementById('workPriceUnit');
        const totalInput = document.getElementById('workPriceTotal');

        const unitValue = typeof currentWorkPricing.unitCost === 'number'
            ? roundMoneyValue(Math.max(currentWorkPricing.unitCost, 0))
            : null;
        const totalValue = typeof currentWorkPricing.totalCost === 'number'
            ? roundMoneyValue(Math.max(currentWorkPricing.totalCost, 0))
            : null;

        if (unitInput && !exclude.has('workPriceUnit')) {
            unitInput.value = formatMoneyValue(unitValue);
        }
        if (totalInput && !exclude.has('workPriceTotal')) {
            totalInput.value = formatMoneyValue(totalValue);
        }
    }

    function handlePricingInput(field, rawValue) {
        const parsed = parseMoneyInput(rawValue);

        if (field === 'unitCost') {
            currentWorkPricing.unitCost = parsed === null ? null : roundMoneyValue(parsed);
        } else if (field === 'totalCost') {
            currentWorkPricing.totalCost = parsed === null ? null : roundMoneyValue(parsed);
        }
    }

    function resetWorkPricing() {
        currentWorkPricing = {
            unitCost: null,
            totalCost: null
        };
        updateWorkPricingInputs();
    }

    function updateMaterialPricingInputs(excludeIds = []) {
        const exclude = Array.isArray(excludeIds) ? new Set(excludeIds) : new Set([excludeIds]);

        const unitInput = document.getElementById('materialPriceUnit');
        const totalInput = document.getElementById('materialPriceTotal');
        const quantityInput = document.getElementById('materialPriceQuantity');

        const unitValue = typeof currentMaterialPricing.unitCost === 'number'
            ? roundMoneyValue(Math.max(currentMaterialPricing.unitCost, 0))
            : null;
        const quantityValue = Number.isFinite(currentMaterialQuantityForPricing)
            ? Math.max(currentMaterialQuantityForPricing, 0)
            : null;
        let totalValue = typeof currentMaterialPricing.totalCost === 'number'
            ? roundMoneyValue(Math.max(currentMaterialPricing.totalCost, 0))
            : null;

        if (typeof unitValue === 'number' && typeof quantityValue === 'number') {
            totalValue = roundMoneyValue(unitValue * quantityValue);
            currentMaterialPricing.totalCost = totalValue;
        }

        if (unitInput && !exclude.has('materialPriceUnit')) {
            unitInput.value = formatMoneyValue(unitValue);
        }
        if (quantityInput && !exclude.has('materialPriceQuantity')) {
            quantityInput.value = quantityValue !== null ? quantityValue : '';
        }
        if (totalInput && !exclude.has('materialPriceTotal')) {
            totalInput.value = formatMoneyValue(totalValue);
        }
    }

    function handleMaterialPricingInput(field, rawValue) {
        const parsed = parseMoneyInput(rawValue);

        if (field === 'unitCost') {
            currentMaterialPricing.unitCost = parsed === null ? null : roundMoneyValue(parsed);
        } else if (field === 'totalCost') {
            currentMaterialPricing.totalCost = parsed === null ? null : roundMoneyValue(parsed);
        }
    }

    function resetMaterialPricing() {
        currentMaterialPricing = {
            unitCost: null,
            totalCost: null
        };
        updateMaterialPricingInputs();
    }

    async function loadMaterialPricing(materialId) {
        try {
            const response = await makeApiRequest(`/api/materials/${materialId}/pricing`);
            if (response && response.success) {
                const pricingData = response.data || {};
                currentMaterialPricing = {
                    unitCost: normalizeCostValue(pricingData.unit_cost_without_vat),
                    totalCost: normalizeCostValue(pricingData.total_cost_without_vat)
                };
            } else {
                const errorMessage = response?.error || response?.detail;
                resetMaterialPricing();
                if (errorMessage) {
                    showNotification('Не удалось загрузить стоимость материала: ' + errorMessage, 'error');
                }
            }
        } catch (error) {
            resetMaterialPricing();
            showNotification('Ошибка загрузки стоимости материала: ' + error.message, 'error');
        }

        updateMaterialPricingInputs();
    }

    async function openMaterialPricing(materialId) {
        const modal = document.getElementById('materialPricingModal');
        if (!modal) return;

        const material = materials.find(item => item.id === materialId);
        if (!material) {
            showNotification('Материал не найден', 'error');
            return;
        }

        currentMaterialIdForPricing = materialId;

        const nameElement = document.getElementById('materialPricingName');
        if (nameElement) {
            const unitSuffix = material.unit ? ` (${material.unit})` : '';
            nameElement.textContent = `${material.name || `ID ${materialId}`}${unitSuffix}`;
        }

        currentMaterialQuantityForPricing = Number.isFinite(Number(material.quantity))
            ? Number(material.quantity)
            : 0;

        resetMaterialPricing();
        modal.style.display = 'flex';

        await loadMaterialPricing(materialId);
    }

    async function saveMaterialPricing() {
        if (!currentMaterialIdForPricing) {
            showNotification('Материал не выбран', 'error');
            return;
        }

        const saveButton = document.getElementById('materialPricingSaveButton');
        if (saveButton) {
            saveButton.disabled = true;
        }

        const payload = {
            unit_cost_without_vat: typeof currentMaterialPricing.unitCost === 'number'
                ? roundMoneyValue(Math.max(currentMaterialPricing.unitCost, 0)) || 0
                : 0,
            total_cost_without_vat: typeof currentMaterialPricing.totalCost === 'number'
                ? roundMoneyValue(Math.max(currentMaterialPricing.totalCost, 0)) || 0
                : 0,
        };

        try {
            const response = await makeApiRequest(`/api/materials/${currentMaterialIdForPricing}/pricing`, {
                method: 'PUT',
                body: JSON.stringify(payload)
            });

            if (response && response.success) {
                const pricingData = response.data || payload;
                currentMaterialPricing = {
                    unitCost: normalizeCostValue(pricingData.unit_cost_without_vat),
                    totalCost: normalizeCostValue(pricingData.total_cost_without_vat)
                };
                updateMaterialPricingInputs();

                const materialIndex = materials.findIndex(item => item.id === currentMaterialIdForPricing);
                if (materialIndex !== -1) {
                    materials[materialIndex] = {
                        ...materials[materialIndex],
                        unit_cost_without_vat: currentMaterialPricing.unitCost || 0,
                        total_cost_without_vat: currentMaterialPricing.totalCost || 0
                    };
                }

                showNotification(response.message || 'Стоимость материала обновлена', 'success');
            } else {
                const errorMessage = response?.error || response?.detail || response?.message || 'Не удалось сохранить стоимость материала';
                showNotification(errorMessage, 'error');
            }
        } catch (error) {
            showNotification('Ошибка сохранения стоимости материала: ' + error.message, 'error');
        } finally {
            if (saveButton) {
                saveButton.disabled = false;
            }
        }
    }

    function closeMaterialPricingModal() {
        const modal = document.getElementById('materialPricingModal');
        if (modal) {
            modal.style.display = 'none';
        }
        currentMaterialIdForPricing = null;
        currentMaterialQuantityForPricing = 0;
        resetMaterialPricing();
    }

    async function loadWorkMaterials(workId) {
        try {
            const response = await makeApiRequest(`/api/works/${workId}/materials`);
            if (response && response.success) {
                const materialsData = Array.isArray(response.data) ? response.data : [];
                currentWorkMaterials = materialsData.map(item => ({
                    material_id: item.material_id,
                    material_name: item.material_name || `ID ${item.material_id}`,
                    unit: item.unit,
                    category: item.category,
                    quantity_per_unit: parseFloat(item.quantity_per_unit) || 0,
                    available_quantity: item.available_quantity !== undefined ? Number(item.available_quantity) : 0
                }));

                if (response.pricing && typeof response.pricing === 'object') {
                    currentWorkPricing = {
                        unitCost: normalizeCostValue(response.pricing.unit_cost_without_vat),
                        totalCost: normalizeCostValue(response.pricing.total_cost_without_vat)
                    };
                    updateWorkPricingInputs();
                } else {
                    resetWorkPricing();
                }
            } else {
                currentWorkMaterials = [];
                resetWorkPricing();
                const errorMessage = response?.error || response?.detail;
                if (errorMessage) {
                    showNotification('Ошибка загрузки материалов работы: ' + errorMessage, 'error');
                }
            }
        } catch (error) {
            currentWorkMaterials = [];
            resetWorkPricing();
            showNotification('Ошибка загрузки материалов работы: ' + error.message, 'error');
        }

        populateWorkMaterialSelect();
        displayWorkMaterialsList();
        updateWorkPricingInputs();
    }

    async function openWorkMaterials(workId) {
        const modal = document.getElementById('workMaterialsModal');
        if (!modal) return;

        const work = works.find(item => item.id === workId);
        if (!work) {
            showNotification('Работа не найдена', 'error');
            return;
        }

        currentWorkIdForMaterials = workId;

        const workNameElement = document.getElementById('workMaterialsWorkName');
        if (workNameElement) {
            const unitSuffix = work['Единица измерения'] ? ` (${work['Единица измерения']})` : '';
            workNameElement.textContent = `${work['Название работы']}${unitSuffix}`;
        }

        const select = document.getElementById('workMaterialSelect');
        const quantityInput = document.getElementById('workMaterialQuantity');
        if (select) select.value = '';
        if (quantityInput) quantityInput.value = '';

        const tbody = document.getElementById('workMaterialsTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Загрузка...</td></tr>';
        }

        resetWorkPricing();
        modal.style.display = 'flex';

        if (!materials || materials.length === 0) {
            await loadMaterials();
        }

        await loadWorkMaterials(workId);
    }

    function addMaterialToWorkList() {
        const select = document.getElementById('workMaterialSelect');
        const quantityInput = document.getElementById('workMaterialQuantity');
        if (!select || !quantityInput) return;

        const materialId = parseInt(select.value, 10);
        const quantity = parseFloat(quantityInput.value);

        if (!materialId) {
            showNotification('Выберите материал для добавления', 'error');
            return;
        }

        if (isNaN(quantity) || quantity <= 0) {
            showNotification('Введите расход материала больше 0', 'error');
            return;
        }

        const material = materials.find(item => item.id === materialId);
        if (!material) {
            showNotification('Материал не найден', 'error');
            return;
        }

        const normalizedQuantity = Number(quantity);
        const existing = currentWorkMaterials.find(item => item.material_id === materialId);

        if (existing) {
            existing.quantity_per_unit = normalizedQuantity;
            existing.material_name = material.name || existing.material_name;
            existing.unit = material.unit;
            existing.category = material.category;
            existing.available_quantity = material.quantity !== undefined ? Number(material.quantity) : existing.available_quantity;
        } else {
            currentWorkMaterials.push({
                material_id: materialId,
                material_name: material.name || `ID ${materialId}`,
                unit: material.unit,
                category: material.category,
                quantity_per_unit: normalizedQuantity,
                available_quantity: material.quantity !== undefined ? Number(material.quantity) : 0
            });
        }

        quantityInput.value = '';
        select.value = '';

        populateWorkMaterialSelect();
        displayWorkMaterialsList();
    }

    function handleWorkMaterialQuantityChange(materialId, value) {
        const target = currentWorkMaterials.find(item => item.material_id === materialId);
        if (!target) return;

        let parsed = parseFloat(value);
        if (isNaN(parsed) || parsed < 0) {
            parsed = 0;
        }
        target.quantity_per_unit = parsed;
    }

    function removeMaterialFromWork(materialId) {
        currentWorkMaterials = currentWorkMaterials.filter(item => item.material_id !== materialId);
        populateWorkMaterialSelect();
        displayWorkMaterialsList();
    }

    async function saveWorkMaterials() {
        if (!currentWorkIdForMaterials) {
            showNotification('Не выбрана работа для сохранения материалов', 'error');
            return;
        }

        const materialsPayload = currentWorkMaterials.map(item => ({
            material_id: item.material_id,
            quantity_per_unit: Number(item.quantity_per_unit) || 0
        }));

        const pricingPayload = {
            unit_cost_without_vat: typeof currentWorkPricing.unitCost === 'number'
                ? roundMoneyValue(Math.max(currentWorkPricing.unitCost, 0)) || 0
                : 0,
            total_cost_without_vat: typeof currentWorkPricing.totalCost === 'number'
                ? roundMoneyValue(Math.max(currentWorkPricing.totalCost, 0)) || 0
                : 0
        };

        const requestBody = {
            materials: materialsPayload,
            pricing: pricingPayload
        };

        try {
            const response = await makeApiRequest(`/api/works/${currentWorkIdForMaterials}/materials`, {
                method: 'PUT',
                body: JSON.stringify(requestBody)
            });

            if (response && response.success) {
                const materialsData = Array.isArray(response.data) ? response.data : [];
                currentWorkMaterials = materialsData.map(item => ({
                    material_id: item.material_id,
                    material_name: item.material_name || `ID ${item.material_id}`,
                    unit: item.unit,
                    category: item.category,
                    quantity_per_unit: parseFloat(item.quantity_per_unit) || 0,
                    available_quantity: item.available_quantity !== undefined ? Number(item.available_quantity) : 0
                }));

                if (response.pricing && typeof response.pricing === 'object') {
                    currentWorkPricing = {
                        unitCost: normalizeCostValue(response.pricing.unit_cost_without_vat),
                        totalCost: normalizeCostValue(response.pricing.total_cost_without_vat)
                    };
                }

                displayWorkMaterialsList();
                populateWorkMaterialSelect();
                updateWorkPricingInputs();
                showNotification('Материалы работы обновлены', 'success');
            } else {
                const errorMessage = response?.error || response?.message || 'Не удалось сохранить материалы';
                showNotification(errorMessage, 'error');
            }
        } catch (error) {
            showNotification('Ошибка сохранения материалов: ' + error.message, 'error');
        }
    }

    function closeWorkMaterialsModal() {
        const modal = document.getElementById('workMaterialsModal');
        if (modal) {
            modal.style.display = 'none';
        }
        currentWorkIdForMaterials = null;
        currentWorkMaterials = [];
        resetWorkPricing();
        populateWorkMaterialSelect();
        displayWorkMaterialsList();
    }

    // ФУНКЦИИ СОРТИРОВКИ
    
    
    // Инициализация чекбоксов для выбора работ
    function initializeWorkCheckboxes() {
        const selectAllCheckbox = document.getElementById('selectAllWorks');
        const workCheckboxes = document.querySelectorAll('.work-checkbox');
        const deleteSelectedBtn = document.getElementById('deleteSelectedWorks');
        const massActions = document.getElementById('massActions');
        const selectedCount = document.getElementById('selectedCount');
        
        // Сбрасываем состояние "Выбрать все"
        selectAllCheckbox.checked = false;
        
        // Обработчик для "Выбрать все"
        selectAllCheckbox.addEventListener('click', function(event) {
            const shouldSelectAll = selectAllCheckbox.dataset.allSelected !== 'true';

            workCheckboxes.forEach(checkbox => {
                checkbox.checked = shouldSelectAll;
            });

            selectAllCheckbox.checked = shouldSelectAll;
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.dataset.allSelected = shouldSelectAll ? 'true' : 'false';

            updateMassActions();
        });
        
        // Обработчики для отдельных чекбоксов
        workCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateMassActions);
        });
        
        // Функция обновления панели массовых действий
        function updateMassActions() {
            const selectedCountValue = document.querySelectorAll('.work-checkbox:checked').length;
            
            if (selectedCountValue > 0) {
                deleteSelectedBtn.style.display = 'inline-block';
                massActions.style.display = 'flex';
                selectedCount.textContent = selectedCountValue;
                const allSelected = selectedCountValue === workCheckboxes.length;
                selectAllCheckbox.checked = allSelected;
                selectAllCheckbox.indeterminate = !allSelected;
                selectAllCheckbox.dataset.allSelected = allSelected ? 'true' : 'false';
            } else {
                deleteSelectedBtn.style.display = 'none';
                massActions.style.display = 'none';
                selectedCount.textContent = '0';
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
                selectAllCheckbox.dataset.allSelected = 'false';
            }
        }
        
        // Обработчик для кнопки массового удаления
        deleteSelectedBtn.onclick = deleteSelectedWorks;
        
        // Инициализируем состояние
        updateMassActions();
    }
    
    // Массовое удаление выбранных работ
    async function deleteSelectedWorks() {
        const selectedCheckboxes = document.querySelectorAll('.work-checkbox:checked');
        
        if (selectedCheckboxes.length === 0) {
            showNotification('Не выбрано ни одной работы для удаления', 'error');
            return;
        }
        
        const workIds = Array.from(selectedCheckboxes).map(checkbox => parseInt(checkbox.value));
        
        if (!confirm(`Вы уверены, что хотите удалить ${workIds.length} выбранных работ?`)) {
            return;
        }
        
        try {
            // Сначала анимируем исчезновение строк
            selectedCheckboxes.forEach(checkbox => {
                const row = checkbox.closest('tr');
                row.classList.add('fade-out');
            });
            
            // Ждем завершения анимации
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // Удаляем каждую выбранную работу
            const deletePromises = workIds.map(workId => 
                makeApiRequest(`${API_CONFIG.ENDPOINTS.WORKS}/${workId}`, {
                    method: 'DELETE'
                })
            );
            
            // Ждем завершения всех запросов удаления
            await Promise.all(deletePromises);
            
            // Полностью перезагружаем данные с сервера
            await loadWorks();
            
            showNotification(`Успешно удалено ${workIds.length} работ`, 'success');
            
        } catch (error) {
            showNotification('Ошибка при массовом удалении работ: ' + error.message, 'error');
            // Если произошла ошибка, убираем анимацию исчезновения
            selectedCheckboxes.forEach(checkbox => {
                const row = checkbox.closest('tr');
                row.classList.remove('fade-out');
            });
        }
    }
    
    // Добавление новой работы
    function addNewWork() {
        const existingModal = document.getElementById('addWorkModal');
        if (existingModal) {
            existingModal.remove();
        }

        const overlay = document.createElement('div');
        overlay.className = 'modal';
        overlay.id = 'addWorkModal';
        overlay.style.display = 'flex';

        const content = document.createElement('div');
        content.className = 'modal-content';

        const title = document.createElement('h3');
        title.className = 'modal-title';
        title.textContent = 'Добавление работ';

        const subtitle = document.createElement('p');
        subtitle.className = 'modal-subtitle';
        subtitle.textContent = 'Заполните данные и добавьте одну или несколько работ.';

        const form = document.createElement('form');
        form.id = 'addWorkForm';

        const itemsContainer = document.createElement('div');
        itemsContainer.id = 'addWorkItemsContainer';
        itemsContainer.style.display = 'flex';
        itemsContainer.style.flexDirection = 'column';
        itemsContainer.style.gap = '12px';

        const addItemButton = document.createElement('button');
        addItemButton.type = 'button';
        addItemButton.className = 'secondary';
        addItemButton.textContent = '➕ Добавить еще работу';

        const actions = document.createElement('div');
        actions.className = 'modal-actions';

        const cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.className = 'secondary';
        cancelButton.textContent = 'Отмена';

        const submitButton = document.createElement('button');
        submitButton.type = 'submit';
        submitButton.className = 'success';
        submitButton.textContent = '💾 Сохранить';

        actions.appendChild(cancelButton);
        actions.appendChild(submitButton);

        form.appendChild(itemsContainer);
        form.appendChild(addItemButton);
        form.appendChild(actions);

        content.appendChild(title);
        content.appendChild(subtitle);
        content.appendChild(form);

        overlay.appendChild(content);
        document.body.appendChild(overlay);

        const availableCategories = Array.isArray(categories) && categories.length > 0
            ? categories.map(cat => cat.name)
            : [''];
        const availableUnits = Array.isArray(UNITS) && UNITS.length > 0
            ? UNITS.slice()
            : ['шт'];

        function createSelectOptions(options, selectedValue = '') {
            return options.map(option => {
                const value = option ?? '';
                const selected = value === selectedValue ? ' selected' : '';
                return `<option value="${value}"${selected}>${value}</option>`;
            }).join('');
        }

        function createWorkItem(initialData = {}) {
            const item = document.createElement('div');
            item.className = 'report-work-item add-work-item';

            item.innerHTML = `
                <div class="modal-form-group">
                    <label>Наименование</label>
                    <input type="text" class="editable" data-field="name" placeholder="Наименование работы" value="${initialData.name || ''}" required>
                </div>
                <div class="modal-form-group">
                    <label>Раздел</label>
                    <select class="editable" data-field="category"></select>
                </div>
                <div class="modal-form-group">
                    <label>Единица измерения</label>
                    <select class="editable" data-field="unit"></select>
                </div>
                <div class="modal-form-group">
                    <label>На балансе</label>
                    <input type="number" class="editable" data-field="balance" step="1" value="${initialData.balance ?? 0}">
                </div>
                <div class="modal-form-group">
                    <label>Проект</label>
                    <input type="number" class="editable" data-field="project_total" step="1" value="${initialData.project_total ?? 0}">
                </div>
                <div class="modal-form-group">
                    <label>Активно</label>
                    <select class="editable" data-field="is_active">
                        <option value="1"${initialData.is_active === 0 ? '' : ' selected'}>Да</option>
                        <option value="0"${initialData.is_active === 0 ? ' selected' : ''}>Нет</option>
                    </select>
                </div>
                <button type="button" class="secondary remove-add-work-button">Удалить</button>
            `;

            const categorySelect = item.querySelector('select[data-field="category"]');
            categorySelect.innerHTML = createSelectOptions(availableCategories, initialData.category || availableCategories[0] || '');

            const unitSelect = item.querySelector('select[data-field="unit"]');
            unitSelect.innerHTML = createSelectOptions(availableUnits, initialData.unit || availableUnits[0]);

            const removeButton = item.querySelector('.remove-add-work-button');
            removeButton.addEventListener('click', () => {
                item.remove();
                if (!itemsContainer.querySelector('.add-work-item')) {
                    addWorkEntry();
                }
            });

            return item;
        }

        function addWorkEntry(initialData = {}) {
            const item = createWorkItem(initialData);
            itemsContainer.appendChild(item);
        }

        addItemButton.addEventListener('click', () => addWorkEntry());
        cancelButton.addEventListener('click', () => {
            overlay.remove();
        });

        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                overlay.remove();
            }
        });

        content.addEventListener('click', (event) => event.stopPropagation());

        addWorkEntry();

        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            const items = Array.from(itemsContainer.querySelectorAll('.add-work-item'));
            if (items.length === 0) {
                showNotification('Добавьте хотя бы одну работу', 'error');
                return;
            }

            const worksPayload = [];

            for (const item of items) {
                const getField = (selector) => item.querySelector(selector);

                const nameInput = getField('input[data-field="name"]');
                const categorySelect = getField('select[data-field="category"]');
                const unitSelect = getField('select[data-field="unit"]');
                const balanceInput = getField('input[data-field="balance"]');
                const projectInput = getField('input[data-field="project_total"]');
                const isActiveSelect = getField('select[data-field="is_active"]');

                const name = (nameInput.value || '').trim();
                if (!name) {
                    showNotification('Наименование работы не может быть пустым', 'error');
                    nameInput.focus();
                    return;
                }

                worksPayload.push({
                    name,
                    category: (categorySelect?.value || '').trim(),
                    unit: unitSelect?.value || '',
                    balance: parseFloat(balanceInput?.value || '0') || 0,
                    project_total: parseFloat(projectInput?.value || '0') || 0,
                    is_active: parseInt(isActiveSelect?.value || '1', 10) || 0
                });
            }

            submitButton.disabled = true;
            cancelButton.disabled = true;
            addItemButton.disabled = true;

            let successCount = 0;
            let errorMessages = [];

            for (const workData of worksPayload) {
                try {
                    showNotification('Добавление работы...', 'success');

                    const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WORKS), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('token')}`
                        },
                        body: JSON.stringify({
                            name: workData.name,
                            category: workData.category,
                            unit: workData.unit,
                            balance: workData.balance,
                            project_total: workData.project_total,
                            is_active: workData.is_active
                        })
                    });

                    const workAdded = await checkIfWorkExists(workData.name, workData.category);

                    if (workAdded) {
                        successCount++;
                        showNotification(`Работа "${workData.name}" успешно добавлена`, 'success');
                    } else {
                        let errorMessage = 'Работа не была добавлена в базе данных';
                        try {
                            const errorText = await response.text();
                            if (errorText) {
                                const errorData = JSON.parse(errorText);
                                errorMessage = errorData.detail || errorData.error || errorMessage;
                            }
                        } catch (e) {}
                        errorMessages.push(errorMessage);
                    }
                } catch (error) {
                    errorMessages.push('Ошибка при добавлении работы: ' + error.message);
                }
            }

            if (successCount > 0) {
                overlay.remove();
            } else {
                submitButton.disabled = false;
                cancelButton.disabled = false;
                addItemButton.disabled = false;
            }

            if (errorMessages.length > 0) {
                showNotification(errorMessages.join(' '), 'error');
            }
        });
    }
    
    // Удаление новой работы (если пользователь передумал)
    function removeNewWork(button) {
        const row = button.closest('tr');
        row.remove();
        
        // Если таблица пустая, показываем сообщение
        const tableBody = document.getElementById('worksTableBody');
        if (tableBody.children.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Нет данных о работах</td></tr>';
        }
    }
    
    // Сохранение новой работы
    async function saveNewWork(button) {
        const row = button.closest('tr');
        const inputs = row.querySelectorAll('.editable');
        
        const workData = {};
        inputs.forEach(input => {
            const field = input.getAttribute('data-field');
            let value = input.value;
            
            if (field === 'balance' || field === 'project_total') value = parseFloat(value);
            if (field === 'is_active') value = parseInt(value);
            
            workData[field] = value;
        });
        
        const workName = workData.name;
        const category = workData.category;
        
        const apiData = {
            name: workData.name,
            category: workData.category,
            unit: workData.unit,
            balance: workData.balance,
            project_total: workData.project_total,
            is_active: workData.is_active
        };
        
        try {
            showNotification('Добавление работы...', 'success');
            
            const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.WORKS), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(apiData)
            });
            
            const workAdded = await checkIfWorkExists(workName, category);
            
            if (workAdded) {
                showNotification('Работа успешно добавлена', 'success');
            } else {
                let errorMessage = 'Работа не была добавлена в базу данных';
                try {
                    const errorText = await response.text();
                    if (errorText) {
                        const errorData = JSON.parse(errorText);
                        errorMessage = errorData.detail || errorData.error || errorMessage;
                    }
                } catch (e) {}
                showNotification(`Ошибка: ${errorMessage}`, 'error');
            }
            
        } catch (error) {
            showNotification('Ошибка при добавлении работы: ' + error.message, 'error');
        }
    }

    async function checkIfWorkExists(workName, category, maxAttempts = 5) {
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            await loadWorks();
            const exists = works.some(work => {
                const sectionName = work.Раздел || work['Категория'] || '';
                return work['Название работы'] === workName && sectionName === category;
            });
            if (exists) return true;
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        return false;
    }
    
    // Сохранение работы
    async function saveWork(workId) {
        const row = document.querySelector(`tr:has(input[value="${workId}"])`);
        const inputs = row.querySelectorAll('.editable');
        
        const workData = { id: workId };
        inputs.forEach(input => {
            const field = input.getAttribute('data-field');
            let value = input.value;
            
            if (field === 'balance' || field === 'project_total') value = parseFloat(value);
            if (field === 'is_active') value = parseInt(value);
            
            workData[field] = value;
        });
        
        const apiData = {
            name: workData.name,
            category: workData.category,
            unit: workData.unit,
            balance: workData.balance,
            project_total: workData.project_total,
            is_active: workData.is_active
        };
        
        try {
            const originalWork = works.find(work => work.id === workId);
            if (!originalWork) {
                showNotification('Работа не найдена', 'error');
                return;
            }
            
            showNotification('Обновление работы...', 'success');
            
            const response = await fetch(buildApiUrl(`${API_CONFIG.ENDPOINTS.WORKS}/${workId}`), {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(apiData)
            });
            
            await new Promise(resolve => setTimeout(resolve, 1000));
            await loadWorks();
            
            const updatedWork = works.find(work => work.id === workId);
            
            if (updatedWork) {
                const updatedSection = updatedWork.Раздел || updatedWork['Категория'] || '';
                const isUpdated =
                    updatedWork['Название работы'] === workData.name &&
                    updatedSection === workData.category &&
                    updatedWork['Единица измерения'] === workData.unit &&
                    parseFloat(updatedWork['На балансе']) === workData.balance &&
                    parseFloat(updatedWork['Проект'] || 0) === workData.project_total &&
                    Boolean(updatedWork.is_active) === Boolean(workData.is_active);
                
                if (isUpdated) {
                    showNotification('Работа успешно обновлена', 'success');
                } else {
                    showNotification('Работа найдена, но данные не были обновлены', 'warning');
                }
            } else {
                let errorMessage = 'Работа не была обновлена в базе данных';
                try {
                    const errorText = await response.text();
                    if (errorText) {
                        const errorData = JSON.parse(errorText);
                        errorMessage = errorData.detail || errorData.error || errorMessage;
                    }
                } catch (e) {}
                showNotification(`Ошибка: ${errorMessage}`, 'error');
            }
            
        } catch (error) {
            showNotification('Ошибка при обновлении работы: ' + error.message, 'error');
        }
    }
    
    // Сохранение всех работ
    async function saveAllWorks() {
        const rows = document.querySelectorAll('#worksTableBody tr');
        let hasChanges = false;
        let successCount = 0;
        let errorCount = 0;
        
        showNotification('Сохранение всех изменений...', 'success');
        
        for (const row of rows) {
            const idInput = row.querySelector('td:nth-child(2) input');
            if (!idInput || idInput.value === 'новый') continue;
            
            const workId = parseInt(idInput.value);
            const inputs = row.querySelectorAll('.editable');
            
            const workData = { id: workId };
            inputs.forEach(input => {
                const field = input.getAttribute('data-field');
                let value = input.value;
                
                if (field === 'balance' || field === 'project_total') value = parseFloat(value);
                if (field === 'is_active') value = parseInt(value);
                
                workData[field] = value;
            });
            
            const apiData = {
                name: workData.name,
                category: workData.category,
                unit: workData.unit,
                balance: workData.balance,
                project_total: workData.project_total,
                is_active: workData.is_active
            };
            
            try {
                const response = await fetch(buildApiUrl(`${API_CONFIG.ENDPOINTS.WORKS}/${workId}`), {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(apiData)
                });
                
                await new Promise(resolve => setTimeout(resolve, 500));
                
                if (successCount + errorCount === rows.length - 1) {
                    await loadWorks();
                }
                
                successCount++;
                hasChanges = true;
                
            } catch (error) {
                errorCount++;
            }
        }
        
        await loadWorks();
        
        if (hasChanges) {
            let message = `Все изменения успешно сохранены. Обновлено работ: ${successCount}`;
            if (errorCount > 0) {
                message += `, ошибок: ${errorCount}`;
            }
            showNotification(message, 'success');
        } else {
            showNotification('Нет изменений для сохранения', 'success');
        }
    }
    
    // Удаление работы
    async function deleteWork(workId) {
        if (confirm('Вы уверены, что хотите удалить эту работу?')) {
            try {
                const row = document.querySelector(`tr:has(input[value="${workId}"])`);
                row.classList.add('fade-out');
                await new Promise(resolve => setTimeout(resolve, 300));
                
                const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.WORKS}/${workId}`, {
                    method: 'DELETE'
                });
                
                if (response.success) {
                    await loadWorks();
                    showNotification('Работа успешно удалена', 'success');
                } else {
                    showNotification('Ошибка при удалении работы: ' + (response.error || 'Неизвестная ошибка'), 'error');
                }
            } catch (error) {
                showNotification('Ошибка при удалении работы: ' + error.message, 'error');
            }
        }
    }
    
    // Фильтрация работ
    function filterWorks() {
        const searchTerm = document.getElementById('searchWorks').value.toLowerCase();
        const filteredWorks = works.filter(work => {
            const sectionValue = (work.Раздел || work['Категория'] || '').toLowerCase();
            return (
                work['Название работы'].toLowerCase().includes(searchTerm) ||
                sectionValue.includes(searchTerm) ||
                work['Единица измерения'].toLowerCase().includes(searchTerm)
            );
        });
        displayWorks(filteredWorks);
    }
    
    // ========== ФУНКЦИИ ИМПОРТА/ЭКСПОРТА XLS ==========
    async function exportWorksToExcel() {
        try {
            showNotification('Подготовка файла для скачивания...', 'success');
            
            const workbook = XLSX.utils.book_new();
            workbook.Props = {
                Title: "Список работ",
                Subject: "Работы строительной отчетности",
                Author: "WiTech System",
                CreatedDate: new Date()
            };

            const exportData = works.map(work => ({
                'ID': work.id,
                'Название работы': work['Название работы'],
                'Раздел': work.Раздел || work['Категория'] || '',
                'Единица измерения': work['Единица измерения'],
                'На балансе': work['На балансе'],
                'Проект': work['Проект'] || 0,
                'Стоимость за единицу': work['Стоимость за единицу'] ?? work.unit_cost_without_vat ?? 0,
                'Активна': work.is_active ? 'Да' : 'Нет'
            }));

            const worksheet = XLSX.utils.json_to_sheet(exportData);
            
            const colWidths = [
                { wch: 8 },   // ID
                { wch: 40 },  // Название работы
                { wch: 20 },  // Раздел
                { wch: 15 },  // Единица измерения
                { wch: 12 },  // На балансе
                { wch: 12 },  // Проект
                { wch: 18 },  // Стоимость за единицу
                { wch: 10 }   // Активна
            ];
            worksheet['!cols'] = colWidths;

            XLSX.utils.book_append_sheet(workbook, worksheet, "Работы");

            const fileName = `works_export_${new Date().toISOString().split('T')[0]}.xlsx`;
            XLSX.writeFile(workbook, fileName);
            
            showNotification('Файл успешно скачан', 'success');
        } catch (error) {
            console.error('Export error:', error);
            showNotification('Ошибка при экспорте файла: ' + error.message, 'error');
        }
    }

    function triggerImportWorks() {
        document.getElementById('importFileInput').click();
    }

    async function handleWorksImport(event) {
        const file = event.target.files[0];
        if (!file) return;
        event.target.value = '';

        try {
            showNotification('Чтение файла...', 'success');
            const data = await readExcelFile(file);
            await importWorksFromExcel(data);
        } catch (error) {
            console.error('Import error:', error);
            showNotification('Ошибка при импорте файла: ' + error.message, 'error');
        }
    }

    function readExcelFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const data = new Uint8Array(e.target.result);
                    const workbook = XLSX.read(data, { type: 'array' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const jsonData = XLSX.utils.sheet_to_json(worksheet);
                    resolve(jsonData);
                } catch (error) {
                    reject(error);
                }
            };
            reader.onerror = function() {
                reject(new Error('Ошибка чтения файла'));
            };
            reader.readAsArrayBuffer(file);
        });
    }

    async function importWorksFromExcel(excelData) {
        if (!excelData || excelData.length === 0) {
            throw new Error('Файл не содержит данных');
        }

        let importedCount = 0;
        let updatedCount = 0;
        let errors = [];

        showNotification(`Начинаем импорт ${excelData.length} записей...`, 'success');

        for (let i = 0; i < excelData.length; i++) {
            const row = excelData[i];
            try {
                const rawSection = row['Раздел'] ?? row['Категория'];
                if (!row['Название работы'] || !rawSection || !row['Единица измерения']) {
                    errors.push(`Строка ${i + 2}: Отсутствуют обязательные поля`);
                    continue;
                }

                const sectionName = String(rawSection).trim();
                const unitCost = parseFloat(row['Стоимость за единицу']) || 0;
                const workData = {
                    name: String(row['Название работы']).trim(),
                    category: sectionName,
                    unit: String(row['Единица измерения']).trim(),
                    balance: parseFloat(row['На балансе']) || 0,
                    project_total: parseFloat(row['Проект']) || 0,
                    unit_cost_without_vat: unitCost,
                    total_cost_without_vat: unitCost * (parseFloat(row['Проект']) || 0),
                    is_active: String(row['Активна']).toLowerCase() === 'да' ? 1 : 0
                };

                const existingWorkId = row['ID'] ? parseInt(row['ID']) : null;
                
                if (existingWorkId && works.find(w => w.id === existingWorkId)) {
                    const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.WORKS}/${existingWorkId}`, {
                        method: 'PUT',
                        body: JSON.stringify(workData)
                    });
                    
                    if (response && response.success) {
                        updatedCount++;
                    } else {
                        errors.push(`Строка ${i + 2}: Ошибка обновления работы ID ${existingWorkId}`);
                    }
                } else {
                    const response = await makeApiRequest(API_CONFIG.ENDPOINTS.WORKS, {
                        method: 'POST',
                        body: JSON.stringify(workData)
                    });
                    
                    if (response && response.success) {
                        importedCount++;
                    } else {
                        errors.push(`Строка ${i + 2}: Ошибка создания работы "${workData.name}"`);
                    }
                }
            } catch (error) {
                errors.push(`Строка ${i + 2}: ${error.message}`);
            }
        }

        await loadWorks();

        let resultMessage = `Импорт завершен. Добавлено: ${importedCount}, обновлено: ${updatedCount}`;
        if (errors.length > 0) {
            resultMessage += `. Ошибок: ${errors.length}`;
            console.error('Import errors:', errors);
        }
        
        showNotification(resultMessage, errors.length > 0 ? 'error' : 'success');
    }

    // ========== МАТЕРИАЛЫ ==========

    async function loadMaterials() {
        const loadingElement = document.getElementById('materialsLoading');
        const tableBody = document.getElementById('materialsTableBody');

        if (!loadingElement || !tableBody) return;

        loadingElement.style.display = 'block';
        tableBody.innerHTML = '';

        try {
            const data = await makeApiRequest(API_CONFIG.ENDPOINTS.MATERIALS);
            if (data.success) {
                materials = data.data || [];
                displayMaterials(materials);
                if (currentWorkMaterials && currentWorkMaterials.length > 0) {
                    currentWorkMaterials = currentWorkMaterials.map(item => {
                        const updated = materials.find(material => material.id === item.material_id);
                        if (updated) {
                            return {
                                ...item,
                                material_name: updated.name || item.material_name,
                                unit: updated.unit,
                                category: updated.category,
                                available_quantity: updated.quantity !== undefined ? Number(updated.quantity) : item.available_quantity
                            };
                        }
                        return item;
                    });
                    displayWorkMaterialsList();
                }
                populateWorkMaterialSelect();
            } else {
                showNotification('Ошибка при загрузке материалов: ' + (data.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            showNotification('Ошибка при загрузке материалов: ' + error.message, 'error');
        } finally {
            loadingElement.style.display = 'none';
        }
    }

    function displayMaterials(materialsToDisplay = materials) {
        const tableBody = document.getElementById('materialsTableBody');
        if (!tableBody) return;

        tableBody.innerHTML = '';

        if (!materialsToDisplay || materialsToDisplay.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Нет данных о материалах</td></tr>';
            refreshTableSorting('materialsTable');
            return;
        }

        materialsToDisplay.forEach(material => {
            const row = document.createElement('tr');
            row.setAttribute('data-material-id', material.id);
            const quantityValue = material.quantity !== undefined && material.quantity !== null ? Number(material.quantity) : 0;

            const categoryOptions = [
                ...categories.map(cat => `<option value="${cat.name}" ${cat.name === material.category ? 'selected' : ''}>${cat.name}</option>`)
            ];
            if (!categories.find(cat => cat.name === material.category) && material.category) {
                categoryOptions.push(`<option value="${material.category}" selected>${material.category}</option>`);
            }
            if (!material.category) {
                categoryOptions.unshift('<option value="" selected>Не выбрано</option>');
            }

            const unitOptions = [
                ...UNITS.map(unit => `<option value="${unit}" ${unit === material.unit ? 'selected' : ''}>${unit}</option>`)
            ];
            if (material.unit && !UNITS.includes(material.unit)) {
                unitOptions.push(`<option value="${material.unit}" selected>${material.unit}</option>`);
            }
            if (!material.unit) {
                unitOptions.unshift('<option value="" selected>Не выбрано</option>');
            }

            row.innerHTML = `
                <td><input type="text" value="${material.id}" readonly></td>
                <td>
                    <select class="editable" data-field="category">
                        ${categoryOptions.join('')}
                    </select>
                </td>
                <td><input type="text" value="${material.name || ''}" class="editable" data-field="name"></td>
                <td>
                    <select class="editable" data-field="unit">
                        ${unitOptions.join('')}
                    </select>
                </td>
                <td><input type="number" value="${quantityValue}" class="editable" data-field="quantity" step="1" min="0"></td>
                <td class="action-buttons">
                    <button onclick="saveMaterial(${material.id})" class="secondary">💾</button>
                    <button onclick="openMaterialPricing(${material.id})" class="secondary" title="Стоимость материала">🧾</button>
                    <button onclick="addMaterialQuantity(${material.id})" class="success" title="Добавить на склад">➕</button>
                    <button onclick="deleteMaterial(${material.id})" class="danger">🗑️</button>
                </td>
            `;

            tableBody.appendChild(row);
        });

        refreshTableSorting('materialsTable');
    }

    async function loadMaterialHistory(forceReload = false) {
        const loadingElement = document.getElementById('materialsHistoryLoading');
        const tableBody = document.getElementById('materialHistoryTableBody');

        if (!loadingElement || !tableBody) return;

        if (forceReload) {
            materialHistoryLoaded = false;
        }

        if (materialHistoryLoaded && !forceReload) {
            displayMaterialHistory(materialHistory);
            return;
        }

        loadingElement.style.display = 'block';
        tableBody.innerHTML = '';

        try {
            const data = await makeApiRequest(API_CONFIG.ENDPOINTS.MATERIALS_HISTORY);
            if (data.success) {
                materialHistory = data.data || [];
                materialHistoryLoaded = true;
                displayMaterialHistory(materialHistory);
            } else {
                showNotification('Ошибка при загрузке истории материалов: ' + (data.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            showNotification('Ошибка при загрузке истории материалов: ' + error.message, 'error');
        } finally {
            loadingElement.style.display = 'none';
        }
    }

    function formatHistoryNumber(value, unit) {
        if (value === null || value === undefined || value === '') {
            return '';
        }
        const numberValue = Number(value);
        if (!Number.isFinite(numberValue)) {
            return value;
        }
        const formatted = numberValue.toLocaleString('ru-RU', { maximumFractionDigits: 2 });
        return unit ? `${formatted} ${unit}` : formatted;
    }

    function formatHistoryChange(amount, unit) {
        if (amount === null || amount === undefined || amount === '') {
            return '';
        }
        const numberValue = Number(amount);
        if (!Number.isFinite(numberValue)) {
            return amount;
        }
        const sign = numberValue > 0 ? '+' : numberValue < 0 ? '-' : '';
        const formatted = Math.abs(numberValue).toLocaleString('ru-RU', { maximumFractionDigits: 2 });
        return unit ? `${sign}${formatted} ${unit}` : `${sign}${formatted}`;
    }

    function formatHistoryDate(dateValue) {
        if (!dateValue) {
            return '';
        }
        const normalized = typeof dateValue === 'string' ? dateValue.replace(' ', 'T') : dateValue;
        const date = new Date(normalized);
        if (Number.isNaN(date.getTime())) {
            return dateValue;
        }
        return date.toLocaleString('ru-RU');
    }

    function displayMaterialHistory(historyToDisplay = materialHistory) {
        const tableBody = document.getElementById('materialHistoryTableBody');
        if (!tableBody) return;

        tableBody.innerHTML = '';

        if (!historyToDisplay || historyToDisplay.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Нет данных об истории материалов</td></tr>';
            refreshTableSorting('materialHistoryTable');
            return;
        }

        historyToDisplay.forEach(entry => {
            const row = document.createElement('tr');
            const unit = entry.unit || '';
            const changeValue = Number(entry.change_amount);
            const resultingValue = Number(entry.resulting_quantity);
            const changeSortValue = Number.isFinite(changeValue) ? changeValue : '';
            const resultingSortValue = Number.isFinite(resultingValue) ? resultingValue : '';
            const dateSortValue = entry.created_at
                ? String(entry.created_at).replace(' ', 'T')
                : '';
            row.innerHTML = `
                <td>${entry.id ?? ''}</td>
                <td>${entry.material_name || '-'}</td>
                <td>${entry.change_type || '-'}</td>
                <td data-sort-value="${changeSortValue}">${formatHistoryChange(entry.change_amount, unit)}</td>
                <td data-sort-value="${resultingSortValue}">${formatHistoryNumber(entry.resulting_quantity, unit)}</td>
                <td>${entry.description || ''}</td>
                <td>${entry.performed_by || ''}</td>
                <td data-sort-value="${dateSortValue}">${formatHistoryDate(entry.created_at)}</td>
            `;
            tableBody.appendChild(row);
        });

        refreshTableSorting('materialHistoryTable');
    }

    function filterMaterialHistory(query) {
        if (!query) {
            displayMaterialHistory(materialHistory);
            return;
        }

        const normalized = query.toLowerCase();
        const filtered = materialHistory.filter(entry => {
            return [
                entry.id,
                entry.material_id,
                entry.material_name,
                entry.change_type,
                entry.change_amount,
                entry.resulting_quantity,
                entry.performed_by,
                entry.description,
                entry.created_at
            ].some(value => value !== undefined && value !== null && String(value).toLowerCase().includes(normalized));
        });

        displayMaterialHistory(filtered);
    }

    async function toggleMaterialHistoryView() {
        const button = document.getElementById('toggleMaterialsHistory');
        const materialsContainer = document.getElementById('materialsTableContainer');
        const historyContainer = document.getElementById('materialHistoryContainer');
        const materialsLoading = document.getElementById('materialsLoading');
        const historyLoading = document.getElementById('materialsHistoryLoading');
        const searchInput = document.getElementById('searchMaterials');
        const addMaterialBtn = document.getElementById('addMaterial');
        const exportMaterialsBtn = document.getElementById('exportMaterials');
        const importMaterialsBtn = document.getElementById('importMaterials');

        if (!button || !materialsContainer || !historyContainer) {
            return;
        }

        if (!isMaterialHistoryView) {
            isMaterialHistoryView = true;
            button.textContent = '📦 Материалы';
            materialsContainer.style.display = 'none';
            if (materialsLoading) {
                materialsLoading.style.display = 'none';
            }
            historyContainer.style.display = 'block';
            if (historyLoading) {
                historyLoading.style.display = 'block';
            }
            if (addMaterialBtn) addMaterialBtn.style.display = 'none';
            if (exportMaterialsBtn) exportMaterialsBtn.style.display = 'none';
            if (importMaterialsBtn) importMaterialsBtn.style.display = 'none';
            await loadMaterialHistory(true);
            if (searchInput && searchInput.value) {
                filterMaterialHistory(searchInput.value.toLowerCase());
            }
        } else {
            isMaterialHistoryView = false;
            button.textContent = '📜 История';
            historyContainer.style.display = 'none';
            if (historyLoading) {
                historyLoading.style.display = 'none';
            }
            materialsContainer.style.display = 'block';
            if (addMaterialBtn) addMaterialBtn.style.display = '';
            if (exportMaterialsBtn) exportMaterialsBtn.style.display = '';
            if (importMaterialsBtn) importMaterialsBtn.style.display = '';
            if (searchInput) {
                filterMaterials({ target: searchInput });
            } else {
                displayMaterials(materials);
            }
        }
    }

    function filterMaterials(event) {
        const query = (event.target.value || '').toLowerCase();

        if (isMaterialHistoryView) {
            filterMaterialHistory(query);
            return;
        }

        if (!query) {
            displayMaterials(materials);
            return;
        }

        const filtered = materials.filter(material => {
            return [
                material.id,
                material.name,
                material.category,
                material.unit,
                material.quantity
            ].some(value => value !== undefined && value !== null && String(value).toLowerCase().includes(query));
        });

        displayMaterials(filtered);
    }

    function addNewMaterial() {
        const existingModal = document.getElementById('addMaterialModal');
        if (existingModal) {
            existingModal.remove();
        }

        const overlay = document.createElement('div');
        overlay.className = 'modal';
        overlay.id = 'addMaterialModal';
        overlay.style.display = 'flex';

        const content = document.createElement('div');
        content.className = 'modal-content';

        const title = document.createElement('h3');
        title.className = 'modal-title';
        title.textContent = 'Добавление материалов';

        const subtitle = document.createElement('p');
        subtitle.className = 'modal-subtitle';
        subtitle.textContent = 'Заполните данные и добавьте один или несколько материалов.';

        const form = document.createElement('form');
        form.id = 'addMaterialForm';

        const itemsContainer = document.createElement('div');
        itemsContainer.id = 'addMaterialItemsContainer';
        itemsContainer.style.display = 'flex';
        itemsContainer.style.flexDirection = 'column';
        itemsContainer.style.gap = '12px';

        const addItemButton = document.createElement('button');
        addItemButton.type = 'button';
        addItemButton.className = 'secondary';
        addItemButton.textContent = '➕ Добавить еще материал';

        const actions = document.createElement('div');
        actions.className = 'modal-actions';

        const cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.className = 'secondary';
        cancelButton.textContent = 'Отмена';

        const submitButton = document.createElement('button');
        submitButton.type = 'submit';
        submitButton.className = 'success';
        submitButton.textContent = '💾 Сохранить';

        actions.appendChild(cancelButton);
        actions.appendChild(submitButton);

        form.appendChild(itemsContainer);
        form.appendChild(addItemButton);
        form.appendChild(actions);

        content.appendChild(title);
        content.appendChild(subtitle);
        content.appendChild(form);

        overlay.appendChild(content);
        document.body.appendChild(overlay);

        const availableCategories = Array.isArray(categories) && categories.length > 0
            ? categories.map(cat => cat.name).filter(Boolean)
            : [];
        const availableUnits = Array.isArray(UNITS) && UNITS.length > 0
            ? UNITS.slice()
            : ['шт'];

        function populateSelect(select, options, selectedValue = '', placeholder = 'Не выбрано') {
            const uniqueOptions = Array.from(new Set((options || [])
                .map(option => (option ?? '').trim())
                .filter(option => option)));

            const parts = [];
            if (placeholder) {
                parts.push(`<option value=""${selectedValue ? '' : ' selected'}>${placeholder}</option>`);
            }

            uniqueOptions.forEach(option => {
                const isSelected = option === selectedValue;
                parts.push(`<option value="${option}"${isSelected ? ' selected' : ''}>${option}</option>`);
            });

            if (selectedValue && !uniqueOptions.includes(selectedValue)) {
                parts.push(`<option value="${selectedValue}" selected>${selectedValue}</option>`);
            }

            select.innerHTML = parts.join('');
        }

        function createMaterialItem(initialData = {}) {
            const item = document.createElement('div');
            item.className = 'report-work-item add-material-item';

            item.innerHTML = `
                <div class="modal-form-group">
                    <label>Раздел</label>
                    <select class="editable" data-field="category"></select>
                </div>
                <div class="modal-form-group">
                    <label>Наименование</label>
                    <input type="text" class="editable" data-field="name" placeholder="Название материала" value="${initialData.name || ''}" required>
                </div>
                <div class="modal-form-group">
                    <label>Единица измерения</label>
                    <select class="editable" data-field="unit"></select>
                </div>
                <div class="modal-form-group">
                    <label>Количество</label>
                    <input type="number" class="editable" data-field="quantity" step="1" min="0" value="${initialData.quantity ?? 0}">
                </div>
                <button type="button" class="secondary remove-add-material-button">Удалить</button>
            `;

            const categorySelect = item.querySelector('select[data-field="category"]');
            populateSelect(categorySelect, availableCategories, initialData.category || '', 'Выберите раздел');

            const unitSelect = item.querySelector('select[data-field="unit"]');
            populateSelect(unitSelect, availableUnits, initialData.unit || '', 'Выберите единицу измерения');

            const removeButton = item.querySelector('.remove-add-material-button');
            removeButton.addEventListener('click', () => {
                item.remove();
                if (!itemsContainer.querySelector('.add-material-item')) {
                    addMaterialEntry();
                }
            });

            return item;
        }

        function addMaterialEntry(initialData = {}) {
            const item = createMaterialItem(initialData);
            itemsContainer.appendChild(item);
        }

        addItemButton.addEventListener('click', () => addMaterialEntry());
        cancelButton.addEventListener('click', () => {
            overlay.remove();
        });

        overlay.addEventListener('click', event => {
            if (event.target === overlay) {
                overlay.remove();
            }
        });

        content.addEventListener('click', event => event.stopPropagation());

        addMaterialEntry();

        form.addEventListener('submit', async event => {
            event.preventDefault();

            const items = Array.from(itemsContainer.querySelectorAll('.add-material-item'));
            if (items.length === 0) {
                showNotification('Добавьте хотя бы один материал', 'error');
                return;
            }

            const materialsPayload = [];

            for (const item of items) {
                const getField = selector => item.querySelector(selector);

                const categorySelect = getField('select[data-field="category"]');
                const nameInput = getField('input[data-field="name"]');
                const unitSelect = getField('select[data-field="unit"]');
                const quantityInput = getField('input[data-field="quantity"]');

                const name = (nameInput?.value || '').trim();
                const category = (categorySelect?.value || '').trim();
                const unit = (unitSelect?.value || '').trim();
                const quantity = parseFloat(quantityInput?.value || '0') || 0;

                if (!category) {
                    showNotification('Выберите раздел для материала', 'error');
                    categorySelect.focus();
                    return;
                }

                if (!name) {
                    showNotification('Наименование материала не может быть пустым', 'error');
                    nameInput.focus();
                    return;
                }

                if (!unit) {
                    showNotification('Выберите единицу измерения', 'error');
                    unitSelect.focus();
                    return;
                }

                if (quantity < 0) {
                    showNotification('Количество не может быть отрицательным', 'error');
                    quantityInput.focus();
                    return;
                }

                materialsPayload.push({
                    name,
                    category,
                    unit,
                    quantity,
                    performed_by: getCurrentUsername()
                });
            }

            submitButton.disabled = true;
            cancelButton.disabled = true;
            addItemButton.disabled = true;

            let successCount = 0;
            const errorMessages = [];

            for (const materialData of materialsPayload) {
                try {
                    showNotification(`Добавление материала "${materialData.name}"...`, 'success');

                    const response = await makeApiRequest(API_CONFIG.ENDPOINTS.MATERIALS, {
                        method: 'POST',
                        body: JSON.stringify(materialData)
                    });

                    if (response && response.success) {
                        successCount++;
                    } else {
                        const errorMessage = response?.detail || response?.error || 'Не удалось добавить материал';
                        errorMessages.push(errorMessage);
                    }
                } catch (error) {
                    errorMessages.push('Ошибка при добавлении материала: ' + error.message);
                }
            }

            if (successCount > 0) {
                materialHistoryLoaded = false;
                await loadMaterials();
                overlay.remove();
                showNotification(`Материалов успешно добавлено: ${successCount}`, 'success');
            } else {
                submitButton.disabled = false;
                cancelButton.disabled = false;
                addItemButton.disabled = false;
            }

            if (errorMessages.length > 0) {
                showNotification(errorMessages.join('\n'), 'error');
            }
        });
    }

    async function saveMaterial(materialId) {
        const row = document.querySelector(`#materialsTableBody tr[data-material-id="${materialId}"]`);
        if (!row) {
            showNotification('Строка материала не найдена', 'error');
            return;
        }

        const inputs = row.querySelectorAll('.editable');
        const materialData = {};
        inputs.forEach(input => {
            const field = input.getAttribute('data-field');
            materialData[field] = input.value;
        });

        materialData.performed_by = getCurrentUsername();

        if (!materialData.name || !materialData.category || !materialData.unit) {
            showNotification('Заполните все обязательные поля для материала', 'error');
            return;
        }

        materialData.quantity = parseFloat(materialData.quantity);
        if (isNaN(materialData.quantity) || materialData.quantity < 0) {
            showNotification('Количество должно быть числом больше или равным нулю', 'error');
            return;
        }

        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.MATERIALS}/${materialId}`, {
                method: 'PUT',
                body: JSON.stringify(materialData)
            });

            if (response && response.success) {
                showNotification('Материал успешно обновлен', 'success');
                materialHistoryLoaded = false;
                await loadMaterials();
            } else {
                const errorMessage = response?.detail || response?.error || 'Не удалось обновить материал';
                showNotification(errorMessage, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при обновлении материала: ' + error.message, 'error');
        }
    }

    async function deleteMaterial(materialId) {
        if (!confirm('Вы уверены, что хотите удалить этот материал?')) {
            return;
        }

        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.MATERIALS}/${materialId}`, {
                method: 'DELETE'
            });

            if (response && response.success) {
                showNotification('Материал успешно удален', 'success');
                materialHistoryLoaded = false;
                await loadMaterials();
            } else {
                const errorMessage = response?.detail || response?.error || 'Не удалось удалить материал';
                showNotification(errorMessage, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при удалении материала: ' + error.message, 'error');
        }
    }

    async function exportMaterialsToExcel() {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.MATERIALS_EXPORT), {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Ошибка скачивания файла');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `materials_export_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            showNotification('Файл успешно скачан', 'success');
        } catch (error) {
            showNotification('Ошибка при экспорте материалов: ' + error.message, 'error');
        }
    }

    function triggerImportMaterials() {
        const importInput = document.getElementById('materialsImportInput');
        if (importInput) {
            importInput.click();
        }
    }

    async function handleMaterialsImport(event) {
        const file = event.target.files[0];
        if (!file) return;
        event.target.value = '';

        try {
            const formData = new FormData();
            formData.append('file', file);

            const token = localStorage.getItem('token');
            const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.MATERIALS_IMPORT), {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                body: formData
            });

            const responseText = await response.text();
            let result = {};
            try {
                result = responseText ? JSON.parse(responseText) : {};
            } catch (parseError) {
                throw new Error('Не удалось обработать ответ сервера');
            }

            if (!response.ok || !result.success) {
                const errorMessage = result.detail || result.error || 'Ошибка при импорте материалов';
                throw new Error(errorMessage);
            }

            await loadMaterials();
            materialHistoryLoaded = false;

            let message = result.message || 'Импорт успешно выполнен';
            if (result.errors && result.errors.length > 0) {
                message += `. Ошибок: ${result.errors.length}`;
                console.warn('Ошибки импорта материалов:', result.errors);
                showNotification(message, 'warning');
            } else {
                showNotification(message, 'success');
            }
        } catch (error) {
            showNotification('Ошибка при импорте материалов: ' + error.message, 'error');
        }
    }

    async function downloadMaterialsTemplate() {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.MATERIALS_TEMPLATE), {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Ошибка скачивания шаблона');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'materials_template.xlsx';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            showNotification('Шаблон успешно скачан', 'success');
        } catch (error) {
            showNotification('Ошибка при скачивании шаблона: ' + error.message, 'error');
        }
    }

    // ========== КАТЕГОРИИ ==========
    async function loadCategories() {
        try {
            const data = await makeApiRequest(API_CONFIG.ENDPOINTS.CATEGORIES);
            if (data.success) {
                categories = data.data || [];
                if (document.getElementById('works').classList.contains('active')) {
                    await loadWorks();
                }
                displayMaterials(materials);
                const foremanSectionsModal = document.getElementById('foremanSectionsModal');
                if (foremanSectionsModal && foremanSectionsModal.style.display === 'flex') {
                    populateForemanSectionsSelect();
                    displayForemanSectionsList();
                }
            } else {
                showNotification('Ошибка при загрузке разделов: ' + data.error, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при загрузке разделов: ' + error.message, 'error');
        }
    }
    
    function displayCategoriesInModal() {
        const categoriesList = document.getElementById('categoriesList');
        categoriesList.innerHTML = '';
        
        if (categories.length === 0) {
            categoriesList.innerHTML = '<div style="text-align: center; color: var(--accent); opacity: 0.7;">Нет разделов</div>';
            return;
        }
        
        categories.forEach(category => {
            const categoryItem = document.createElement('div');
            categoryItem.className = 'category-item';
            categoryItem.dataset.categoryId = category.id;

            const nameSpan = document.createElement('span');
            nameSpan.className = 'category-name';
            nameSpan.textContent = category.name;

            const actionsContainer = document.createElement('div');
            actionsContainer.className = 'category-actions';

            const editButton = document.createElement('button');
            editButton.className = 'secondary';
            editButton.textContent = '✏️';
            editButton.addEventListener('click', () => startEditCategory(category.id));

            const deleteButton = document.createElement('button');
            deleteButton.className = 'danger';
            deleteButton.textContent = '🗑️';
            deleteButton.addEventListener('click', () => deleteCategory(category.id));

            actionsContainer.appendChild(editButton);
            actionsContainer.appendChild(deleteButton);

            categoryItem.appendChild(nameSpan);
            categoryItem.appendChild(actionsContainer);

            categoriesList.appendChild(categoryItem);
        });
    }

    function openCategoryModal() {
        displayCategoriesInModal();
        document.getElementById('categoryModal').style.display = 'flex';
        document.getElementById('newCategoryName').value = '';
        document.getElementById('newCategoryName').focus();
    }
    
    function closeCategoryModal() {
        document.getElementById('categoryModal').style.display = 'none';
    }

    function startEditCategory(categoryId) {
        const categoryItem = document.querySelector(`.category-item[data-category-id="${categoryId}"]`);
        if (!categoryItem) {
            return;
        }

        const category = categories.find(cat => cat.id === categoryId);
        if (!category) {
            return;
        }

        categoryItem.classList.add('editing');
        categoryItem.innerHTML = '';

        const input = document.createElement('input');
        input.type = 'text';
        input.value = category.name;
        input.className = 'login-input';
        input.setAttribute('data-category-edit', 'true');

        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'category-actions';

        const saveButton = document.createElement('button');
        saveButton.className = 'success';
        saveButton.textContent = '💾';
        saveButton.addEventListener('click', () => confirmEditCategory(categoryId));

        const cancelButton = document.createElement('button');
        cancelButton.className = 'secondary';
        cancelButton.textContent = '↩️';
        cancelButton.addEventListener('click', () => cancelEditCategory(categoryId));

        actionsContainer.appendChild(saveButton);
        actionsContainer.appendChild(cancelButton);

        categoryItem.appendChild(input);
        categoryItem.appendChild(actionsContainer);

        input.focus();
        input.select();

        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                confirmEditCategory(categoryId);
            } else if (event.key === 'Escape') {
                event.preventDefault();
                cancelEditCategory(categoryId);
            }
        });
    }

    function cancelEditCategory(categoryId) {
        displayCategoriesInModal();
        const list = document.getElementById('categoriesList');
        if (list) {
            const item = list.querySelector(`.category-item[data-category-id="${categoryId}"] input[data-category-edit]`);
            if (item) {
                item.blur();
            }
        }
    }

    async function confirmEditCategory(categoryId) {
        const category = categories.find(cat => cat.id === categoryId);
        if (!category) {
            return;
        }

        const categoryItem = document.querySelector(`.category-item[data-category-id="${categoryId}"]`);
        const input = categoryItem ? categoryItem.querySelector('input[data-category-edit]') : null;
        const newName = input ? input.value.trim() : '';

        if (!newName) {
            showNotification('Введите название раздела', 'error');
            if (input) {
                input.focus();
            }
            return;
        }

        if (category.name === newName) {
            displayCategoriesInModal();
            return;
        }

        try {
            showNotification('Обновление раздела...', 'success');
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.CATEGORIES}/${categoryId}`, {
                method: 'PUT',
                body: JSON.stringify({ name: newName })
            });

            if (response && response.success) {
                showNotification('Раздел успешно обновлен', 'success');
                await loadCategories();
                displayCategoriesInModal();
            } else {
                const errorMessage = response?.error || response?.detail || 'Не удалось обновить раздел';
                showNotification(`Ошибка: ${errorMessage}`, 'error');
                displayCategoriesInModal();
            }
        } catch (error) {
            showNotification('Ошибка при обновлении раздела: ' + error.message, 'error');
            displayCategoriesInModal();
        }
    }

    async function saveNewCategory() {
        const categoryName = document.getElementById('newCategoryName').value.trim();
        if (!categoryName) {
            showNotification('Введите название раздела', 'error');
            return;
        }

        try {
            showNotification('Добавление раздела...', 'success');
            const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.CATEGORIES), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ name: categoryName })
            });
            
            const categoryAdded = await checkIfCategoryExists(categoryName);
            
            if (categoryAdded) {
                showNotification('Раздел успешно добавлен', 'success');
                document.getElementById('newCategoryName').value = '';
                displayCategoriesInModal();
                if (document.getElementById('works').classList.contains('active')) {
                    await loadWorks();
                }
            } else {
                let errorMessage = 'Раздел не был добавлен в базу данных';
                try {
                    const errorText = await response.text();
                    if (errorText) {
                        const errorData = JSON.parse(errorText);
                        errorMessage = errorData.detail || errorData.error || errorMessage;
                    }
                } catch (e) {}
                showNotification(`Ошибка: ${errorMessage}`, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при добавлении раздела: ' + error.message, 'error');
        }
    }

    async function checkIfCategoryExists(categoryName, maxAttempts = 5) {
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            await loadCategories();
            const exists = categories.some(cat => cat.name === categoryName);
            if (exists) return true;
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        return false;
    }
    
    async function deleteCategory(categoryId) {
        if (!confirm('Вы уверены, что хотите удалить этот раздел?')) {
            return;
        }
        
        try {
            const categoryToDelete = categories.find(cat => cat.id === categoryId);
            if (!categoryToDelete) return;
            
            const categoryName = categoryToDelete.name;
            const response = await fetch(buildApiUrl(`${API_CONFIG.ENDPOINTS.CATEGORIES}/${categoryId}`), {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            await new Promise(resolve => setTimeout(resolve, 1000));
            await loadCategories();
            
            const categoryStillExists = categories.some(cat => cat.id === categoryId);
            
            if (!categoryStillExists) {
                showNotification('Раздел успешно удален', 'success');
                displayCategoriesInModal();
                if (document.getElementById('works').classList.contains('active')) {
                    await loadWorks();
                }
            } else {
                let errorMessage = 'Раздел не был удален из базы данных';
                try {
                    const errorText = await response.text();
                    if (errorText) {
                        const errorData = JSON.parse(errorText);
                        errorMessage = errorData.detail || errorData.error || errorMessage;
                    }
                } catch (e) {}
                showNotification(`Ошибка: ${errorMessage}`, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при удалении раздела: ' + error.message, 'error');
        }
    }

    // ========== ФУНКЦИИ ДЛЯ ДОБАВЛЕНИЯ БАЛАНСА ==========
    function addBalance(workId) {
        const work = works.find(w => w.id === workId);
        if (!work) return;
        
        currentWorkIdForBalance = workId;
        currentWorkBalance = parseFloat(work['На балансе']) || 0;
        
        document.getElementById('balanceWorkName').textContent = work['Название работы'];
        document.getElementById('currentBalance').textContent = currentWorkBalance + ' ' + work['Единица измерения'];
        document.getElementById('addBalanceAmount').value = '';
        document.getElementById('addBalanceModal').style.display = 'flex';
        document.getElementById('addBalanceAmount').focus();
    }

    function closeAddBalanceModal() {
        document.getElementById('addBalanceModal').style.display = 'none';
        currentWorkIdForBalance = null;
        currentWorkBalance = 0;
    }

    async function confirmAddBalance() {
        const amount = parseFloat(document.getElementById('addBalanceAmount').value);

        if (!amount || amount <= 0) {
            showNotification('Введите положительное число', 'error');
            return;
        }
        
        try {
            const work = works.find(w => w.id === currentWorkIdForBalance);
            if (!work) {
                showNotification('Работа не найдена', 'error');
                return;
            }
            
            showNotification('Добавление к балансу...', 'success');
            
            const response = await fetch(buildApiUrl(`${API_CONFIG.ENDPOINTS.WORKS}/${currentWorkIdForBalance}/add-balance`), {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ amount })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || `HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                showNotification('Баланс успешно обновлен', 'success');
                closeAddBalanceModal();
                
                const balanceCell = document.querySelector(`tr:has(input[value="${currentWorkIdForBalance}"]) td:nth-child(6) input`);
                if (balanceCell) {
                    const newBalance = currentWorkBalance + amount;
                    balanceCell.value = newBalance;
                }
                
                const workIndex = works.findIndex(w => w.id === currentWorkIdForBalance);
                if (workIndex !== -1) {
                    works[workIndex]['На балансе'] = currentWorkBalance + amount;
                }
            } else {
                showNotification('Ошибка при обновлении баланса: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Add balance error:', error);
            showNotification('Ошибка при обновлении баланса: ' + error.message, 'error');
        }
    }

    function addMaterialQuantity(materialId) {
        const material = materials.find(item => item.id === materialId);
        if (!material) {
            showNotification('Материал не найден', 'error');
            return;
        }

        currentMaterialIdForQuantity = materialId;
        currentMaterialQuantity = material.quantity !== undefined && material.quantity !== null
            ? Number(material.quantity)
            : 0;
        currentMaterialUnit = material.unit || '';

        const nameElement = document.getElementById('materialQuantityName');
        if (nameElement) {
            nameElement.textContent = material.name || `ID ${materialId}`;
        }

        const currentQuantityElement = document.getElementById('materialCurrentQuantity');
        if (currentQuantityElement) {
            const formattedQuantity = Number.isFinite(currentMaterialQuantity)
                ? currentMaterialQuantity.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
                : '0';
            currentQuantityElement.textContent = currentMaterialUnit
                ? `${formattedQuantity} ${currentMaterialUnit}`
                : formattedQuantity;
        }

        const amountInput = document.getElementById('addMaterialQuantityAmount');
        if (amountInput) {
            amountInput.value = '';
            amountInput.focus();
        }

        const modal = document.getElementById('addMaterialQuantityModal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    function closeAddMaterialQuantityModal() {
        const modal = document.getElementById('addMaterialQuantityModal');
        if (modal) {
            modal.style.display = 'none';
        }

        currentMaterialIdForQuantity = null;
        currentMaterialQuantity = 0;
        currentMaterialUnit = '';
    }

    async function confirmAddMaterialQuantity() {
        const amountInput = document.getElementById('addMaterialQuantityAmount');
        if (!amountInput) {
            showNotification('Поле количества не найдено', 'error');
            return;
        }

        const amount = parseFloat(amountInput.value);

        if (!amount || amount <= 0) {
            showNotification('Введите положительное число', 'error');
            return;
        }

        if (!currentMaterialIdForQuantity) {
            showNotification('Материал не выбран', 'error');
            return;
        }

        const materialId = currentMaterialIdForQuantity;
        const previousQuantity = currentMaterialQuantity;

        try {
            showNotification('Добавление на склад...', 'success');

            const response = await fetch(buildApiUrl(`${API_CONFIG.ENDPOINTS.MATERIALS}/${materialId}/add-quantity`), {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    amount,
                    performed_by: getCurrentUsername(),
                    description: 'Пополнение через панель управления'
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                const newQuantity = previousQuantity + amount;
                showNotification('Количество материала обновлено', 'success');
                closeAddMaterialQuantityModal();
                materialHistoryLoaded = false;

                const quantityInput = document.querySelector(`#materialsTableBody tr[data-material-id="${materialId}"] input[data-field="quantity"]`);
                if (quantityInput) {
                    quantityInput.value = newQuantity;
                }

                const materialIndex = materials.findIndex(item => item.id === materialId);
                if (materialIndex !== -1) {
                    materials[materialIndex].quantity = newQuantity;
                }
            } else {
                const errorMessage = data.error || data.detail || 'Не удалось обновить количество';
                showNotification('Ошибка при обновлении количества: ' + errorMessage, 'error');
            }
        } catch (error) {
            console.error('Add material quantity error:', error);
            showNotification('Ошибка при обновлении количества: ' + error.message, 'error');
        }
    }

    // ========== БРИГАДИРЫ ==========
    async function loadForemen() {
        const loadingElement = document.getElementById('foremenLoading');
        const tableBody = document.getElementById('foremenTableBody');
        
        loadingElement.style.display = 'block';
        tableBody.innerHTML = '';
        
        try {
            const data = await makeApiRequest(API_CONFIG.ENDPOINTS.FOREMEN);
            
            if (data.success) {
                foremen = data.data || [];
                displayForemen(foremen);
            } else {
                showNotification('Ошибка при загрузке бригадиров: ' + data.error, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при загрузке бригадиров: ' + error.message, 'error');
        } finally {
            loadingElement.style.display = 'none';
        }
    }
    
    function displayForemen(foremenToDisplay) {
        const tableBody = document.getElementById('foremenTableBody');
        tableBody.innerHTML = '';
        
        if (foremenToDisplay.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Нет данных о бригадирах</td></tr>';
            refreshTableSorting('foremenTable');
            return;
        }

        foremenToDisplay.forEach(foreman => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="text" value="${foreman.id}" readonly></td>
                <td><input type="text" value="${foreman.full_name || ''}" class="editable" data-field="full_name"></td>
                <td><input type="text" value="${foreman.position || ''}" class="editable" data-field="position"></td>
                <td><input type="text" value="${foreman.username || ''}" readonly></td>
                <td><input type="text" value="${foreman.registration_date || ''}" readonly></td>
                <td>
                    <select class="editable" data-field="is_active">
                        <option value="1" ${foreman.is_active ? 'selected' : ''}>✅ Доступен</option>
                        <option value="0" ${!foreman.is_active ? 'selected' : ''}>❌ Заблокирован</option>
                    </select>
                </td>
                <td class="action-buttons">
                    <button onclick="saveForeman(${foreman.id})" class="secondary">💾 Сохранить</button>
                    <button onclick="openForemanSections(${foreman.id})" class="secondary" title="Привязать разделы">🧾</button>
                    <button onclick="deleteForeman(${foreman.id})" class="danger">🗑️ Удалить</button>
                </td>
            `;
            tableBody.appendChild(row);
        });

        refreshTableSorting('foremenTable');
    }

    async function openForemanSections(foremanId) {
        const modal = document.getElementById('foremanSectionsModal');
        if (!modal) {
            return;
        }

        const foreman = foremen.find(item => item.id === foremanId);
        if (!foreman) {
            showNotification('Бригадир не найден', 'error');
            return;
        }

        currentForemanIdForSections = foremanId;
        const nameParts = [];
        if (foreman.full_name) {
            nameParts.push(foreman.full_name);
        }
        if (foreman.position) {
            nameParts.push(foreman.position);
        }
        document.getElementById('foremanSectionsName').textContent = nameParts.join(' • ') || `ID ${foremanId}`;

        if (!categories || categories.length === 0) {
            await loadCategories();
        }

        await loadForemanSections(foremanId);
        populateForemanSectionsSelect();
        displayForemanSectionsList();
        const select = document.getElementById('foremanSectionsSelect');
        if (select) {
            select.value = '';
        }

        modal.style.display = 'flex';
    }

    async function loadForemanSections(foremanId) {
        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.FOREMEN}/${foremanId}/sections`);
            if (response && response.success) {
                currentForemanSections = (response.data || []).map(item => ({
                    id: item.id,
                    name: item.name
                }));
            } else {
                currentForemanSections = [];
                const errorMessage = response?.error || response?.detail || 'Не удалось загрузить разделы бригадира';
                showNotification(errorMessage, 'error');
            }
        } catch (error) {
            currentForemanSections = [];
            showNotification('Ошибка при загрузке разделов бригадира: ' + error.message, 'error');
        }
    }

    function populateForemanSectionsSelect() {
        const select = document.getElementById('foremanSectionsSelect');
        if (!select) {
            return;
        }

        const assignedIds = new Set((currentForemanSections || []).map(item => item.id));

        if (!categories || categories.length === 0) {
            select.innerHTML = '<option value="">Нет доступных разделов</option>';
            select.disabled = true;
            return;
        }

        let optionsHtml = '<option value="">Выберите раздел</option>';
        categories.forEach(category => {
            const disabled = assignedIds.has(category.id) ? 'disabled' : '';
            optionsHtml += `<option value="${category.id}" ${disabled}>${category.name}</option>`;
        });

        select.innerHTML = optionsHtml;
        select.disabled = false;
    }

    function displayForemanSectionsList() {
        const listContainer = document.getElementById('foremanSectionsList');
        if (!listContainer) {
            return;
        }

        if (!currentForemanSections || currentForemanSections.length === 0) {
            listContainer.innerHTML = '<div class="foreman-sections-list-empty">Разделы не назначены</div>';
            return;
        }

        const rows = currentForemanSections.map(section => `
            <div class="foreman-sections-list-item" data-section-id="${section.id}">
                <span>${section.name || `ID ${section.id}`}</span>
                <button type="button" class="danger" onclick="removeSectionFromForeman(${section.id})">🗑️</button>
            </div>
        `);

        listContainer.innerHTML = rows.join('');
    }

    function addSectionToForeman() {
        const select = document.getElementById('foremanSectionsSelect');
        if (!select) {
            return;
        }

        const selectedValue = select.value;
        if (!selectedValue) {
            showNotification('Выберите раздел для добавления', 'error');
            return;
        }

        let categoryId;
        try {
            categoryId = parseInt(selectedValue, 10);
        } catch (e) {
            categoryId = NaN;
        }

        if (!Number.isInteger(categoryId) || categoryId <= 0) {
            showNotification('Некорректный идентификатор раздела', 'error');
            return;
        }

        if (currentForemanSections.some(section => section.id === categoryId)) {
            showNotification('Раздел уже добавлен', 'error');
            return;
        }

        const category = categories.find(cat => cat.id === categoryId);
        if (!category) {
            showNotification('Раздел не найден в списке разделов', 'error');
            return;
        }

        currentForemanSections = [...currentForemanSections, { id: category.id, name: category.name }];
        displayForemanSectionsList();
        populateForemanSectionsSelect();
        select.value = '';
    }

    function removeSectionFromForeman(categoryId) {
        currentForemanSections = currentForemanSections.filter(section => section.id !== categoryId);
        displayForemanSectionsList();
        populateForemanSectionsSelect();
    }

    async function saveForemanSections() {
        if (!currentForemanIdForSections) {
            showNotification('Не выбран бригадир для сохранения разделов', 'error');
            return;
        }

        const categoryIds = currentForemanSections.map(section => section.id);

        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.FOREMEN}/${currentForemanIdForSections}/sections`, {
                method: 'PUT',
                body: JSON.stringify({ category_ids: categoryIds })
            });

            if (response && response.success) {
                const updatedSections = Array.isArray(response.data) ? response.data : null;
                if (updatedSections) {
                    currentForemanSections = updatedSections.map(item => ({ id: item.id, name: item.name }));
                    displayForemanSectionsList();
                    populateForemanSectionsSelect();
                }
                showNotification('Разделы бригадира обновлены', 'success');
            } else {
                const errorMessage = response?.error || response?.detail || 'Не удалось сохранить разделы бригадира';
                showNotification(errorMessage, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при сохранении разделов: ' + error.message, 'error');
        }
    }

    function closeForemanSectionsModal() {
        const modal = document.getElementById('foremanSectionsModal');
        if (modal) {
            modal.style.display = 'none';
        }
        currentForemanIdForSections = null;
        currentForemanSections = [];
        const select = document.getElementById('foremanSectionsSelect');
        if (select) {
            select.value = '';
        }
        displayForemanSectionsList();
        populateForemanSectionsSelect();
    }

    async function saveForeman(foremanId) {
        const row = document.querySelector(`tr:has(input[value="${foremanId}"])`);
        const inputs = row.querySelectorAll('.editable');

        const foremanData = { id: foremanId };
        inputs.forEach(input => {
            const field = input.getAttribute('data-field');
            let value = input.value;
            
            if (field === 'is_active') value = parseInt(value);
            
            foremanData[field] = value;
        });
        
        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.FOREMEN}/${foremanId}`, {
                method: 'PUT',
                body: JSON.stringify(foremanData)
            });
            
            if (response.success) {
                showNotification('Данные бригадира успешно обновлены', 'success');
            } else {
                showNotification('Ошибка при обновлении бригадира: ' + (response.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            showNotification('Ошибка при обновлении бригадира: ' + error.message, 'error');
        }
    }

    async function deleteForeman(foremanId) {
        if (!confirm('Вы уверены, что хотите удалить этого бригадира? Это действие нельзя отменить.')) {
            return;
        }
        
        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.FOREMEN}/${foremanId}`, {
                method: 'DELETE'
            });
            
            if (response.success) {
                showNotification('Бригадир успешно удален', 'success');
                await loadForemen();
            } else {
                showNotification('Ошибка при удалении бригадира: ' + (response.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            showNotification('Ошибка при удалении бригадира: ' + error.message, 'error');
        }
    }
    
    async function saveAllForemen() {
        const button = document.getElementById('saveAllForemen');
        const rows = document.querySelectorAll('#foremenTableBody tr');

        if (!rows.length) {
            showNotification('Нет бригадиров для сохранения', 'error');
            return;
        }

        if (button) {
            button.disabled = true;
        }

        const updates = [];

        rows.forEach(row => {
            const idInput = row.querySelector('td:first-child input');
            if (!idInput) {
                return;
            }

            const foremanId = parseInt(idInput.value, 10);
            if (!Number.isInteger(foremanId)) {
                return;
            }

            const foremanData = { id: foremanId };
            row.querySelectorAll('.editable').forEach(input => {
                const field = input.getAttribute('data-field');
                if (!field) {
                    return;
                }

                let value = input.value;
                if (field === 'is_active') {
                    value = parseInt(value, 10);
                }

                foremanData[field] = value;
            });

            updates.push(foremanData);
        });

        if (!updates.length) {
            if (button) {
                button.disabled = false;
            }
            showNotification('Нет данных для сохранения', 'error');
            return;
        }

        let successCount = 0;
        const failedIds = [];

        for (const foremanData of updates) {
            try {
                const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.FOREMEN}/${foremanData.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(foremanData)
                });

                if (response && response.success) {
                    successCount += 1;
                } else {
                    failedIds.push(foremanData.id);
                }
            } catch (error) {
                console.error('Bulk foreman update error:', error);
                failedIds.push(foremanData.id);
            }
        }

        if (button) {
            button.disabled = false;
        }

        if (successCount > 0) {
            await loadForemen();
            showNotification(`Данные ${successCount} бригадиров сохранены`, 'success');
        }

        if (failedIds.length > 0) {
            showNotification(`Ошибка сохранения для бригадиров: ${failedIds.join(', ')}`, 'error');
        }
    }
    
    function filterForemen() {
        const searchTerm = document.getElementById('searchForemen').value.toLowerCase();
        const filteredForemen = foremen.filter(foreman =>
            (foreman.full_name && foreman.full_name.toLowerCase().includes(searchTerm)) ||
            (foreman.position && foreman.position.toLowerCase().includes(searchTerm)) ||
            (foreman.username && foreman.username.toLowerCase().includes(searchTerm))
        );
        displayForemen(filteredForemen);
    }
    
    // ========== ОТЧЕТЫ ==========
    async function loadReports() {
        const loadingElement = document.getElementById('reportsLoading');
        const tableBody = document.getElementById('reportsTableBody');
        
        loadingElement.style.display = 'block';
        tableBody.innerHTML = '';
        
        try {
            reports = [];
            displayReports(reports);
        } catch (error) {
            showNotification('Ошибка при загрузке отчетов: ' + error.message, 'error');
        } finally {
            loadingElement.style.display = 'none';
        }
    }
    
    function displayReports(reportsToDisplay) {
        const tableBody = document.getElementById('reportsTableBody');
        tableBody.innerHTML = '';

        if (reportsToDisplay.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Нет данных об отчетах</td></tr>';
            refreshTableSorting('reportsTable');
            return;
        }

        refreshTableSorting('reportsTable');
    }
    
    function addNewReport() {
        showNotification('Функция добавления отчета будет реализована в следующем обновлении', 'success');
    }
    
    async function saveAllReports() {
        showNotification('Функция сохранения отчетов будет реализована в следующем обновлении', 'success');
    }
    
    function filterReports() {}

    // ========== НАКОПИТЕЛЬНАЯ ВЕДОМОСТЬ ==========
    let accumulativeData = [];

    function initializeAccumulativeTab() {
        document.getElementById('refreshAccumulative').addEventListener('click', loadAccumulativeStatement);
        document.getElementById('exportAccumulative').addEventListener('click', exportAccumulativeToExcel);
        document.getElementById('searchAccumulative').addEventListener('input', filterAccumulative);
        document.getElementById('foremanFilterButton').addEventListener('click', toggleForemanDropdown);
        document.addEventListener('click', handleForemanDropdownOutsideClick);
    }

    async function loadAccumulativeStatement() {
        const loadingElement = document.getElementById('accumulativeLoading');
        const tableBody = document.getElementById('accumulativeTableBody');

        loadingElement.style.display = 'block';
        tableBody.innerHTML = '';

        try {
            const query = selectedAccumulativeForemanId ? `?foreman_id=${selectedAccumulativeForemanId}` : '';
            const data = await makeApiRequest(`/api/accumulative-statement${query}`);

            if (data.success) {
                accumulativeData = data.data || [];
                accumulativeForemen = data.foremen || [];
                updateAccumulativeForemanButton();
                populateForemanDropdown();
                displayAccumulativeStatement(accumulativeData);
            } else {
                showNotification('Ошибка при загрузке накопительной ведомости: ' + data.error, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при загрузке накопительной ведомости: ' + error.message, 'error');
        } finally {
            loadingElement.style.display = 'none';
        }
    }

    function updateAccumulativeForemanButton() {
        const button = document.getElementById('foremanFilterButton');
        if (!button) {
            return;
        }

        const selectedForeman = accumulativeForemen.find(foreman => String(foreman.id) === String(selectedAccumulativeForemanId));
        const label = selectedForeman ? selectedForeman.full_name : 'Все бригадиры';
        button.textContent = `👷 ${label}`;
    }

    function populateForemanDropdown() {
        const dropdownMenu = document.getElementById('foremanDropdownMenu');
        if (!dropdownMenu) {
            return;
        }

        dropdownMenu.innerHTML = '';

        const allOption = document.createElement('button');
        allOption.className = 'dropdown-item';
        allOption.type = 'button';
        allOption.textContent = 'Все бригадиры';
        allOption.addEventListener('click', () => selectAccumulativeForeman(null));
        dropdownMenu.appendChild(allOption);

        accumulativeForemen.forEach(foreman => {
            const option = document.createElement('button');
            option.className = 'dropdown-item';
            option.type = 'button';
            option.textContent = foreman.full_name || `ID ${foreman.id}`;
            option.addEventListener('click', () => selectAccumulativeForeman(foreman.id));
            dropdownMenu.appendChild(option);
        });
    }

    function toggleForemanDropdown(event) {
        event.stopPropagation();
        const dropdownMenu = document.getElementById('foremanDropdownMenu');
        if (!dropdownMenu) {
            return;
        }
        dropdownMenu.classList.toggle('show');
    }

    function handleForemanDropdownOutsideClick(event) {
        const dropdown = document.getElementById('accumulativeForemanDropdown');
        const dropdownMenu = document.getElementById('foremanDropdownMenu');

        if (!dropdown || !dropdownMenu) {
            return;
        }

        if (!dropdown.contains(event.target)) {
            dropdownMenu.classList.remove('show');
        }
    }

    function selectAccumulativeForeman(foremanId) {
        selectedAccumulativeForemanId = foremanId;
        updateAccumulativeForemanButton();
        const dropdownMenu = document.getElementById('foremanDropdownMenu');
        if (dropdownMenu) {
            dropdownMenu.classList.remove('show');
        }
        loadAccumulativeStatement();
    }

    function displayAccumulativeStatement(data) {
        const tableBody = document.getElementById('accumulativeTableBody');
        tableBody.innerHTML = '';
        
        if (data.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Нет данных</td></tr>';
            refreshTableSorting('accumulativeTable');
            return;
        }

        data.forEach(item => {
            const sectionName = item.Раздел || item.Категория || '';
            const row = document.createElement('tr');
            const quantityValue = Number(item.Количество);
            const projectValue = Number(item.Проект);
            const percentValue = Number(item['%Выполнения']);
            const unitCost = Number(item['Стоимость за единицу'] ?? 0);
            const totalCost = Number(item['Сумма'] ?? 0);
            row.innerHTML = `
                <td>${sectionName}</td>
                <td>${item.Работа}</td>
                <td>${item['Единица измерения']}</td>
                <td data-sort-value="${Number.isFinite(unitCost) ? unitCost : ''}">${formatMoneyValue(unitCost)}</td>
                <td data-sort-value="${Number.isFinite(quantityValue) ? quantityValue : ''}">${item.Количество}</td>
                <td data-sort-value="${Number.isFinite(projectValue) ? projectValue : ''}">${item.Проект}</td>
                <td data-sort-value="${Number.isFinite(percentValue) ? percentValue : ''}">${item['%Выполнения']}%</td>
                <td data-sort-value="${Number.isFinite(totalCost) ? totalCost : ''}">${formatMoneyValue(totalCost)}</td>
            `;
            tableBody.appendChild(row);
        });

        refreshTableSorting('accumulativeTable');
    }

    function filterAccumulative() {
        const searchTerm = document.getElementById('searchAccumulative').value.toLowerCase();
        const filteredData = accumulativeData.filter(item => {
            const sectionValue = (item.Раздел || item.Категория || '').toLowerCase();
            return sectionValue.includes(searchTerm) || item.Работа.toLowerCase().includes(searchTerm);
        });
        displayAccumulativeStatement(filteredData);
    }

    async function exportAccumulativeToExcel() {
        try {
            showNotification('Подготовка файла для скачивания...', 'success');
            
            const workbook = XLSX.utils.book_new();
            workbook.Props = {
                Title: "Накопительная ведомость",
                Subject: "Накопительная ведомость выполненных работ",
                Author: "WiTech System",
                CreatedDate: new Date()
            };

            const exportData = accumulativeData.map(item => ({
                'Раздел': item.Раздел || item.Категория || '',
                'Работа': item.Работа,
                'Единица измерения': item['Единица измерения'],
                'Стоимость за единицу': formatMoneyValue(item['Стоимость за единицу']),
                'Количество': item.Количество,
                'Проектное число': item.Проект,
                '% выполнения': item['%Выполнения'],
                'Сумма': formatMoneyValue(item['Сумма'])
            }));

            const worksheet = XLSX.utils.json_to_sheet(exportData);
            
            const colWidths = [
                { wch: 25 },
                { wch: 40 },
                { wch: 18 },
                { wch: 18 },
                { wch: 16 },
                { wch: 18 },
                { wch: 18 },
                { wch: 18 }
            ];
            worksheet['!cols'] = colWidths;

            XLSX.utils.book_append_sheet(workbook, worksheet, "Накопительная ведомость");

            const fileName = `accumulative_statement_${new Date().toISOString().split('T')[0]}.xlsx`;
            XLSX.writeFile(workbook, fileName);
            
            showNotification('Файл успешно скачан', 'success');
        } catch (error) {
            console.error('Export error:', error);
            showNotification('Ошибка при экспорте файла: ' + error.message, 'error');
        }
    }

    // ========== ВСЕ ОТЧЕТЫ ==========
    async function loadAllReports() {
        const loadingElement = document.getElementById('allReportsLoading');
        const tableBody = document.getElementById('allReportsTableBody');
        
        loadingElement.style.display = 'block';
        tableBody.innerHTML = '';
        
        try {
            const data = await makeApiRequest(API_CONFIG.ENDPOINTS.ALL_REPORTS);
            
            if (data.success) {
                allReports = data.data || [];
                displayAllReportsTable(allReports);
            } else {
                showNotification('Ошибка при загрузке отчетов: ' + data.error, 'error');
            }
        } catch (error) {
            showNotification('Ошибка при загрузке отчетов: ' + error.message, 'error');
        } finally {
            loadingElement.style.display = 'none';
        }
    }
    
    function displayAllReportsTable(reportsToDisplay) {
        const tableBody = document.getElementById('allReportsTableBody');
        tableBody.innerHTML = '';
        
        if (reportsToDisplay.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Нет данных об отчетах</td></tr>';
            refreshTableSorting('allReportsTable');
            return;
        }

        reportsToDisplay.forEach(report => {
            const photoLink = report.photo_report_url ?
                `<a href="${report.photo_report_url}" target="_blank" style="color: var(--primary);">📷 Просмотреть</a>` :
                'Нет фото';

            const isVerified = Boolean(report.is_verified);
            const verifyButtonClass = `verify-button${isVerified ? ' verified' : ''}`;
            const verifyButtonLabel = isVerified ? '✅' : 'Проверить';
            const verifyButtonTitle = isVerified ? 'Отчет подтвержден' : 'Отметить отчет как проверенный';

            const quantityValue = Number(report.quantity);
            const dateSortValue = report.report_date
                ? String(report.report_date).replace(' ', 'T')
                : '';
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${report.id}</td>
                <td>${report.foreman_name || 'Неизвестно'}</td>
                <td>${report.foreman_position || '—'}</td>
                <td>${report.work_name || 'Неизвестно'}</td>
                <td data-sort-value="${Number.isFinite(quantityValue) ? quantityValue : ''}">${report.quantity} ${report.unit || 'шт'}</td>
                <td data-sort-value="${dateSortValue}">${report.report_date}</td>
                <td>${report.report_time}</td>
                <td>${photoLink}</td>
                <td class="action-buttons">
                    <button onclick="editReport(${report.id})" class="secondary">✏️</button>
                    <button onclick="deleteReport(${report.id})" class="danger">🗑️</button>
                    <button onclick="toggleReportVerification(${report.id}, ${!isVerified})" class="${verifyButtonClass}" title="${verifyButtonTitle}">${verifyButtonLabel}</button>
                </td>
            `;
            tableBody.appendChild(row);
        });

        refreshTableSorting('allReportsTable');
    }
    
    async function deleteReport(reportId) {
        if (confirm('Вы уверены, что хотите удалить этот отчет?')) {
            try {
                const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.REPORT}/${reportId}`, {
                    method: 'DELETE'
                });
                
                if (response.success) {
                    showNotification('Отчет успешно удален', 'success');
                    loadAllReports();
                } else {
                    showNotification('Ошибка при удалении отчета: ' + (response.error || 'Неизвестная ошибка'), 'error');
                }
            } catch (error) {
                showNotification('Ошибка при удалении отчета: ' + error.message, 'error');
            }
        }
    }

    async function toggleReportVerification(reportId, shouldVerify) {
        try {
            const response = await makeApiRequest(`${API_CONFIG.ENDPOINTS.REPORT}/${reportId}/verify`, {
                method: 'POST',
                body: JSON.stringify({ is_verified: shouldVerify })
            });

            if (response.success) {
                const updatedStatus = response.data?.is_verified ?? shouldVerify;
                const reportIndex = allReports.findIndex(report => report.id === reportId);
                if (reportIndex !== -1) {
                    allReports[reportIndex].is_verified = updatedStatus;
                }

                const message = updatedStatus ? 'Отчет отмечен как проверенный' : 'Отметка проверки снята';
                showNotification(message, 'success');

                const searchInput = document.getElementById('searchAllReports');
                if (searchInput && searchInput.value.trim()) {
                    filterAllReports();
                } else {
                    displayAllReportsTable(allReports);
                }
            } else {
                showNotification('Не удалось обновить статус проверки: ' + (response.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            showNotification('Ошибка при обновлении статуса проверки: ' + error.message, 'error');
        }
    }

    function filterAllReports() {
        const searchInput = document.getElementById('searchAllReports');
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';

        const filteredReports = allReports.filter(report =>
            (report.foreman_name && report.foreman_name.toLowerCase().includes(searchTerm)) ||
            (report.foreman_position && report.foreman_position.toLowerCase().includes(searchTerm)) ||
            (report.work_name && report.work_name.toLowerCase().includes(searchTerm)) ||
            (report.report_date && report.report_date.toLowerCase().includes(searchTerm))
        );
        displayAllReportsTable(filteredReports);
    }
    
    // Показать уведомление
    function showNotification(message, type) {
        const notification = document.getElementById('notification');
        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.style.display = 'block';
        
        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);
    }
    
    // Анимация волн
    const waves = document.querySelector('.waves');
    let waveOffset = 0;
    
    function animateWaves() {
        waveOffset += 0.5;
        waves.style.backgroundPositionX = -waveOffset + 'px';
        requestAnimationFrame(animateWaves);
    }

    // Обработчик нажатия Enter в модальном окне добавления баланса
    document.addEventListener('DOMContentLoaded', function() {
        const addBalanceInput = document.getElementById('addBalanceAmount');
        if (addBalanceInput) {
            addBalanceInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    confirmAddBalance();
                }
            });
        }

        const addMaterialQuantityInput = document.getElementById('addMaterialQuantityAmount');
        if (addMaterialQuantityInput) {
            addMaterialQuantityInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    confirmAddMaterialQuantity();
                }
            });
        }
    });
    
    animateWaves();