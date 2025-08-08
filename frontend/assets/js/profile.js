// Profile Page JavaScript
const API_BASE = 'http://localhost:5001/api';

// Global variables
let isEditMode = false;
let originalData = {};
let currentUser = null;

// Initialize profile page
document.addEventListener('DOMContentLoaded', function() {
    checkAuthentication();
    loadUserProfile();
    setupEventListeners();
    
    // Handle profile form submission
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }
});

// Check if user is authenticated
function checkAuthentication() {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    
    if (!token || !user) {
        window.location.href = 'login.html';
        return;
    }
    
    try {
        currentUser = JSON.parse(user);
    } catch (error) {
        console.error('Error parsing user data:', error);
        window.location.href = 'login.html';
    }
}

// Load user profile data
async function loadUserProfile() {
    try {
        showLoading(true);
        
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/profile`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            displayUserProfile(result.user);
        } else if (response.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = 'login.html';
        } else {
            throw new Error('Failed to load profile');
        }
    } catch (error) {
        console.error('Error loading profile:', error);
        showNotification('Failed to load profile data', 'error');
    } finally {
        showLoading(false);
    }
}

// Display user profile data
function displayUserProfile(userData) {
    // Store original data for cancel functionality
    originalData = { ...userData };
    
    // Update profile header elements
    updateProfileHeader(userData);
    
    // Update form fields with user data
    updateFormFields(userData);
}

// Update form fields with user data (for the simple profile.html form)
function updateFormFields(userData) {
    // Update profile display elements
    const profileDisplayName = document.getElementById('profileDisplayName');
    const profileDisplayEmail = document.getElementById('profileDisplayEmail');
    const profileAvatar = document.getElementById('profileAvatar');
    const profileAvatarSmall = document.getElementById('profileAvatarSmall');
    const profileName = document.getElementById('profileName');
    
    if (profileDisplayName) {
        profileDisplayName.textContent = userData.name || 'User Name';
    }
    
    if (profileDisplayEmail) {
        profileDisplayEmail.textContent = userData.email || '';
    }
    
    // Update avatar initials
    const initials = userData.name ? userData.name.split(' ').map(n => n[0]).join('').toUpperCase() : 'U';
    if (profileAvatar) {
        profileAvatar.textContent = initials;
    }
    if (profileAvatarSmall) {
        profileAvatarSmall.textContent = initials;
    }
    if (profileName) {
        profileName.textContent = userData.name ? userData.name.split(' ')[0] : 'User';
    }
    
    // Update form input fields
    const fullNameInput = document.getElementById('fullName');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');
    const dateOfBirthInput = document.getElementById('dateOfBirth');
    const genderInput = document.getElementById('gender');
    
    if (fullNameInput) {
        fullNameInput.value = userData.name || '';
    }
    
    if (emailInput) {
        emailInput.value = userData.email || '';
    }
    
    if (phoneInput) {
        phoneInput.value = userData.phone || '';
    }
    
    if (dateOfBirthInput && userData.date_of_birth) {
        // Convert date to input format (YYYY-MM-DD)
        const date = new Date(userData.date_of_birth);
        if (!isNaN(date.getTime())) {
            dateOfBirthInput.value = date.toISOString().split('T')[0];
        }
    }
    
    if (genderInput) {
        genderInput.value = userData.gender || '';
    }
}

// Update navigation elements
function updateNavigation(userData) {
    const navAvatar = document.getElementById('navAvatar');
    const navUserName = document.getElementById('navUserName');
    
    if (navAvatar && userData.name) {
        navAvatar.textContent = userData.name.charAt(0).toUpperCase();
    }
    
    if (navUserName && userData.name) {
        navUserName.textContent = userData.name.split(' ')[0]; // First name only
    }
}

// Update profile header
function updateProfileHeader(userData) {
    const profileAvatar = document.getElementById('profileAvatar');
    const profileName = document.getElementById('profileName');
    const profileEmail = document.getElementById('profileEmail');
    const memberSince = document.getElementById('memberSince');
    const lastLogin = document.getElementById('lastLogin');
    
    if (profileAvatar && userData.name) {
        profileAvatar.textContent = userData.name.charAt(0).toUpperCase();
    }
    
    if (profileName) {
        profileName.textContent = userData.name || 'User';
    }
    
    if (profileEmail) {
        profileEmail.textContent = userData.email || '';
    }
    
    if (memberSince && userData.created_at) {
        const date = new Date(userData.created_at);
        memberSince.textContent = date.toLocaleDateString('en-US', { 
            month: 'short', 
            year: 'numeric' 
        });
    }
    
    if (lastLogin) {
        lastLogin.textContent = 'Today'; // Could be enhanced with actual last login data
    }
}

// Update personal information tab
function updatePersonalInfo(userData) {
    updateField('name', userData.name);
    updateField('email', userData.email);
    updateField('phone', userData.phone || 'Not provided');
    updateField('dob', userData.date_of_birth ? formatDate(userData.date_of_birth) : 'Not provided');
    updateField('gender', userData.gender ? capitalizeFirst(userData.gender) : 'Not specified');
}

// Update health profile tab
function updateHealthProfile(userData) {
    const metadata = userData.metadata || {};
    
    updateField('height', metadata.height ? `${metadata.height} cm` : 'Not provided');
    updateField('weight', metadata.weight ? `${metadata.weight} kg` : 'Not provided');
    updateField('blood-type', metadata.blood_type || 'Not provided');
    updateField('allergies', metadata.allergies || 'None reported');
    updateField('medications', metadata.medications || 'None reported');
    updateField('conditions', metadata.medical_conditions || 'None reported');
}

// Update emergency contact tab
function updateEmergencyContact(userData) {
    const metadata = userData.metadata || {};
    const emergency = metadata.emergency_contact || {};
    
    updateField('emergency-name', emergency.name || 'Not provided');
    updateField('emergency-relation', emergency.relationship ? capitalizeFirst(emergency.relationship) : 'Not specified');
    updateField('emergency-phone', emergency.phone || 'Not provided');
}

// Update privacy settings tab
function updatePrivacySettings(userData) {
    const metadata = userData.metadata || {};
    const preferences = metadata.preferences || {};
    
    const marketingEmails = document.getElementById('marketing-emails');
    const smsNotifications = document.getElementById('sms-notifications');
    const dataSharing = document.getElementById('data-sharing');
    
    if (marketingEmails) {
        marketingEmails.checked = preferences.marketing_emails || false;
    }
    
    if (smsNotifications) {
        smsNotifications.checked = preferences.sms_notifications || false;
    }
    
    if (dataSharing) {
        dataSharing.checked = preferences.data_sharing || false;
    }
}

// Calculate and display BMI
function calculateBMI(userData) {
    const metadata = userData.metadata || {};
    const height = parseFloat(metadata.height);
    const weight = parseFloat(metadata.weight);
    
    const bmiValue = document.getElementById('bmi-value');
    const bmiCategory = document.getElementById('bmi-category');
    
    if (height && weight && height > 0) {
        const heightInMeters = height / 100;
        const bmi = weight / (heightInMeters * heightInMeters);
        const roundedBMI = Math.round(bmi * 10) / 10;
        
        if (bmiValue) {
            bmiValue.textContent = roundedBMI;
        }
        
        if (bmiCategory) {
            let category = '';
            let categoryClass = '';
            
            if (bmi < 18.5) {
                category = 'Underweight';
                categoryClass = 'underweight';
            } else if (bmi < 25) {
                category = 'Normal weight';
                categoryClass = 'normal';
            } else if (bmi < 30) {
                category = 'Overweight';
                categoryClass = 'overweight';
            } else {
                category = 'Obese';
                categoryClass = 'obese';
            }
            
            bmiCategory.textContent = category;
            bmiCategory.className = `bmi-category ${categoryClass}`;
        }
    } else {
        if (bmiValue) {
            bmiValue.textContent = '-';
        }
        if (bmiCategory) {
            bmiCategory.textContent = 'Enter height and weight';
            bmiCategory.className = 'bmi-category';
        }
    }
}

// Update field display and input values
function updateField(fieldName, value) {
    const displayElement = document.getElementById(`display-${fieldName}`);
    const inputElement = document.getElementById(`input-${fieldName}`);
    
    if (displayElement) {
        displayElement.textContent = value || 'Not provided';
    }
    
    if (inputElement) {
        if (fieldName === 'dob' && value && value !== 'Not provided') {
            // Convert display date back to input format
            const date = new Date(originalData.date_of_birth);
            inputElement.value = date.toISOString().split('T')[0];
        } else if (fieldName === 'gender' && originalData.gender) {
            inputElement.value = originalData.gender;
        } else if (fieldName === 'blood-type' && originalData.metadata?.blood_type) {
            inputElement.value = originalData.metadata.blood_type;
        } else if (fieldName === 'emergency-relation' && originalData.metadata?.emergency_contact?.relationship) {
            inputElement.value = originalData.metadata.emergency_contact.relationship;
        } else if (fieldName.includes('emergency-')) {
            const emergencyField = fieldName.replace('emergency-', '');
            const emergencyData = originalData.metadata?.emergency_contact || {};
            inputElement.value = emergencyData[emergencyField] || '';
        } else if (['height', 'weight', 'allergies', 'medications', 'conditions'].includes(fieldName)) {
            const metadataValue = originalData.metadata?.[fieldName === 'conditions' ? 'medical_conditions' : fieldName];
            inputElement.value = metadataValue || '';
        } else {
            inputElement.value = originalData[fieldName] || '';
        }
    }
}

// Toggle edit mode
function toggleEditMode() {
    isEditMode = !isEditMode;
    
    const displayElements = document.querySelectorAll('.field-display');
    const inputElements = document.querySelectorAll('.field-input');
    const editActions = document.getElementById('edit-actions');
    const editBtn = document.querySelector('.edit-profile-btn');
    
    if (isEditMode) {
        // Show inputs, hide displays
        displayElements.forEach(el => el.classList.add('hidden'));
        inputElements.forEach(el => el.classList.remove('hidden'));
        editActions.classList.remove('hidden');
        editBtn.style.display = 'none';
    } else {
        // Show displays, hide inputs
        displayElements.forEach(el => el.classList.remove('hidden'));
        inputElements.forEach(el => el.classList.add('hidden'));
        editActions.classList.add('hidden');
        editBtn.style.display = 'flex';
    }
}

// Cancel edit mode
function cancelEdit() {
    // Restore original values
    displayUserProfile(originalData);
    toggleEditMode();
}

// Save profile changes
async function saveProfile() {
    try {
        showLoading(true);
        
        const updatedData = collectFormData();
        const token = localStorage.getItem('token');
        
        const response = await fetch(`${API_BASE}/profile`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updatedData)
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Update localStorage with new user data
            localStorage.setItem('user', JSON.stringify(result.user));
            
            // Update display with new data
            displayUserProfile(result.user);
            toggleEditMode();
            
            showNotification('Profile updated successfully!', 'success');
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update profile');
        }
    } catch (error) {
        console.error('Error saving profile:', error);
        showNotification(error.message || 'Failed to update profile', 'error');
    } finally {
        showLoading(false);
    }
}

// Collect form data
function collectFormData() {
    return {
        name: document.getElementById('input-name').value.trim(),
        phone: document.getElementById('input-phone').value.trim() || null,
        date_of_birth: document.getElementById('input-dob').value || null,
        gender: document.getElementById('input-gender').value || null,
        metadata: {
            height: parseFloat(document.getElementById('input-height').value) || null,
            weight: parseFloat(document.getElementById('input-weight').value) || null,
            blood_type: document.getElementById('input-blood-type').value || null,
            allergies: document.getElementById('input-allergies').value.trim() || null,
            medications: document.getElementById('input-medications').value.trim() || null,
            medical_conditions: document.getElementById('input-conditions').value.trim() || null,
            emergency_contact: {
                name: document.getElementById('input-emergency-name').value.trim() || null,
                relationship: document.getElementById('input-emergency-relation').value || null,
                phone: document.getElementById('input-emergency-phone').value.trim() || null
            },
            preferences: {
                marketing_emails: document.getElementById('marketing-emails').checked,
                sms_notifications: document.getElementById('sms-notifications').checked,
                data_sharing: document.getElementById('data-sharing').checked
            }
        }
    };
}

// Tab switching functionality
function switchTab(tabName) {
    // Remove active class from all tabs and panels
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
    
    // Add active class to selected tab and panel
    event.target.classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Profile dropdown toggle
function toggleProfileDropdown() {
    const dropdown = document.querySelector('.profile-menu');
    dropdown.classList.toggle('show');
}

// Setup event listeners
function setupEventListeners() {
    // Privacy settings toggles
    const privacyToggles = document.querySelectorAll('#privacy-tab input[type="checkbox"]');
    privacyToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            if (isEditMode) {
                // Auto-save privacy settings
                savePrivacySettings();
            }
        });
    });
    
    // BMI calculation on height/weight change
    const heightInput = document.getElementById('input-height');
    const weightInput = document.getElementById('input-weight');
    
    [heightInput, weightInput].forEach(input => {
        if (input) {
            input.addEventListener('input', function() {
                if (isEditMode) {
                    calculateBMIFromInputs();
                }
            });
        }
    });
    
    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function() {
            this.value = formatPhoneNumber(this.value);
        });
    });
}

// Save privacy settings separately
async function savePrivacySettings() {
    try {
        const preferences = {
            marketing_emails: document.getElementById('marketing-emails').checked,
            sms_notifications: document.getElementById('sms-notifications').checked,
            data_sharing: document.getElementById('data-sharing').checked
        };
        
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/profile/preferences`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ preferences })
        });
        
        if (response.ok) {
            showNotification('Privacy settings updated', 'success');
        }
    } catch (error) {
        console.error('Error saving privacy settings:', error);
    }
}

