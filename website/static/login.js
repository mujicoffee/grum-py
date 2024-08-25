let passwordVisibility = document.getElementById("eye");
let password = document.getElementById("password");

passwordVisibility.onclick = function() {
    if (password.type === "password") {
        password.type = "text";
        passwordVisibility.src = "/static/images/extras/openedeye.gif"; // Update with the path to your open eye image
    } else {
        password.type = "password";
        passwordVisibility.src = "/static/images/extras/closedeye.gif"; // Update with the path to your closed eye image
    }
};



//loading animation

document.addEventListener('DOMContentLoaded', function() {
    var form = document.getElementById('loginForm');
    var overlay = document.getElementById('overlay');
    var loading = document.getElementById('loading');

    form.addEventListener('submit', function(event) {
        overlay.style.display = 'flex'; // show the overlay
        loading.style.display = 'block'; // show loading indicator

    
    });
});
