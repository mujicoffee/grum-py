document.addEventListener('DOMContentLoaded', (event) => {
    const navbar = document.getElementById('navbartransition');
    const oldContent = document.getElementById('transition-content');
    const startquizContent = document.getElementById('startquizContent');

    // Function to start the transition for navbar and main content
    function startTransition() {
        navbar.classList.add('slide-out');
        oldContent.classList.add('slide-down');
    }

    // Function to remove the elements from the DOM and make the boss-position visible
    function completeTransition() {
        navbar.remove();
        oldContent.remove();
        // Make the boss-position element visible
        startquizContent.style.display = 'block'; // Ensure it is visible
        startquizContent.style.opacity = '1'; // Make it fully opaque
    }

    // Start transition after a short delay to ensure CSS is applied
    setTimeout(startTransition, 100);

    // Set a timeout to match the duration of your CSS transition
    setTimeout(completeTransition, 700); // 500ms matches the transition duration

});


document.addEventListener("DOMContentLoaded", function() {
    // Wait for the animation to complete (10 seconds) and then change the image
    setTimeout(function() {
        // Find the boss image element
        var bossImage = document.querySelector('.boss');
        var knightImage = document.querySelector('.knight');
        var idleSrc = bossImage.getAttribute('data-idle-src');
        // Change the src attribute to bossidle.gif

        knightImage.src='/static/images/knight/idle.gif'
        bossImage.src = idleSrc; 
        bossImage.alt = 'Boss Idle Animation'; // Update alt text if needed

    }, 5200); // 10 seconds in milliseconds
});


// Function to show the question card
function showQuestionCard() {
    document.getElementById('quizcard-container').style.display = 'flex';
}

// Assume the boss animation takes 5 seconds to complete
setTimeout(showQuestionCard, 6000);

// Alternatively, if you have an event listener for the boss animation completion:
// bossAnimationElement.addEventListener('animationend', showQuestionCard);