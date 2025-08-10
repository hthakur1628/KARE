
// Healthcare Signup Form JavaScript
const API_BASE = 'http://localhost:5001/api';

// Initialize form on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeForm();
    setupValidation();
    setupPasswordStrengthChecker();
});

function initializeForm() {
    // Set max date for date of birth (must be at least 13 years old)
    const today = new Date();
    const maxDate = new Date(today.getFullYear() - 13, today.getMonth(), today.getDate());
    const dateInput = document.getElementById('dateOfBirth');
    if (dateInput) {
        dateInput.max = maxDate.toISOString().split('T')[0];
    }

    // Check if user is already logged in
    if (localStorage.getItem('token')) {
        window.location.href = 'index.html';
    }
}

// Enhanced loading state function matching forgot password pattern
function setLoading(buttonSelector, loading, loadingText = 'Processing...') {
    const button = document.querySelector(buttonSelector);
    if (!button) return;
    
    const originalText = button.getAttribute('data-original-text') || button.textContent.trim();
    
    if (!button.getAttribute('data-original-text')) {
        button.setAttribute('data-original-text', originalText);
    }
    
    if (loading) {
        button.disabled = true;
        button.innerHTML = `<span class="loading"></span>${loadingText}`;
        button.classList.add('loading-state');
    } else {
        button.disabled = false;
        button.innerHTML = originalText;
        button.classList.remove('loading-state');
    }
}

// Add success/error visual feedback
function setButtonState(buttonSelector, state, duration = 2000) {
    const button = document.querySelector(buttonSelector);
    if (!button) return;
    
    button.classList.remove('success', 'error');
    
    if (state === 'success' || state === 'error') {
        button.classList.add(state);
        setTimeout(() => {
            button.classList.remove(state);
        }, duration);
    }
}

// Main form submission handler with enhanced feedback
async function handleSignup(event) {
    event.preventDefault();
    
    if (!validateSignupForm()) {
        setButtonState('.auth-btn', 'error');
        return;
    }

    setLoading('.auth-btn', true, 'Creating Account...');

    try {
        const formData = collectFormData();
        
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            setButtonState('.auth-btn', 'success');
            
            // Store authentication data
            localStorage.setItem('token', result.token);
            localStorage.setItem('user', JSON.stringify(result.user));
            
            // Show success message
            showSuccessMessage('Account created successfully! Redirecting to your dashboard...');
            
            // Redirect after short delay
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
        } else {
            setButtonState('.auth-btn', 'error');
            showErrorMessage(result.error || 'Registration failed. Please try again.');
        }
    } catch (error) {
        console.error('Registration error:', error);
        setButtonState('.auth-btn', 'error');
        showErrorMessage('Network error. Please check your connection and try again.');
    } finally {
        setLoading('.auth-btn', false);
    }
}

// Collect all form data
function collectFormData() {
    const formData = {
        // Combine first and last name
        name: `${document.getElementById('firstName').value.trim()} ${document.getElementById('lastName').value.trim()}`,
        email: document.getElementById('email').value.trim().toLowerCase(),
        password: document.getElementById('password').value,
        phone: document.getElementById('phone').value.trim() || null,
        date_of_birth: document.getElementById('dateOfBirth').value || null,
        gender: document.getElementById('gender').value || null,
        
        // Additional health information (stored as metadata for now)
        metadata: {
            height: document.getElementById('height').value || null,
            weight: document.getElementById('weight').value || null,
            blood_type: document.getElementById('bloodType').value || null,
            allergies: document.getElementById('allergies').value.trim() || null,
            medications: document.getElementById('medications').value.trim() || null,
            medical_conditions: document.getElementById('medicalConditions').value.trim() || null,
            emergency_contact: {
                name: document.getElementById('emergencyContactName').value.trim() || null,
                relationship: document.getElementById('emergencyContactRelation').value || null,
                phone: document.getElementById('emergencyContactPhone').value.trim() || null
            },
            preferences: {
                marketing_emails: document.getElementById('marketingEmails').checked,
                sms_notifications: document.getElementById('smsNotifications').checked
            }
        }
    };

    return formData;
}

// Comprehensive form validation
function validateSignupForm() {
    let isValid = true;
    
    // Clear previous errors
    clearAllErrors();
    
    // Personal Information Validation
    isValid = validatePersonalInfo() && isValid;
    
    // Health Information Validation
    isValid = validateHealthInfo() && isValid;
    
    // Emergency Contact Validation
    isValid = validateEmergencyContact() && isValid;
    
    // Password Validation
    isValid = validatePasswords() && isValid;
    
    // Consent Validation
    isValid = validateConsent() && isValid;
    
    return isValid;
}

