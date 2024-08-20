//login page password visibility
let passwordVisibility = document.getElementById("eye")
let password = document.getElementById("password")

passwordVisibility.onclick = function(){

if(password.type == "password"){
     password.type ="text";
}
else{
  password.type="password"; 
}

}



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
