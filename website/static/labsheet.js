console.log('labsheet.js is loaded');

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.action-button').forEach(button => {
    button.addEventListener('click', () => {
      const textToCopy = button.getAttribute('data-question-text');
      console.log('Button clicked, text to copy:', textToCopy);
      
      navigator.clipboard.writeText(textToCopy)
        .then(() => {
          showSnackbar('Text copied to clipboard!');
        })
        .catch(err => {
          showSnackbar('Failed to copy text');
          console.error('Failed to copy text: ', err);
        });
    });
  });
});


