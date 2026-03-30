// ===== СОВРЕМЕННЫЙ JAVASCRIPT ВЕРСИИ 2.0 =====

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Север-Юг v2.0 загружен');
    
    // Инициализация всех модулей
    initAnimations();
    initNotifications();
    initForms();
    initTooltips();
    initRideCards();
    initMobileMenu();
    initSmoothScroll();
    initLazyLoading();
    initSecurity();
});

// ===== АНИМАЦИИ =====
function initAnimations() {
    // Intersection Observer для анимации при скролле
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.card, .ride-card, .btn').forEach(el => {
        el.classList.add('animate-ready');
        observer.observe(el);
    });
}

// ===== УВЕДОМЛЕНИЯ =====
function initNotifications() {
    // Проверка новых уведомлений каждые 30 секунд
    setInterval(checkNewNotifications, 30000);
    
    // Toast уведомления
    window.showToast = function(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            </div>
            <div class="toast-message">${message}</div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => toast.classList.add('show'), 100);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    };
}

async function checkNewNotifications() {
    try {
        const response = await fetch('/api/notifications/count');
        const data = await response.json();
        if (data.count > 0) {
            updateNotificationBadge(data.count);
        }
    } catch (e) {
        console.log('Не удалось проверить уведомления');
    }
}

function updateNotificationBadge(count) {
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    }
}

// ===== ФОРМЫ =====
function initForms() {
    // Валидация форм в реальном времени
    document.querySelectorAll('input[required], textarea[required]').forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearError);
    });
    
    // Автоформатирование телефона
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', formatPhone);
    });
    
    // Защита от двойной отправки
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Отправка...';
            }
        });
    });
}

function validateField(e) {
    const field = e.target;
    if (!field.value.trim()) {
        showError(field, 'Это поле обязательно');
        return false;
    }
    if (field.type === 'email' && !isValidEmail(field.value)) {
        showError(field, 'Введите корректный email');
        return false;
    }
    if (field.minLength && field.value.length < field.minLength) {
        showError(field, `Минимум ${field.minLength} символов`);
        return false;
    }
    clearError(e);
    return true;
}

function showError(field, message) {
    field.classList.add('is-invalid');
    let errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        field.parentNode.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
}

function clearError(e) {
    e.target.classList.remove('is-invalid');
    const errorDiv = e.target.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) errorDiv.remove();
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function formatPhone(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.startsWith('8')) value = '7' + value.slice(1);
    if (!value.startsWith('7')) value = '7' + value;
    
    let formatted = '+' + value;
    if (value.length > 1) {
        formatted = formatted.slice(0, 2) + ' (' + formatted.slice(2, 5);
    }
    if (value.length > 4) {
        formatted = formatted.slice(0, 7) + ') ' + formatted.slice(7, 10);
    }
    if (value.length > 7) {
        formatted = formatted.slice(0, 11) + '-' + formatted.slice(11, 13);
    }
    if (value.length > 9) {
        formatted = formatted.slice(0, 14) + '-' + formatted.slice(14, 16);
    }
    
    e.target.value = formatted.slice(0, 18);
}

// ===== ПОДСКАЗКИ =====
function initTooltips() {
    // Кастомные тултипы
    document.querySelectorAll('[data-tooltip]').forEach(el => {
        el.addEventListener('mouseenter', showTooltip);
        el.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.textContent = e.target.dataset.tooltip;
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
    tooltip.style.left = rect.left + (rect.width - tooltip.offsetWidth) / 2 + 'px';
    tooltip.classList.add('show');
    
    e.target._tooltip = tooltip;
}

function hideTooltip(e) {
    if (e.target._tooltip) {
        e.target._tooltip.remove();
        e.target._tooltip = null;
    }
}

// ===== КАРТОЧКИ ПОЕЗДОК =====
function initRideCards() {
    // Добавление эффектов при наведении
    document.querySelectorAll('.ride-card').forEach(card => {
        card.addEventListener('click', function() {
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
}

// ===== МОБИЛЬНОЕ МЕНЮ =====
function initMobileMenu() {
    const menuBtn = document.querySelector('.mobile-menu-btn');
    const mobileMenu = document.querySelector('.mobile-menu');
    
    if (menuBtn && mobileMenu) {
        menuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('active');
            menuBtn.classList.toggle('active');
        });
        
        // Закрытие по клику вне меню
        document.addEventListener('click', (e) => {
            if (!mobileMenu.contains(e.target) && !menuBtn.contains(e.target)) {
                mobileMenu.classList.remove('active');
                menuBtn.classList.remove('active');
            }
        });
    }
}

// ===== ПЛАВНЫЙ СКРОЛЛ =====
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                e.preventDefault();
                const target = document.querySelector(targetId);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });
}

// ===== ЛЕНИВАЯ ЗАГРУЗКА =====
function initLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imgObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    imgObserver.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imgObserver.observe(img);
        });
    }
}

// ===== БЕЗОПАСНОСТЬ =====
function initSecurity() {
    // Защита от XSS
    window.escapeHtml = function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };
    
    // Проверка CSRF токена
    window.getCSRFToken = function() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.content : '';
    };
    
    // Безопасный AJAX
    window.safeFetch = async function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        };
        
        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            showToast('Ошибка соединения', 'error');
            throw error;
        }
    };
}

// ===== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ =====

// Копирование в буфер
window.copyToClipboard = async function(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Скопировано в буфер', 'success');
        return true;
    } catch (err) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('Скопировано', 'success');
        return true;
    }
};

// Подтверждение действия
window.confirmAction = function(message) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'confirmation-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <p>${escapeHtml(message)}</p>
                <div class="modal-buttons">
                    <button class="btn btn-cancel">Отмена</button>
                    <button class="btn btn-confirm">Подтвердить</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        modal.querySelector('.btn-confirm').onclick = () => {
            modal.remove();
            resolve(true);
        };
        modal.querySelector('.btn-cancel').onclick = () => {
            modal.remove();
            resolve(false);
        };
    });
};

// Дебаунс для частых событий
window.debounce = function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

console.log('✅ Все системы v2.0 инициализированы');
