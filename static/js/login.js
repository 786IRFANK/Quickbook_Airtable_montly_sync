// static/js/login.js
// Login page functionality

class LoginManager {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupFormValidation();
        this.setupAnimations();
    }

    bindEvents() {
        const form = document.querySelector('.login-form');
        if (form) {
            form.addEventListener('submit', this.handleSubmit.bind(this));
        }

        // Enter key support
        document.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                const activeElement = document.activeElement;
                if (activeElement && (activeElement.tagName === 'INPUT')) {
                    form.dispatchEvent(new Event('submit'));
                }
            }
        });

        // Auto-dismiss alerts
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.parentElement) {
                    this.fadeOutAlert(alert);
                }
            }, 5000);
        });

        // Focus management
        const usernameInput = document.getElementById('username');
        if (usernameInput) {
            usernameInput.focus();
        }
    }

    setupFormValidation() {
        const inputs = document.querySelectorAll('.login-form input');
        
        inputs.forEach(input => {
            // Real-time validation feedback
            input.addEventListener('blur', () => {
                this.validateField(input);
            });

            input.addEventListener('input', () => {
                this.clearFieldError(input);
            });

            // Enhanced focus effects
            input.addEventListener('focus', () => {
                const formGroup = input.closest('.form-group');
                if (formGroup) {
                    formGroup.classList.add('focused');
                }
            });

            input.addEventListener('blur', () => {
                const formGroup = input.closest('.form-group');
                if (formGroup) {
                    formGroup.classList.remove('focused');
                }
            });
        });
    }

    setupAnimations() {
        // Stagger animation for form elements
        const formElements = document.querySelectorAll('.form-group, .btn');
        formElements.forEach((element, index) => {
            element.style.animationDelay = `${index * 0.1}s`;
            element.classList.add('animate-in');
        });
    }

    handleSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const submitBtn = form.querySelector('.btn');
        const username = form.querySelector('#username').value.trim();
        const password = form.querySelector('#password').value;

        // Client-side validation
        if (!this.validateForm(username, password)) {
            return;
        }

        // Show loading state
        this.setLoadingState(submitBtn, true);

        // Submit form after brief delay for better UX
        setTimeout(() => {
            form.submit();
        }, 500);
    }

    validateForm(username, password) {
        let isValid = true;

        // Username validation
        const usernameInput = document.getElementById('username');
        if (!username) {
            this.showFieldError(usernameInput, 'Username is required');
            isValid = false;
        } else if (username.length < 3) {
            this.showFieldError(usernameInput, 'Username must be at least 3 characters');
            isValid = false;
        }

        // Password validation
        const passwordInput = document.getElementById('password');
        if (!password) {
            this.showFieldError(passwordInput, 'Password is required');
            isValid = false;
        } else if (password.length < 6) {
            this.showFieldError(passwordInput, 'Password must be at least 6 characters');
            isValid = false;
        }

        return isValid;
    }

    validateField(input) {
        const value = input.value.trim();
        
        switch (input.type) {
            case 'text': // username
                if (!value) {
                    this.showFieldError(input, 'Username is required');
                } else if (value.length < 3) {
                    this.showFieldError(input, 'Username must be at least 3 characters');
                } else {
                    this.clearFieldError(input);
                }
                break;
                
            case 'password':
                if (!value) {
                    this.showFieldError(input, 'Password is required');
                } else if (value.length < 6) {
                    this.showFieldError(input, 'Password must be at least 6 characters');
                } else {
                    this.clearFieldError(input);
                }
                break;
        }
    }

    showFieldError(input, message) {
        const formGroup = input.closest('.form-group');
        if (!formGroup) return;

        // Remove existing error
        this.clearFieldError(input);

        // Add error styling
        input.classList.add('error');
        formGroup.classList.add('has-error');

        // Create error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            color: #dc3545;
            font-size: 0.8rem;
            margin-top: 0.25rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        `;
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;

        formGroup.appendChild(errorDiv);

        // Shake animation
        input.style.animation = 'shake 0.5s ease-in-out';
        setTimeout(() => {
            input.style.animation = '';
        }, 500);
    }

    clearFieldError(input) {
        const formGroup = input.closest('.form-group');
        if (!formGroup) return;

        input.classList.remove('error');
        formGroup.classList.remove('has-error');

        const existingError = formGroup.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    }

    setLoadingState(button, isLoading) {
        if (isLoading) {
            button.disabled = true;
            button.innerHTML = `
                <div class="spinner"></div>
                Signing In...
            `;
            button.style.cursor = 'not-allowed';
        } else {
            button.disabled = false;
            button.innerHTML = 'Sign In';
            button.style.cursor = 'pointer';
        }
    }

    fadeOutAlert(alert) {
        alert.style.transition = 'all 0.3s ease';
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            if (alert.parentElement) {
                alert.remove();
            }
        }, 300);
    }

    // Show custom notification
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.innerHTML = `
            <i class="fas fa-info-circle"></i>
            ${message}
        `;
        
        const container = document.querySelector('.login-container');
        const form = container.querySelector('.login-form');
        
        container.insertBefore(notification, form);
        
        // Auto remove
        setTimeout(() => {
            this.fadeOutAlert(notification);
        }, 4000);
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-in {
        animation: fadeInUp 0.6s ease forwards;
    }
    
    .form-group input.error {
        border-color: #dc3545;
        box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1);
    }
    
    .form-group.has-error label {
        color: #dc3545;
    }
    
    .spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid transparent;
        border-top: 2px solid currentColor;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-right: 0.5rem;
    }
    
    .form-group.focused::after {
        width: 100%;
    }
    
    .form-group {
        position: relative;
    }
    
    .form-group::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 0;
        height: 2px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        transition: width 0.3s ease;
    }
`;
document.head.appendChild(style);

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new LoginManager();
});

// Handle browser back button
window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        // Clear any cached form data
        const form = document.querySelector('.login-form');
        if (form) {
            form.reset();
        }
    }
});