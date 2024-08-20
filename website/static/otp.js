document.addEventListener("DOMContentLoaded", function() {
    var otpInputs = document.querySelectorAll('.otpNumber');
    var countdownElement = document.getElementById('countdown');
    var resendLink = document.getElementById('resend-link');
    var resendText = document.getElementById('resend-text');
    var resendContainer = document.querySelector('.resend-otp');
    var countdown = 30;

    // Initialize countdown timer to 30 seconds
    function updateCountdown() {
        countdownElement.textContent = countdown + 's';
        countdown--;
        if (countdown < 0) {
            clearInterval(timer);
            resendText.style.display = 'none'; // Hide the resend text
            resendLink.style.display = 'inline'; // Show the resend link
        }
    }
    var timer = setInterval(updateCountdown, 1000);

    otpInputs.forEach((input, index) => {
        // Allow alphanumeric characters
        input.addEventListener('input', (event) => {
            // Restrict to 1 character input
            if (input.value.length > 1) {
                input.value = input.value.slice(0, 1);
            }
            if (input.value.length === 1 && index < otpInputs.length - 1) {
                otpInputs[index + 1].focus();
            }
        });

        input.addEventListener('keydown', (event) => {
            if (!((event.key >= '0' && event.key <= '9') || 
                  (event.key >= 'a' && event.key <= 'z') ||
                  (event.key >= 'A' && event.key <= 'Z') ||
                  event.key === 'Backspace' || 
                  event.key === 'ArrowLeft' || 
                  event.key === 'ArrowRight' || 
                  event.key === 'Tab')) {
                event.preventDefault();
            }
            if (event.key === "Backspace" && index > 0 && input.value.length === 0) {
                otpInputs[index - 1].focus();
            }
        });
    });

    // Automatically focus the first input field on page load
    if (otpInputs.length > 0) {
        otpInputs[0].focus();
    }

    document.getElementById('verifyButton').addEventListener('click', function() {
        let otpValue = '';
        otpInputs.forEach(input => otpValue += input.value);

        if (otpValue.length === otpInputs.length) {
            const form = document.getElementById('otpForm');
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'otp';
            hiddenInput.value = otpValue;
            form.appendChild(hiddenInput);
            form.submit();
        } else {
            // Display snackbar instead of alert
            var snackbar = document.getElementById("snackbarOtp");
            snackbar.textContent = 'Please enter all OTP characters.';
            snackbar.className = "show";
            setTimeout(function() {
                snackbar.className = snackbar.className.replace("show", "");
            }, 6000); // Adjust timing as necessary
        }
    });
});

document.getElementById('resend-link').addEventListener('click', function() {
    document.getElementById('resendForm').submit();
    return false;
});

