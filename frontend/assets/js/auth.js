

// Handle login form submission
function handleLogin(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const email = formData.get('email');
    const password = formData.get('password');
    
    // Clear previous errors
    hideError('emailError');
    hideError('passwordError');
    
    // Validate inputs
    let isValid = true;
    
    if (!email) {
        showError('emailError', 'Email is required');
        isValid = false;
    }
    
    if (!password) {
        showError('passwordError', 'Password is required');
        isValid = false;
    }
    
    if (!isValid) return;
    
    // Simulate login success
    alert('Login successful! Redirecting...');
    // In a real app, this would authenticate with the server
    // window.location.href = 'dashboard.html';
}

// Handle signup form submission
function handleSignup(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const name = formData.get('name');
    const email = formData.get('email');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    
    // Clear previous errors
    hideError('nameError');
    hideError('emailError');
    hideError('passwordError');
    hideError('confirmPasswordError');
    
    // Validate inputs
    let isValid = true;
    
    if (!name) {
        showError('nameError', 'Name is required');
        isValid = false;
    }
    
    if (!email) {
        showError('emailError', 'Email is required');
        isValid = false;
    }
    
    if (!password) {
        showError('passwordError', 'Password is required');
        isValid = false;
    }
    
    if (!confirmPassword) {
        showError('confirmPasswordError', 'Please confirm your password');
        isValid = false;
    } else if (password !== confirmPassword) {
        showError('confirmPasswordError', 'Passwords do not match');
        isValid = false;
    }
    
    if (!isValid) return;
    
    // Simulate signup success
    alert('Account created successfully! Please check your email for verification.');
    // In a real app, this would create the account on the server
    // window.location.href = 'login.html';
}

// Utility functions for error handling
function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }
}

function hideError(elementId) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.classList.remove('show');
    }
}
