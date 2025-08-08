// Auto-hide alert popup after 3 seconds
document.addEventListener('DOMContentLoaded', () => {
  const popup = document.querySelector('.popup-alert');
  if (popup) {
    setTimeout(() => {
      popup.style.opacity = '0';
      popup.style.transition = 'opacity 0.5s ease';
      setTimeout(() => popup.remove(), 500);
    }, 3000);
  }

  // Confirm before slot booking
  const bookForm = document.querySelector('form[action="/dashboard"]');
  if (bookForm) {
    bookForm.addEventListener('submit', (e) => {
      const confirmed = confirm("Are you sure you want to book this slot?");
      if (!confirmed) e.preventDefault();
    });
  }

  // Toggle password visibility
  const togglePassBtn = document.getElementById('togglePassword');
  const passwordInput = document.getElementById('password');
  if (togglePassBtn && passwordInput) {
    togglePassBtn.addEventListener('click', () => {
      const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordInput.setAttribute('type', type);
      togglePassBtn.textContent = type === 'text' ? '🙈 Hide' : '👁 Show';
    });
  }
});

