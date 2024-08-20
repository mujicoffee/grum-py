//snackbar

document.addEventListener('DOMContentLoaded', function() {
    var snackbar = document.getElementById("snackbar");
 
    if (snackbar.textContent.trim() !== '') {
      
        snackbar.className = "show";
        setTimeout(function() {
            snackbar.className = snackbar.className.replace("show", "");
 
        }, 5500);
    }
});

function showSnackbar(message) {
    var snackbar = document.getElementById("snackbar");
    snackbar.textContent = message; // Set the message text
    snackbar.classList.add("show"); // Add the 'show' class to make it visible
    
    // Hide the snackbar after 6 seconds
    setTimeout(function() {
      snackbar.classList.remove("show"); // Remove the 'show' class to hide it
    }, 5500);
  }
  

 