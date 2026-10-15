// static/js/dashboard.js
// Dashboard functionality

class Dashboard {
    constructor() {
        this.clients = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadClients();
    }

    bindEvents() {
        // Auto-dismiss alerts after 5 seconds
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.parentElement) {
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateX(100%)';
                    setTimeout(() => {
                        alert.remove();
                    }, 300);
                }
            }, 5000);
        });

        // Close alert manually
        const alertCloses = document.querySelectorAll('.alert-close');
        alertCloses.forEach(close => {
            close.addEventListener('click', () => {
                const alert = close.parentElement;
                alert.style.opacity = '0';
                alert.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    alert.remove();
                }, 300);
            });
        });
    }

    async loadClients() {
        try {
            this.showLoading();
            
            const response = await fetch('/api/clients');
            const data = await response.json();
            
            if (data.success) {
                this.clients = data.clients;
                this.displayClients(this.clients);
                this.updateStats(this.clients);
            } else {
                this.showError('Error loading clients: ' + data.error);
            }
        } catch (error) {
            console.error('Error loading clients:', error);
            this.showError('Error loading clients: ' + error.message);
        }
    }

    showLoading() {
        const loading = document.getElementById('loading');
        const table = document.getElementById('tableContainer');
        const emptyState = document.getElementById('emptyState');
        
        if (loading) loading.style.display = 'block';
        if (table) table.style.display = 'none';
        if (emptyState) emptyState.style.display = 'none';
    }

    hideLoading() {
        const loading = document.getElementById('loading');
        if (loading) loading.style.display = 'none';
    }

    showError(message) {
        this.hideLoading();
        const loading = document.getElementById('loading');
        if (loading) {
            loading.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Error</h3>
                    <p>${message}</p>
                    <button class="btn btn-primary" onclick="dashboard.loadClients()">
                        <i class="fas fa-refresh"></i> Retry
                    </button>
                </div>
            `;
            loading.style.display = 'block';
        }
    }

    displayClients(clients) {
        const tbody = document.getElementById('clientTableBody');
        const table = document.getElementById('tableContainer');
        const emptyState = document.getElementById('emptyState');
        
        this.hideLoading();

        if (clients.length === 0) {
            if (table) table.style.display = 'none';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        if (table) table.style.display = 'block';

        if (tbody) {
            tbody.innerHTML = '';

            clients.forEach(client => {
                const row = document.createElement('tr');
                const timeUntilExpire = this.calculateTimeUntilExpire(client.timestamp, client.Rtoken_expire);
                const isExpired = timeUntilExpire === 'Expired';
                const statusClass = isExpired ? 'status-expired' : 'status-active';
                const statusText = isExpired ? 'Expired' : 'Active';
                const statusIcon = isExpired ? 'fas fa-times-circle' : 'fas fa-check-circle';

                row.innerHTML = `
                    <td>
                        <span class="clickable" onclick="dashboard.navigateToTransactions('${client.ID}')">
                            ${this.escapeHtml(client.ID)}
                        </span>
                    </td>
                    <td>${this.escapeHtml(client.Name)}</td>
                    <td>${timeUntilExpire}</td>
                    <td>${this.formatDate(client.timestamp)}</td>
                    <td>
                        <span class="status-badge ${statusClass}">
                            <i class="${statusIcon}"></i>
                            ${statusText}
                        </span>
                    </td>
                `;

                tbody.appendChild(row);
            });
        }
    }

    // Navigate to transactions page instead of showing modal
    navigateToTransactions(clientId) {
        window.location.href = `/transactions/${encodeURIComponent(clientId)}`;
    }

    updateStats(clients) {
        const total = clients.length;
        let active = 0;
        let expired = 0;

        clients.forEach(client => {
            const timeUntilExpire = this.calculateTimeUntilExpire(client.timestamp, client.Rtoken_expire);
            if (timeUntilExpire === 'Expired') {
                expired++;
            } else {
                active++;
            }
        });

        this.animateCounter('totalClients', total);
        this.animateCounter('activeTokens', active);
        this.animateCounter('expiredTokens', expired);
    }

    animateCounter(elementId, targetValue) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const startValue = 0;
        const duration = 1000; // 1 second
        const startTime = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeOutCubic = 1 - Math.pow(1 - progress, 3);
            const currentValue = Math.floor(startValue + (targetValue - startValue) * easeOutCubic);
            
            element.textContent = currentValue;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.textContent = targetValue;
            }
        };

        requestAnimationFrame(animate);
    }

    calculateTimeUntilExpire(timestamp, expireSeconds) {
        try {
            const createdTime = new Date(timestamp);
            const expireTime = new Date(createdTime.getTime() + (parseInt(expireSeconds) * 1000));
            const now = new Date();

            if (expireTime > now) {
                const remaining = expireTime - now;
                const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
                const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));

                if (days > 0) {
                    return `${days}d ${hours}h ${minutes}m`;
                } else if (hours > 0) {
                    return `${hours}h ${minutes}m`;
                } else {
                    return `${minutes}m`;
                }
            } else {
                return 'Expired';
            }
        } catch (error) {
            console.error('Error calculating time until expire:', error);
            return 'Unknown';
        }
    }

    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            return 'Invalid Date';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    refreshData() {
        this.loadClients();
    }

    // Utility method to show notifications
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.innerHTML = `
            <i class="fas fa-info-circle"></i>
            ${message}
            <button class="alert-close">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Add to flash messages container or create one
        let container = document.querySelector('.flash-messages');
        if (!container) {
            container = document.createElement('div');
            container.className = 'flash-messages';
            const mainContent = document.querySelector('.main-content .container');
            if (mainContent) {
                mainContent.insertBefore(container, mainContent.firstChild);
            }
        }

        container.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    notification.remove();
                }, 300);
            }
        }, 5000);

        // Manual close
        const closeBtn = notification.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    notification.remove();
                }, 300);
            });
        }
    }
}

// Initialize dashboard when DOM is loaded
let dashboard;

document.addEventListener("DOMContentLoaded", function() {
    dashboard = new Dashboard();

    // Add Client Button - Direct redirect (no popup)
    const addBtn = document.getElementById("addBtn");
    if (addBtn) {
        addBtn.addEventListener("click", function(e) {
            e.preventDefault();
            
            // Show loading indicator
            const originalText = addBtn.innerHTML;
            addBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting...';
            addBtn.disabled = true;
            
            // Redirect to QuickBooks OAuth (full page redirect)
            window.location.href = "/auth/quickbooks";
        });
    }
});

// Handle visibility change to refresh data when tab becomes active
// document.addEventListener('visibilitychange', function() {
//     if (!document.hidden && dashboard) {
//         dashboard.refreshData();
//     }
// });

// Export for global access
window.dashboard = dashboard;