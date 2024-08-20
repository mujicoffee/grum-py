

//makes the border
function chooseImage(img) {
    // Update the hidden input value with the selected image
    document.querySelector('input[name="profilePic"]').value = img;

    // Highlight the selected image (optional)
    document.querySelectorAll('.profile-pic').forEach(label => {
        label.classList.remove('selected');
    });
    event.currentTarget.classList.add('selected');
}