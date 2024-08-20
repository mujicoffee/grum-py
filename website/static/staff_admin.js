
function updateTime() {
    var currentTimeElement = document.getElementById('date-time');

    function formatDate(date) {
        const options = {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            hour: 'numeric',
            minute: 'numeric',
            second: 'numeric',
            hour12: true
        };
        // Format the date with the specified options
        let formattedDate = date.toLocaleString('en-US', options);
    
        // Replace the default date-time formatting with desired format
        formattedDate = formattedDate.replace(' at', ',');
        formattedDate = formattedDate.replace(/, (.+)$/, ' $1');
        return formattedDate;
    }
    

    // Initial display
    currentTimeElement.innerText = formatDate(new Date());

    // Update time every second
    setInterval(function() {
        currentTimeElement.innerText = formatDate(new Date());
    }, 1000);
}

window.onload = function() {
    updateTime();
    };

document.addEventListener('DOMContentLoaded', function() {
    var overlay = document.getElementById('overlay');
    var loading = document.getElementById('loading');

    // Select all forms on the page
    var forms = document.querySelectorAll('form');

    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            overlay.style.display = 'flex'; // show the overlay
            loading.style.display = 'block'; // show loading indicator

            // Optionally, you can prevent the form from submitting immediately
            // to ensure the overlay shows up before form submission
            // event.preventDefault();
        });
    });
});