// Calculate BMI from current input values
function calculateBMIFromInputs() {
    const height = parseFloat(document.getElementById('input-height').value);
    const weight = parseFloat(document.getElementById('input-weight').value);
    
    const bmiValue = document.getElementById('bmi-value');
    const bmiCategory = document.getElementById('bmi-category');
    
    if (height && weight && height > 0) {
        const heightInMeters = height / 100;
        const bmi = weight / (heightInMeters * heightInMeters);
        const roundedBMI = Math.round(bmi * 10) / 10;
        
        if (bmiValue) {
            bmiValue.textContent = roundedBMI;
        }
        
        if (bmiCategory) {
            let category = '';
            let categoryClass = '';
            
            if (bmi < 18.5) {
                category = 'Underweight';
                categoryClass = 'underweight';
            } else if (bmi < 25) {
                category = 'Normal weight';
                categoryClass = 'normal';
            } else if (bmi < 30) {
                category = 'Overweight';
                categoryClass = 'overweight';
            } else {
                category = 'Obese';
                categoryClass = 'obese';
            }
            
            bmiCategory.textContent = category;
            bmiCategory.className = `bmi-category ${categoryClass}`;
        }
    }
}

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1).replace('-', ' ');
}

function formatPhoneNumber(value) {
    const digits = value.replace(/\D/g, '');
    
    if (digits.length >= 6) {
        return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
    } else if (digits.length >= 3) {
        return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
    }
    
    return digits;
}

