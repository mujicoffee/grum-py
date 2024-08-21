
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

document.addEventListener('DOMContentLoaded', () => {
    const table = document.querySelector('table');
    const cols = table.querySelectorAll('th');

    cols.forEach(col => {
        const resizer = document.createElement('div');
        resizer.classList.add('resizer');
        col.appendChild(resizer);

        let startX, startWidth;

        resizer.addEventListener('mousedown', (e) => {
            startX = e.clientX;
            startWidth = col.offsetWidth;

            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', () => {
                document.removeEventListener('mousemove', handleMouseMove);
            });
        });

        function handleMouseMove(e) {
            const newWidth = startWidth + (e.clientX - startX);
            col.style.width = `${newWidth}px`;
            // Adjust column width for the rest of the table
            table.querySelectorAll(`td:nth-child(${Array.from(col.parentElement.children).indexOf(col) + 1})`).forEach(td => {
                td.style.width = `${newWidth}px`;
            });
        }
    });
});

