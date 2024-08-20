// learn_html page CONFIGURATIONS
document.addEventListener('DOMContentLoaded', function() {
    if (document.body.classList.contains('learn-html-page')) {
        const left = document.querySelector(".left"),
              right = document.querySelector(".right"),
              bar = document.querySelector(".bar"),
              run = document.querySelector(".btn-run"),
              editor = document.querySelector(".editor"),
              iframe = document.querySelector(".iframe");

        const drag = (e) => {
            e.preventDefault();
            document.selection ? document.selection.empty() :
            window.getSelection().removeAllRanges();
            left.style.width = (e.pageX - bar.offsetWidth / 3) + "px";
            editor.resize();
        };

        // When user presses the bar, event listener on mousedown anywhere on the bar
        bar.addEventListener("mousedown", () => {
            document.addEventListener("mousemove", drag);
            
            // Make sure to remove the event listener on mouseup anywhere on the document
            document.addEventListener("mouseup", () => {
                document.removeEventListener("mousemove", drag);
            }, { once: true });
        });

        // Run Btn Event Listener
        run.addEventListener("click", () => {
            const html = editor.textContent;
            iframe.src = "data:text/html;charset=utl-8," + encodeURI(html);
        });
    }
});



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

}