function validatePersonalInfo() {
    let isValid = true;
    
    // First Name
    const firstName = document.getElementById('firstName').value.trim();
    if (!firstName) {
        showFieldError('firstNameError', 'First name is required');
        isValid = false;
    } else if (firstName.length < 2) {
        showFieldError('firstNameError', 'First name must be at least 2 characters');
        isValid = false;
    } else if (!/^[a-zA-Z\s'-]+$/.test(firstName)) {
        showFieldError('firstNameError', 'First name contains invalid characters');
        isValid = false;
    }
    
    // Last Name
    const lastName = document.getElementById('lastName').value.trim();
    if (!lastName) {
        showFieldError('lastNameError', 'Last name is required');
        isValid = false;
    } else if (lastName.length < 2) {
        showFieldError('lastNameError', 'Last name must be at least 2 characters');
        isValid = false;
    } else if (!/^[a-zA-Z\s'-]+$/.test(lastName)) {
        showFieldError('lastNameError', 'Last name contains invalid characters');
        isValid = false;
    }
    
    // Email
    const email = document.getElementById('email').value.trim();
    if (!email) {
        showFieldError('emailError', 'Email address is required');
        isValid = false;
    } else if (!validateEmail(email)) {
        showFieldError('emailError', 'Please enter a valid email address');
        isValid = false;
    }
    
    // Phone (optional but validate if provided)
    const phone = document.getElementById('phone').value.trim();
    if (phone && !validatePhone(phone)) {
        showFieldError('phoneError', 'Please enter a valid phone number');
        isValid = false;
    }
    
    return isValid;
}

function validateHealthInfo() {
    let isValid = true;
    
    // Date of Birth
    const dateOfBirth = document.getElementById('dateOfBirth').value;
    if (!dateOfBirth) {
        showFieldError('dateOfBirthError', 'Date of birth is required');
        isValid = false;
    } else {
        const birthDate = new Date(dateOfBirth);
        const today = new Date();
        const age = today.getFullYear() - birthDate.getFullYear();
        
        if (age < 13) {
            showFieldError('dateOfBirthError', 'You must be at least 13 years old to create an account');
            isValid = false;
        } else if (age > 120) {
            showFieldError('dateOfBirthError', 'Please enter a valid date of birth');
            isValid = false;
        }
    }
    
    // Height validation (optional)
    const height = document.getElementById('height').value;
    if (height && (height < 50 || height > 300)) {
        showFieldError('heightError', 'Please enter a valid height between 50-300 cm');
        isValid = false;
    }
    
    // Weight validation (optional)
    const weight = document.getElementById('weight').value;
    if (weight && (weight < 10 || weight > 500)) {
        showFieldError('weightError', 'Please enter a valid weight between 10-500 kg');
        isValid = false;
    }
    
    return isValid;
}

function validateEmergencyContact() {
    let isValid = true;
    
    const emergencyName = document.getElementById('emergencyContactName').value.trim();
    const emergencyRelation = document.getElementById('emergencyContactRelation').value;
    const emergencyPhone = document.getElementById('emergencyContactPhone').value.trim();
    
    // If any emergency contact field is filled, validate all
    if (emergencyName || emergencyRelation || emergencyPhone) {
        if (!emergencyName) {
            showFieldError('emergencyContactNameError', 'Emergency contact name is required');
            isValid = false;
        }
        
        if (!emergencyRelation) {
            showFieldError('emergencyContactRelationError', 'Please select relationship');
            isValid = false;
        }
        
        if (!emergencyPhone) {
            showFieldError('emergencyContactPhoneError', 'Emergency contact phone is required');
            isValid = false;
        } else if (!validatePhone(emergencyPhone)) {
            showFieldError('emergencyContactPhoneError', 'Please enter a valid phone number');
            isValid = false;
        }
    }
    
    return isValid;
}

function validatePasswords() {
    let isValid = true;
    
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // Password validation
    if (!password) {
        showFieldError('passwordError', 'Password is required');
        isValid = false;
    } else {
        const strength = checkPasswordStrength(password);
        if (strength.score < 4) {
            showFieldError('passwordError', 'Password must meet all security requirements');
            isValid = false;
        }
    }
    
    // Confirm password validation
    if (!confirmPassword) {
        showFieldError('confirmPasswordError', 'Please confirm your password');
        isValid = false;
    } else if (password !== confirmPassword) {
        showFieldError('confirmPasswordError', 'Passwords do not match');
        isValid = false;
    }
    
    return isValid;
}

function validateConsent() {
    let isValid = true;
    
    // Terms of Service
    if (!document.getElementById('agreeTerms').checked) {
        showFieldError('termsError', 'You must agree to the Terms of Service and Privacy Policy');
        isValid = false;
    }
    
    // HIPAA Consent
    if (!document.getElementById('agreeHIPAA').checked) {
        showFieldError('hipaaError', 'HIPAA consent is required for healthcare services');
        isValid = false;
    }
    
    // Data Processing Consent
    if (!document.getElementById('agreeDataProcessing').checked) {
        showFieldError('dataProcessingError', 'Data processing consent is required');
        isValid = false;
    }
    
    return isValid;
}

// Setup real-time validation
function setupValidation() {
    // First Name
    setupFieldValidation('firstName', (value) => {
        if (value.length > 0 && value.length < 2) {
            return 'First name must be at least 2 characters';
        }
        if (value.length > 0 && !/^[a-zA-Z\s'-]+$/.test(value)) {
            return 'First name contains invalid characters';
        }
        return null;
    });
    
    // Last Name
    setupFieldValidation('lastName', (value) => {
        if (value.length > 0 && value.length < 2) {
            return 'Last name must be at least 2 characters';
        }
        if (value.length > 0 && !/^[a-zA-Z\s'-]+$/.test(value)) {
            return 'Last name contains invalid characters';
        }
        return null;
    });
    
    // Email
    setupFieldValidation('email', (value) => {
        if (value.length > 0 && !validateEmail(value)) {
            return 'Please enter a valid email address';
        }
        return null;
    });
    
    // Phone
    setupFieldValidation('phone', (value) => {
        if (value.length > 0 && !validatePhone(value)) {
            return 'Please enter a valid phone number';
        }
        return null;
    });
    
    // Date of Birth
    setupFieldValidation('dateOfBirth', (value) => {
        if (value) {
            const birthDate = new Date(value);
            const today = new Date();
            const age = today.getFullYear() - birthDate.getFullYear();
            
            if (age < 13) {
                return 'You must be at least 13 years old';
            }
            if (age > 120) {
                return 'Please enter a valid date of birth';
            }
        }
        return null;
    });
    
    // Height
    setupFieldValidation('height', (value) => {
        if (value && (value < 50 || value > 300)) {
            return 'Height must be between 50-300 cm';
        }
        return null;
    });
    
    // Weight
    setupFieldValidation('weight', (value) => {
        if (value && (value < 10 || value > 500)) {
            return 'Weight must be between 10-500 kg';
        }
        return null;
    });
    
    // Phone formatting
    const phoneInput = document.getElementById('phone');
    const emergencyPhoneInput = document.getElementById('emergencyContactPhone');
    
    [phoneInput, emergencyPhoneInput].forEach(input => {
        if (input) {
            input.addEventListener('input', function() {
                this.value = formatPhoneNumber(this.value);
            });
        }
    });
}

function setupFieldValidation(fieldId, validator) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    field.addEventListener('blur', function() {
        const value = this.value.trim();
        const errorId = fieldId + 'Error';
        
        hideFieldError(errorId);
        
        const error = validator(value);
        if (error) {
            showFieldError(errorId, error);
            this.classList.add('error');
        } else if (value) {
            this.classList.remove('error');
            this.classList.add('success');
        }
    });
    
    field.addEventListener('input', function() {
        this.classList.remove('error', 'success');
    });
}

// Password strength checker
function setupPasswordStrengthChecker() {
    const passwordInput = document.getElementById('password');
    if (!passwordInput) return;
    
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        const strength = checkPasswordStrength(password);
        
        // Update requirement indicators
        updateRequirement('req-length', password.length >= 8);
        updateRequirement('req-uppercase', /[A-Z]/.test(password));
        updateRequirement('req-lowercase', /[a-z]/.test(password));
        updateRequirement('req-number', /\d/.test(password));
        updateRequirement('req-special', /[^A-Za-z0-9]/.test(password));
    });
}

function updateRequirement(reqId, isValid) {
    const element = document.getElementById(reqId);
    if (element) {
        if (isValid) {
            element.classList.add('valid');
        } else {
            element.classList.remove('valid');
        }
    }
}

// Utility functions
function formatPhoneNumber(value) {
    // Remove all non-digits
    const digits = value.replace(/\D/g, '');
    
    // Format as (XXX) XXX-XXXX
    if (digits.length >= 6) {
        return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
    } else if (digits.length >= 3) {
        return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
    }
    
    return digits;
}

function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function validatePhone(phone) {
    // Remove formatting and check if it's a valid US phone number
    const digits = phone.replace(/\D/g, '');
    return digits.length === 10 || digits.length === 11;
}

function checkPasswordStrength(password) {
    let score = 0;
    
    if (password.length >= 8) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[a-z]/.test(password)) score += 1;
    if (/\d/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;
    
    return { score };
}

// Error handling functions
function showFieldError(errorId, message) {
    const errorElement = document.getElementById(errorId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }
}

function hideFieldError(errorId) {
    const errorElement = document.getElementById(errorId);
    if (errorElement) {
        errorElement.classList.remove('show');
    }
}

function clearAllErrors() {
    document.querySelectorAll('.error-message').forEach(error => {
        error.classList.remove('show');
    });
    
    document.querySelectorAll('.form-group input, .form-group select, .form-group textarea').forEach(field => {
        field.classList.remove('error', 'success');
    });
}

function showSuccessMessage(message) {
    // Create or update success message
    let successDiv = document.querySelector('.success-notification');
    if (!successDiv) {
        successDiv = document.createElement('div');
        successDiv.className = 'success-notification';
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--success-green);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            font-weight: 500;
        `;
        document.body.appendChild(successDiv);
    }
    
    successDiv.textContent = message;
    successDiv.style.display = 'block';
}

function showErrorMessage(message) {
    // Create or update error message
    let errorDiv = document.querySelector('.error-notification');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification';
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--error-red);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            font-weight: 500;
            max-width: 400px;
        `;
        document.body.appendChild(errorDiv);
    }
    
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}
