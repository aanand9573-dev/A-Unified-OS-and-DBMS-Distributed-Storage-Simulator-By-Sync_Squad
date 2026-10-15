/**
 * Global JavaScript utilities for Operating System Simulator.
 */

// Helper API Fetcher
async function apiRequest(url, method = "GET", body = null) {
    const options = {
        method: method,
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        return data;
    } catch (err) {
        console.error(`API Error (${url}):`, err);
        showToast("Network Error", "Failed to communicate with simulator backend.", "danger");
        return { success: false, message: err.message };
    }
}

// Toast Notifications
function showToast(title, message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.style.position = "fixed";
        container.style.bottom = "20px";
        container.style.right = "20px";
        container.style.zIndex = "9999";
        document.body.appendChild(container);
    }

    const toastId = "toast_" + Date.now();
    const bgMap = {
        info: "rgba(59, 130, 246, 0.95)",
        success: "rgba(16, 185, 129, 0.95)",
        warning: "rgba(245, 158, 11, 0.95)",
        danger: "rgba(239, 68, 68, 0.95)"
    };
    const iconMap = {
        info: "fa-info-circle",
        success: "fa-check-circle",
        warning: "fa-exclamation-triangle",
        danger: "fa-times-circle"
    };

    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white border-0 show mb-2 shadow-lg" role="alert" style="background: ${bgMap[type] || bgMap.info}; border-radius: 10px; min-width: 280px; backdrop-filter: blur(8px);">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center gap-2 font-main">
                    <i class="fas ${iconMap[type] || iconMap.info} fs-5"></i>
                    <div>
                        <strong class="d-block">${title}</strong>
                        <span style="font-size: 0.825rem; opacity: 0.95;">${message}</span>
                    </div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="document.getElementById('${toastId}').remove()"></button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML("beforeend", toastHtml);
    setTimeout(() => {
        const el = document.getElementById(toastId);
        if (el) el.remove();
    }, 4500);
}

// Global System Reset
async function resetFullSystem() {
    if (confirm("Are you sure you want to reset all OS simulator modules and clear state?")) {
        const res = await apiRequest("/api/system/reset_all", "POST");
        if (res.success) {
            showToast("System Reset", "All simulator components returned to initial defaults.", "success");
            setTimeout(() => location.reload(), 800);
        }
    }
}

// Update clock in header
function initHeaderClock() {
    const clockEl = document.getElementById("header-clock");
    if (clockEl) {
        const update = () => {
            const now = new Date();
            clockEl.textContent = now.toLocaleTimeString();
        };
        update();
        setInterval(update, 1000);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    initHeaderClock();
});
