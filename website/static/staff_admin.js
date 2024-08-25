
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

