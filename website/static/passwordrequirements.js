// Password requirements color 
document.addEventListener('DOMContentLoaded', function() {
    var newPasswordField = document.getElementById('newPassword');
    var passwordRequirements = document.getElementById('passwordRequirements');
    
    newPasswordField.addEventListener('input', function() {
        var password = newPasswordField.value;
        
        var minLength = document.getElementById('minLength');
        var lowercase = document.getElementById('lowercase');
        var uppercase = document.getElementById('uppercase');
        var number = document.getElementById('number');
        var specialChar = document.getElementById('specialChar');
        
        // Check minimum length
        if (password.length >= 12) {
            minLength.classList.add('satisfied');
        } else {
            minLength.classList.remove('satisfied');
        }
        
        // Check lowercase letter
        if (/[a-z]/.test(password)) {
            lowercase.classList.add('satisfied');
        } else {
            lowercase.classList.remove('satisfied');
        }
        
        // Check uppercase letter
        if (/[A-Z]/.test(password)) {
            uppercase.classList.add('satisfied');
        } else {
            uppercase.classList.remove('satisfied');
        }
        
        // Check number
        if (/[0-9]/.test(password)) {
            number.classList.add('satisfied');
        } else {
            number.classList.remove('satisfied');
        }
        
        // Check special character
        if (/[!@#$%^&*()]/.test(password)) {
            specialChar.classList.add('satisfied');
        } else {
            specialChar.classList.remove('satisfied');
        }
    });
});