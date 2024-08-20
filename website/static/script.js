function updateDateTime() {
    // Define Singapore time zone
    const options = {
        timeZone: 'Asia/Singapore',
        weekday: 'long',
        day: '2-digit',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };

    // Create a new Date object for the current time
    const now = new Date();

    // Format the date and time according to options
    const formatter = new Intl.DateTimeFormat('en-GB', options);
    const formattedDateTime = formatter.format(now);

    // Update the content of the date-time container
    document.getElementById('date-time').textContent = formattedDateTime;
}

// Update date and time every second
setInterval(updateDateTime, 1000);

// Initial call to display date and time immediately
updateDateTime();