function showLoading(show) {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        if (show) {
            loadingOverlay.classList.remove('hidden');
        } else {
            loadingOverlay.classList.add('hidden');
        }
    }
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    const notificationMessage = document.getElementById('notificationMessage');
    
    if (notification && notificationMessage) {
        notificationMessage.textContent = message;
        notification.className = `notification ${type}`;
        notification.classList.remove('hidden');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            hideNotification();
        }, 5000);
    }
}

function hideNotification() {
    const notification = document.getElementById('notification');
    if (notification) {
        notification.classList.add('hidden');
    }
}

// Settings and logout functions (for navigation)
function viewSettings() {
    switchTab('privacy');
}

// Initialize Socket.IO connection for real-time notifications
function initializeSocketIO() {
    const token = localStorage.getItem('token');
    if (!token) {
        console.log('No token available for Socket.IO connection');
        return;
    }

    try {
        // Initialize Socket.IO connection with authentication
        const socket = io('http://localhost:5001', {
            auth: {
                token: token
            },
            transports: ['websocket', 'polling'],
            timeout: 10000,
            forceNew: true
        });

        socket.on('connect', function() {
            console.log('✅ Profile page Socket.IO connected successfully');
        });

        socket.on('connection_success', function(data) {
            console.log('✅ Profile connection success:', data.message);
        });

        socket.on('disconnect', function(reason) {
            console.log('❌ Profile Socket.IO disconnected:', reason);
        });

        socket.on('connect_error', function(error) {
            console.error('❌ Profile Socket.IO connection error:', error);
        });

        // Listen for profile-specific notifications
        socket.on('profile_update_notification', function(data) {
            console.log('📋 Profile update notification:', data);
            showNotification(data.message, data.type || 'info');
        });

        // Listen for security alerts
        socket.on('security_alert', function(data) {
            console.log('🔒 Security alert:', data);
            showNotification(data.message, 'warning');
        });

        // Listen for system notifications
        socket.on('system_notification', function(data) {
            console.log('🔔 System notification:', data);
            showNotification(data.message, data.type || 'info');
        });

        // Store socket reference globally
        window.profileSocket = socket;

    } catch (error) {
        console.error('❌ Failed to initialize Profile Socket.IO:', error);
    }
}

// Handle profile form submission (for the simple profile.html form)
async function handleProfileUpdate(e) {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('fullName').value.trim(),
        phone: document.getElementById('phone').value.trim() || null,
        date_of_birth: document.getElementById('dateOfBirth').value || null,
        gender: document.getElementById('gender').value || null
    };

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/profile`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            const updatedUser = await response.json();
            
            // Update stored user data
            localStorage.setItem('user', JSON.stringify(updatedUser.user));
            
            // Update display
            loadUserProfile();
            
            // Show success message
            showMessage('profileSuccess', 'Profile updated successfully!');
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to update profile');
        }
    } catch (error) {
        console.error('Profile update error:', error);
        showMessage('profileError', error.message || 'Error updating profile. Please try again.');
    }
}

// Show message function for the simple profile form
function showMessage(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.style.display = 'block';
        
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

function logout() {
    if (confirm('Are you sure you want to sign out?')) {
        // Disconnect Socket.IO if connected
        if (window.profileSocket) {
            window.profileSocket.disconnect();
        }
        
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    }
}