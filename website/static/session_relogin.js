document.addEventListener('DOMContentLoaded', function() {
    let redirectTimeout;  // Declare the timeout variable for redirection
    let countdownTimer;   // Declare the countdown timer variable

    function getCsrfToken() {
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        return csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : '';
    }

    function checkReauthentication() {
        fetch('/check_reauthenticate', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'expired') {
                sessionStorage.setItem('showReauthenticateModal', 'false'); // Disable modal
                alert(data.message);  // Show session expired message as an alert
                window.location.reload();  // Refresh the page to log out user
            } else if (data.reauthenticate) {
                sessionStorage.setItem('reauthenticate', 'true');
                showReauthenticationModal();
            } else {
                sessionStorage.removeItem('reauthenticate');
            }
        })
        .catch(error => {
            console.error('Error checking session status:', error);
        });
    }

    function showReauthenticationModal() {
        const overlay = document.getElementById('sess-overlay');
        const modal = document.getElementById('reloginModal');
        const emailInput = document.getElementById('reauthEmail');
        if (overlay && modal) {
            overlay.style.display = 'block';
            modal.style.display = 'flex';
            if (emailInput) {
                emailInput.focus();
            }

            startCountdown(); // Start the countdown when the modal is shown
        }
    }

    function hideReauthenticationModal() {
        const overlay = document.getElementById('sess-overlay');
        const modal = document.getElementById('reloginModal');
        const emailInput = document.getElementById('reauthEmail');
        const passwordInput = document.getElementById('reauthPassword');

        if (overlay && modal) {
            overlay.style.display = 'none';
            modal.style.display = 'none';
        }

        // Clear input fields
        if (emailInput && passwordInput) {
            emailInput.value = '';
            passwordInput.value = '';
        }
        clearTimeout(redirectTimeout); // Clear the redirection timeout
        clearInterval(countdownTimer); // Clear the countdown timer
    }

    function startCountdown() {
        let timeRemaining = 120; // 120 seconds countdown
        const timerElement = document.getElementById('timer');

        // Debug statement
        console.log('Starting countdown from', timeRemaining);

        countdownTimer = setInterval(() => {
            timeRemaining--;
            if (timerElement) {
                timerElement.textContent = timeRemaining;
            }

            if (timeRemaining <= 0) {
                clearInterval(countdownTimer);
                alert('Your session has expired, please log in again.');
                window.location.href = '/auth.login'; // Redirect after time is up
            }
        }, 1000); // Update every second
    }

    function handleReauthFormSubmit(event) {
        event.preventDefault();
        const email = document.getElementById('reauthEmail').value.trim().toLowerCase();
        const password = document.getElementById('reauthPassword').value.trim();

        if (!email || !password) {
            alert('Please fill in both email and password.');
            return;
        }

        reauthenticate(email, password);
    }

    function reauthenticate(email, password) {
        const formData = new URLSearchParams();
        formData.append('email', email);
        formData.append('password', password);

        fetch('/reauthenticate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            },
            body: formData.toString()
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                hideReauthenticationModal();
                sessionStorage.removeItem('reauthenticate');
                sessionStorage.removeItem('showReauthenticateModal'); // Clear modal state
                alert(data.message);
            } else {
                alert(data.message || 'Reauthentication failed. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error during reauthentication:', error);
        });
    }

    function handleLogout() {
        fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert(data.message);
                window.location.href = '/auth.login';  // Redirect to the login page
            } else {
                alert('Logout failed: ' + (data.message || 'Please try again.'));
            }
        })
        .catch(error => {
            console.error('Error during logout:', error);
            alert('An error occurred during logout. Please try again later.');
        });
    }

    // Ensure autocomplete is turned off for email and password fields
    const emailInput = document.getElementById('reauthEmail');
    if (emailInput) {
        emailInput.setAttribute('autocomplete', 'off');
    }

    const reauthForm = document.getElementById('reauthForm');
    if (reauthForm) {
        reauthForm.addEventListener('submit', handleReauthFormSubmit);
    }

    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }

    // Check reauthentication status immediately on page load
    checkReauthentication();

    // Automatically show the modal after 60 seconds
    setTimeout(() => {
        sessionStorage.setItem('showReauthenticateModal', 'true'); // Save the state
        showReauthenticationModal();
    }, 600000); // 60 seconds

    // Check reauthentication status every 30 seconds
    setInterval(checkReauthentication, 30000);

});
