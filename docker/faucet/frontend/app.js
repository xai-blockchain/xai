// XAI Testnet Faucet - Frontend Application

let captchaToken = null;

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    prefillAddressFromQuery();
});

async function initializeApp() {
    await checkNetworkStatus();
    await loadFaucetStats();

    // Refresh stats every 30 seconds
    setInterval(loadFaucetStats, 30000);
}

function setupEventListeners() {
    const form = document.getElementById('faucetForm');
    const addressInput = document.getElementById('address');

    form.addEventListener('submit', handleFormSubmit);
    addressInput.addEventListener('input', validateAddress);
}

function prefillAddressFromQuery() {
    const addressInput = document.getElementById('address');
    if (!addressInput) return;

    const params = new URLSearchParams(window.location.search);
    const address = params.get('address');
    if (address) {
        addressInput.value = address.trim();
        validateAddress();
    }
}

// Network status check
async function checkNetworkStatus() {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');

    try {
        const response = await fetch('/health');
        const data = await response.json();

        if (data.status === 'healthy') {
            statusDot.classList.remove('offline');
            statusText.textContent = 'Faucet Online';
        } else {
            statusDot.classList.add('offline');
            statusText.textContent = 'Faucet Issues';
        }
    } catch (error) {
        statusDot.classList.add('offline');
        statusText.textContent = 'Faucet Offline';
        console.error('Network status check failed:', error);
    }
}

// Load faucet statistics
async function loadFaucetStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        // Update faucet amount
        document.getElementById('faucetAmount').textContent = data.faucet_amount;

        // Update statistics
        const dailyRemaining = data.daily_remaining !== null ? data.daily_remaining.toLocaleString() : 'N/A';
        document.getElementById('dailyRemaining').textContent = dailyRemaining + ' XAI';
        document.getElementById('totalRequests').textContent = data.total_requests.toLocaleString();
        document.getElementById('uniqueRecipients').textContent = data.unique_addresses.toLocaleString();
        document.getElementById('uptime').textContent = formatUptime(data.uptime_seconds);
    } catch (error) {
        console.error('Failed to load faucet stats:', error);
    }
}

function formatUptime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 24) {
        const days = Math.floor(hours / 24);
        return days + 'd ' + (hours % 24) + 'h';
    }
    return hours + 'h ' + minutes + 'm';
}

// Form submission handler
async function handleFormSubmit(e) {
    e.preventDefault();

    const address = document.getElementById('address').value.trim();
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoading = submitBtn.querySelector('.btn-loading');

    // Validate address
    if (!validateAddress()) {
        return;
    }

    // Check captcha
    if (!captchaToken) {
        showCaptchaError('Please complete the captcha verification');
        return;
    }

    // Hide previous alerts
    hideAlerts();

    // Show loading state
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'flex';

    try {
        const response = await fetch('/api/request', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                address: address,
                captcha: captchaToken
            })
        });

        const data = await response.json();

        if (data.success) {
            showSuccess(data);
            document.getElementById('faucetForm').reset();
            captchaToken = null;

            // Reset captcha
            if (window.turnstile) {
                turnstile.reset();
            }

            // Reload stats
            await loadFaucetStats();
        } else {
            showError(data.error || 'Request failed. Please try again.');

            // Reset captcha on error
            if (window.turnstile) {
                turnstile.reset();
            }
            captchaToken = null;
        }
    } catch (error) {
        console.error('Request failed:', error);
        showError('Network error. Please check your connection and try again.');

        // Reset captcha on error
        if (window.turnstile) {
            turnstile.reset();
        }
        captchaToken = null;
    } finally {
        submitBtn.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}

// Address validation
function validateAddress() {
    const addressInput = document.getElementById('address');
    const errorElement = document.getElementById('addressError');
    const address = addressInput.value.trim();

    // Check if address is empty
    if (!address) {
        errorElement.textContent = '';
        errorElement.classList.remove('show');
        return false;
    }

    // Check if address matches pattern (xaitest1 followed by 32 base32 chars)
    const addressPattern = /^xaitest1[a-z2-7]{32}$/;
    if (!addressPattern.test(address)) {
        errorElement.textContent = 'Invalid XAI address format. Address must start with "xaitest1" followed by 32 lowercase alphanumeric characters.';
        errorElement.classList.add('show');
        return false;
    }

    // Valid address
    errorElement.classList.remove('show');
    return true;
}

// Captcha callbacks
window.onCaptchaSuccess = function(token) {
    captchaToken = token;
    document.getElementById('submitBtn').disabled = false;
    document.getElementById('captchaError').classList.remove('show');
};

window.onCaptchaExpired = function() {
    captchaToken = null;
    document.getElementById('submitBtn').disabled = true;
};

function showCaptchaError(message) {
    const errorElement = document.getElementById('captchaError');
    errorElement.textContent = message;
    errorElement.classList.add('show');
}

// Alert display functions
function showSuccess(data) {
    const alert = document.getElementById('successAlert');
    const message = document.getElementById('successMessage');
    const txLink = document.getElementById('txLink');

    message.textContent = data.message || 'Successfully sent XAI tokens!';

    if (data.txid && data.txid !== 'N/A') {
        txLink.href = 'https://testnet-explorer.xaiblockchain.com/tx/' + data.txid;
        txLink.style.display = 'inline-flex';
    } else {
        txLink.style.display = 'none';
    }

    alert.style.display = 'flex';

    // Auto-hide after 10 seconds
    setTimeout(() => {
        alert.style.display = 'none';
    }, 10000);
}

function showError(message) {
    const alert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');

    errorMessage.textContent = message;
    alert.style.display = 'flex';

    // Auto-hide after 8 seconds
    setTimeout(() => {
        alert.style.display = 'none';
    }, 8000);
}

function hideAlerts() {
    document.getElementById('successAlert').style.display = 'none';
    document.getElementById('errorAlert').style.display = 'none';
}
