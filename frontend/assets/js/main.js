// Mobile menu toggle
function toggleMenu() {
    const navMenu = document.querySelector('.nav-menu');
    const menuToggle = document.querySelector('.menu-toggle');
    
    navMenu.classList.toggle('active');
    menuToggle.classList.toggle('active');
}

// Profile dropdown toggle
function toggleProfileDropdown() {
    const dropdown = document.querySelector('.profile-menu');
    dropdown.classList.toggle('show');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.querySelector('.profile-menu');
    const profileBtn = document.querySelector('.profile-btn');
    
    if (dropdown && !dropdown.contains(event.target) && !profileBtn.contains(event.target)) {
        dropdown.classList.remove('show');
    }
});

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Fade in animation on scroll
function animateOnScroll() {
    const elements = document.querySelectorAll('.fade-in-up');
    
    elements.forEach(element => {
        const elementTop = element.getBoundingClientRect().top;
        const elementVisible = 150;
        
        if (elementTop < window.innerHeight - elementVisible) {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }
    });
}

// Initialize animations
window.addEventListener('scroll', animateOnScroll);
window.addEventListener('load', animateOnScroll);

// Dynamic greeting based on time
function updateGreeting() {
    const greetingElement = document.getElementById('greeting');
    if (greetingElement) {
        const hour = new Date().getHours();
        let greeting;
        
        if (hour < 12) {
            greeting = "Good morning";
        } else if (hour < 18) {
            greeting = "Good afternoon";
        } else {
            greeting = "Good evening";
        }
        
        greetingElement.textContent = `${greeting}! How can we help?`;
    }
}

// Initialize dynamic content
document.addEventListener('DOMContentLoaded', function() {
    updateGreeting();
});

// Loading state for buttons
function setButtonLoading(button, loading = true) {
    if (loading) {
        button.disabled = true;
        button.textContent = 'Loading...';
    } else {
        button.disabled = false;
        button.textContent = button.getAttribute('data-original-text') || 'Submit';
    }
}

// Show/hide error messages
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

// Show/hide success messages
function showSuccess(elementId, message) {
    const successElement = document.getElementById(elementId);
    if (successElement) {
        successElement.textContent = message;
        successElement.classList.remove('hidden');
    }
}

function hideSuccess(elementId) {
    const successElement = document.getElementById(elementId);
    if (successElement) {
        successElement.classList.add('hidden');
    }
}



// Form validation helpers
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function validatePhone(phone) {
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    return phoneRegex.test(phone.replace(/\s/g, ''));
}

// Password strength checker
function checkPasswordStrength(password) {
    let score = 0;
    let feedback = [];
    
    // Length check
    if (password.length >= 8) score += 1;
    else feedback.push('At least 8 characters');
    
    // Uppercase check
    if (/[A-Z]/.test(password)) score += 1;
    else feedback.push('One uppercase letter');
    
    // Lowercase check
    if (/[a-z]/.test(password)) score += 1;
    else feedback.push('One lowercase letter');
    
    // Number check
    if (/\d/.test(password)) score += 1;
    else feedback.push('One number');
    
    // Special character check
    if (/[^A-Za-z0-9]/.test(password)) score += 1;
    else feedback.push('One special character');
    
    let strength = 'weak';
    if (score >= 4) strength = 'strong';
    else if (score >= 3) strength = 'good';
    else if (score >= 2) strength = 'fair';
    
    return { score, strength, feedback };
}

// Debounce function for input validation
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Local storage helpers
function saveToStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        console.error('Error saving to localStorage:', error);
    }
}

function getFromStorage(key) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : null;
    } catch (error) {
        console.error('Error reading from localStorage:', error);
        return null;
    }
}

function removeFromStorage(key) {
    try {
        localStorage.removeItem(key);
    } catch (error) {
        console.error('Error removing from localStorage:', error);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Add any page-specific initialization here
    console.log('Kare Healthcare - Page loaded successfully');
});

// Authentication state management
function checkAuthState() {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null;
    const isLoggedIn = token && userData;
    
    const authButtons = document.querySelector('.auth-buttons');
    const profileDropdown = document.getElementById('profileDropdown');
    const vitalPageButton = document.getElementById('vitalPageButton');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const defaultHero = document.getElementById('defaultHero');
    
    if (isLoggedIn) {
        // Show logged-in state
        if (authButtons) authButtons.style.display = 'none';
        if (profileDropdown) profileDropdown.classList.remove('hidden');
        if (vitalPageButton) vitalPageButton.classList.remove('hidden');
        if (welcomeMessage) {
            welcomeMessage.classList.remove('hidden');
            updateWelcomeMessage(userData);
        }
        if (defaultHero) defaultHero.classList.add('hidden');
    } else {
        // Show logged-out state
        if (authButtons) authButtons.style.display = 'flex';
        if (profileDropdown) profileDropdown.classList.add('hidden');
        if (vitalPageButton) vitalPageButton.classList.add('hidden');
        if (welcomeMessage) welcomeMessage.classList.add('hidden');
        if (defaultHero) defaultHero.classList.remove('hidden');
    }
}

function updateWelcomeMessage(userData) {
    const greetingElement = document.getElementById('greeting');
    if (greetingElement && userData) {
        const hour = new Date().getHours();
        let timeGreeting;
        
        if (hour < 12) {
            timeGreeting = "Good morning";
        } else if (hour < 18) {
            timeGreeting = "Good afternoon";
        } else {
            timeGreeting = "Good evening";
        }
        
        // Use the name from the user data, fallback to email if name not available
        const userName = userData.name || userData.email.split('@')[0];
        greetingElement.textContent = `${timeGreeting}, ${userName}!`;
    }
}

// Profile functions
function viewProfile() {
    const userData = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null;
    if (userData) {
        window.location.href = 'profile.html';
    } else {
        window.location.href = 'login.html';
    }
}

// Update profile dropdown with user info
function updateProfileDropdown() {
    const userData = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null;
    if (userData) {
        // Update profile avatar and name
        const profileAvatarSmall = document.getElementById('profileAvatarSmall');
        const profileName = document.getElementById('profileName');
        
        if (profileAvatarSmall && userData.name) {
            profileAvatarSmall.textContent = userData.name.charAt(0).toUpperCase();
        }
        
        if (profileName && userData.name) {
            profileName.textContent = userData.name.split(' ')[0]; // First name only
        }
    }
}

function viewSettings() {
    alert('Settings page would be implemented here');
}

function logout() {
    if (confirm('Are you sure you want to sign out?')) {
        // Clear user data using the correct keys
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        
        // Update UI
        checkAuthState();
        
        // Show success message
        alert('You have been signed out successfully');
        
        // Optionally redirect to home
        window.location.reload();
    }
}

// Initialize authentication state on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuthState();
    updateProfileDropdown();
    
    // Check auth state periodically (in case user logs in from another tab)
    setInterval(() => {
        checkAuthState();
        updateProfileDropdown();
    }, 5000);
});
