// Vital Signs Page JavaScript

let vitalChart, ecgChart, historyChart;
let currentTimeRange = '24h';
let isConnected = false;
let websocket = null;
let isDeviceLinked = false;
let userDevices = [];
let currentDeviceId = null;
const API_BASE = 'http://localhost:5001/api';

// Initialize the vital signs page
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Vital signs page initializing...');
    
    checkAuthentication();
    
    // Test element availability
    const deviceNotLinked = document.getElementById('deviceNotLinked');
    const deviceLinked = document.getElementById('deviceLinked');
    console.log('🔍 Element check - deviceNotLinked:', deviceNotLinked ? 'Found' : 'NOT FOUND');
    console.log('🔍 Element check - deviceLinked:', deviceLinked ? 'Found' : 'NOT FOUND');
    
    // Always start by showing device not linked view (default state)
    showDeviceNotLinkedView();
    
    // Initialize charts (but keep them hidden until device is linked)
    initializeCharts();
    
    // Check if user has a device linked
    console.log('🔄 About to call checkDeviceStatus...');
    checkDeviceStatus();
    
    updateLastUpdated();
    
    // Initialize Socket.IO connection
    initializeSocketIO();
    
    // Update data every 30 seconds if device is linked
    setInterval(() => {
        if (isDeviceLinked) {
            loadDeviceData();
        }
    }, 30000);
    
    setInterval(updateLastUpdated, 60000);
});

// Check authentication
function checkAuthentication() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

// Check device linking status
async function checkDeviceStatus() {
    console.log('🎯 checkDeviceStatus function called');
    try {
        const token = localStorage.getItem('token');
        console.log('🔍 Checking device status with token:', token ? 'Present' : 'Missing');
        
        if (!token) {
            console.log('❌ No token found - user needs to login');
            return;
        }
        
        const response = await fetch(`${API_BASE}/device/info`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const result = await response.json();
        console.log('📱 Device status API response:', result);
        console.log('📊 Response status:', response.status);
        
        if (response.ok && result.has_device && result.device_info) {
            // User has a device linked - show the dashboard
            isDeviceLinked = true;
            currentDeviceId = result.device_info.device_id;
            console.log('✅ Device found, switching to dashboard view');
            console.log('🔗 Device ID:', result.device_info.device_id);
            showDeviceLinkedView(result.device_info);
            loadDeviceData();
        } else {
            // User has no device linked - keep showing the linking interface
            isDeviceLinked = false;
            console.log('❌ No device linked - showing device linking interface');
            console.log('🔍 has_device:', result.has_device);
            console.log('🔍 device_info:', result.device_info);
            // showDeviceNotLinkedView() is already called in DOMContentLoaded
        }
    } catch (error) {
        console.error('❌ Error checking device status:', error);
        // On error, assume no device is linked
        isDeviceLinked = false;
        console.log('Error occurred - showing device linking interface');
    }
}

// Show device not linked view
function showDeviceNotLinkedView() {
    console.log('Showing device not linked view');
    
    // Show device linking interface
    document.getElementById('deviceNotLinked').style.display = 'block';
    document.getElementById('deviceLinked').style.display = 'none';
    
    // Hide all dashboard sections when no device is linked
    const chartsSection = document.querySelector('.charts-section');
    const historySection = document.querySelector('.history-section');
    const alertsSection = document.querySelector('.alerts-section');
    const actionsSection = document.querySelector('.actions-section');
    
    if (chartsSection) chartsSection.style.display = 'none';
    if (historySection) historySection.style.display = 'none';
    if (alertsSection) alertsSection.style.display = 'none';
    if (actionsSection) actionsSection.style.display = 'none';
    
    // Clear any existing device data
    clearVitalCards();
    
    // Clear the device input field
    const deviceInput = document.getElementById('deviceIdInput');
    if (deviceInput) {
        deviceInput.value = '';
        deviceInput.focus(); // Focus on the input for better UX
    }
    
    // Reset global state
    isDeviceLinked = false;
    currentDeviceId = null;
}

// Show device linked view
function showDeviceLinkedView(deviceInfo) {
    console.log('🎯 showDeviceLinkedView called with:', deviceInfo);
    
    // Check if elements exist
    const deviceNotLinked = document.getElementById('deviceNotLinked');
    const deviceLinked = document.getElementById('deviceLinked');
    
    console.log('📋 deviceNotLinked element:', deviceNotLinked ? 'Found' : 'NOT FOUND');
    console.log('📋 deviceLinked element:', deviceLinked ? 'Found' : 'NOT FOUND');
    
    // Hide device linking interface and show dashboard
    if (deviceNotLinked) {
        deviceNotLinked.style.display = 'none';
        console.log('✅ Hidden device linking interface');
    }
    if (deviceLinked) {
        deviceLinked.style.display = 'block';
        console.log('✅ Shown device dashboard');
    }
    
    // Show all dashboard sections when device is linked
    const chartsSection = document.querySelector('.charts-section');
    const historySection = document.querySelector('.history-section');
    const alertsSection = document.querySelector('.alerts-section');
    const actionsSection = document.querySelector('.actions-section');
    
    if (chartsSection) chartsSection.style.display = 'block';
    if (historySection) historySection.style.display = 'block';
    if (alertsSection) alertsSection.style.display = 'block';
    if (actionsSection) actionsSection.style.display = 'block';
    
    // Update device info display
    if (deviceInfo) {
        const deviceName = document.getElementById('deviceName');
        const linkedDeviceId = document.getElementById('linkedDeviceId');
        
        if (deviceName) {
            deviceName.textContent = deviceInfo.device_type || 'ESP32 Device';
        }
        if (linkedDeviceId) {
            linkedDeviceId.textContent = deviceInfo.device_id;
        }
    }
    
    // Update global state
    isDeviceLinked = true;
    if (deviceInfo && deviceInfo.device_id) {
        currentDeviceId = deviceInfo.device_id;
    }
}

// Link device function
async function linkDevice() {
    const deviceId = document.getElementById('deviceIdInput').value.trim();
    const linkBtn = document.getElementById('linkDeviceBtn');
    const btnText = linkBtn.querySelector('.btn-text');
    const spinner = linkBtn.querySelector('.loading-spinner');
    
    if (!deviceId) {
        showNotification('Please enter a device ID', 'error');
        return;
    }
    
    // Show loading state
    linkBtn.disabled = true;
    btnText.style.display = 'none';
    spinner.classList.remove('hidden');
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/device/link`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ device_id: deviceId })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Device linked successfully! Loading your dashboard...', 'success');
            
            // Update global state
            isDeviceLinked = true;
            currentDeviceId = deviceId;
            
            // Create device info object from the response
            const deviceInfo = {
                device_id: deviceId,
                device_type: 'ESP32',
                linked_at: new Date().toISOString()
            };
            
            console.log('✅ Device linked successfully:', deviceId);
            console.log('🔄 Switching to dashboard view...');
            
            // Show the dashboard
            showDeviceLinkedView(deviceInfo);
            
            // Load initial data
            loadDeviceData();
            
        } else {
            showNotification(result.error || 'Failed to link device. Please check your device ID and try again.', 'error');
            console.error('❌ Device linking failed:', result.error);
        }
    } catch (error) {
        console.error('Error linking device:', error);
        showNotification('Network error. Please try again.', 'error');
    } finally {
        // Reset button state
        linkBtn.disabled = false;
        btnText.style.display = 'inline';
        spinner.classList.add('hidden');
    }
}

// Unlink device function
async function unlinkDevice() {
    if (!confirm('Are you sure you want to unlink your device? This will stop real-time monitoring.')) {
        return;
    }
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/device/unlink`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Device unlinked successfully. You can link a new device below.', 'success');
            
            // Reset state and show device linking interface
            isDeviceLinked = false;
            currentDeviceId = null;
            showDeviceNotLinkedView();
            
            console.log('Device unlinked successfully');
        } else {
            showNotification(result.error || 'Failed to unlink device', 'error');
            console.error('Device unlinking failed:', result.error);
        }
    } catch (error) {
        console.error('Error unlinking device:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

// Load device data
async function loadDeviceData() {
    if (!isDeviceLinked) return;
    
    try {
        const token = localStorage.getItem('token');
        const hours = currentTimeRange === '1h' ? 1 : 
                     currentTimeRange === '6h' ? 6 : 
                     currentTimeRange === '24h' ? 24 : 
                     currentTimeRange === '7d' ? 168 : 24;
        
        const response = await fetch(`${API_BASE}/device/data?hours=${hours}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const result = await response.json();
        
        if (response.ok && result.has_device) {
            updateChartsWithDeviceData(result.data);
            loadLatestVitalSigns();
        } else {
            console.error('Failed to load device data:', result.message || result.error);
        }
    } catch (error) {
        console.error('Error loading device data:', error);
    }
}

// Load latest vital signs
async function loadLatestVitalSigns() {
    if (!isDeviceLinked) return;
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/device/data/latest`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const result = await response.json();
        
        if (response.ok && result.has_device) {
            if (result.has_data) {
                updateVitalCards(result.latest_data);
            } else {
                // Show waiting state when device is linked but no data yet
                updateVitalCards({});
            }
        }
    } catch (error) {
        console.error('Error loading latest vital signs:', error);
    }
}

// Clear vital cards when no device is linked
function clearVitalCards() {
    document.getElementById('heartRate').textContent = '--';
    document.getElementById('heartRateStatus').textContent = 'Device not linked';
    document.getElementById('heartRateStatus').className = 'vital-status waiting';
    
    document.getElementById('spo2').textContent = '--';
    document.getElementById('spo2Status').textContent = 'Device not linked';
    document.getElementById('spo2Status').className = 'vital-status waiting';
    
    document.getElementById('temperature').textContent = '--';
    document.getElementById('temperatureStatus').textContent = 'Device not linked';
    document.getElementById('temperatureStatus').className = 'vital-status waiting';
    
    document.getElementById('deviceStatus').textContent = 'Not Connected';
    document.getElementById('deviceStatusText').textContent = 'No device linked';
    document.getElementById('deviceStatusText').className = 'vital-status waiting';
    
    document.getElementById('lastUpdated').textContent = '--';
}

// Update vital cards with device data
function updateVitalCards(data) {
    // Heart Rate
    if (data.heart_rate_bpm !== undefined && data.heart_rate_bpm !== null) {
        document.getElementById('heartRate').textContent = data.heart_rate_bpm;
        document.getElementById('heartRateStatus').textContent = getHeartRateStatus(data.heart_rate_bpm);
        document.getElementById('heartRateStatus').className = 'vital-status ' + getStatusClass(data.heart_rate_bpm, 60, 100);
    } else {
        document.getElementById('heartRate').textContent = '--';
        document.getElementById('heartRateStatus').textContent = 'Waiting for data...';
        document.getElementById('heartRateStatus').className = 'vital-status waiting';
    }
    
    // SpO2
    if (data.spo2_percent !== undefined && data.spo2_percent !== null) {
        document.getElementById('spo2').textContent = data.spo2_percent;
        document.getElementById('spo2Status').textContent = getSpO2Status(data.spo2_percent);
        document.getElementById('spo2Status').className = 'vital-status ' + getStatusClass(data.spo2_percent, 95, 100);
    } else {
        document.getElementById('spo2').textContent = '--';
        document.getElementById('spo2Status').textContent = 'Waiting for data...';
        document.getElementById('spo2Status').className = 'vital-status waiting';
    }
    
    // Temperature (use Fahrenheit from ESP8266)
    if (data.temperature_f !== undefined && data.temperature_f !== null) {
        document.getElementById('temperature').textContent = data.temperature_f.toFixed(1) + '°F';
        document.getElementById('temperatureStatus').textContent = getTemperatureStatusF(data.temperature_f);
        document.getElementById('temperatureStatus').className = 'vital-status ' + getStatusClassF(data.temperature_f, 97.0, 99.5);
    } else {
        document.getElementById('temperature').textContent = '--';
        document.getElementById('temperatureStatus').textContent = 'Waiting for data...';
        document.getElementById('temperatureStatus').className = 'vital-status waiting';
    }
    
    // Device Status
    document.getElementById('deviceStatus').textContent = 'Connected';
    document.getElementById('deviceStatusText').textContent = 'Receiving data';
    document.getElementById('deviceStatusText').className = 'vital-status normal';
    
    // Update last updated time
    if (data.timestamp) {
        const lastUpdated = new Date(data.timestamp);
        document.getElementById('lastUpdated').textContent = lastUpdated.toLocaleTimeString();
    }
}

// Update charts with device data
function updateChartsWithDeviceData(data) {
    if (!data || !data.timestamps || data.timestamps.length === 0) {
        return;
    }
    
    // Update real-time chart
    if (vitalChart) {
        vitalChart.data.labels = data.timestamps.map(ts => new Date(ts));
        vitalChart.data.datasets[0].data = data.heart_rate;
        vitalChart.data.datasets[1].data = data.spo2;
        vitalChart.update();
    }
    
    // Update history chart
    if (historyChart) {
        historyChart.data.labels = data.timestamps.map(ts => new Date(ts));
        historyChart.data.datasets[0].data = data.heart_rate;
        historyChart.data.datasets[1].data = data.spo2;
        historyChart.data.datasets[2].data = data.temperature;
        historyChart.update();
    }
    
    // Update ECG chart with latest ECG data
    if (ecgChart && data.ecg_data && data.ecg_data.length > 0) {
        const latestEcg = data.ecg_data[data.ecg_data.length - 1];
        if (latestEcg && latestEcg.length > 0) {
            ecgChart.data.labels = latestEcg.map((_, index) => index);
            ecgChart.data.datasets[0].data = latestEcg;
            ecgChart.update();
        }
    }
}

// Refresh data function
async function refreshData() {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshIcon = refreshBtn.querySelector('.refresh-icon');
    
    // Add spinning animation
    refreshIcon.style.animation = 'spin 1s linear infinite';
    refreshBtn.disabled = true;
    
    try {
        await loadDeviceData();
        showNotification('Data refreshed successfully', 'success');
    } catch (error) {
        showNotification('Failed to refresh data', 'error');
    } finally {
        // Remove spinning animation
        setTimeout(() => {
            refreshIcon.style.animation = '';
            refreshBtn.disabled = false;
        }, 1000);
    }
}

// Update last updated time
function updateLastUpdated() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const lastUpdatedElement = document.getElementById('lastUpdated');
    if (lastUpdatedElement) {
        lastUpdatedElement.textContent = timeString;
    }
}

// Status helper functions
function getHeartRateStatus(heartRate) {
    if (heartRate < 60) return 'Low';
    if (heartRate > 100) return 'High';
    return 'Normal';
}

function getSpO2Status(spo2) {
    if (spo2 < 95) return 'Low';
    return 'Normal';
}

function getTemperatureStatus(temp) {
    if (temp < 36.1) return 'Low';
    if (temp > 37.2) return 'High';
    return 'Normal';
}

// Fahrenheit temperature status functions
function getTemperatureStatusF(tempF) {
    if (tempF < 97.0) return 'Low';
    if (tempF > 99.5) return 'High';
    return 'Normal';
}

function getStatusClassF(value, minNormal, maxNormal) {
    if (value < minNormal || value > maxNormal) return 'warning';
    return 'normal';
}

function getStatusClass(value, minNormal, maxNormal) {
    if (value < minNormal || value > maxNormal) return 'warning';
    return 'normal';
}

function getQualityClass(quality) {
    if (quality === 'Good') return 'normal';
    if (quality === 'Fair') return 'warning';
    return 'error';
}

// Time range selection
function selectTimeRange(range) {
    currentTimeRange = range;
    
    // Update active button
    document.querySelectorAll('.time-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Reload data with new time range
    if (isDeviceLinked) {
        loadDeviceData();
    }
}

// Placeholder functions for quick actions
function exportData() {
    showNotification('Export feature coming soon!', 'info');
}

function shareWithDoctor() {
    showNotification('Share feature coming soon!', 'info');
}

function setReminder() {
    showNotification('Reminder feature coming soon!', 'info');
}

function viewTrends() {
    showNotification('Trends feature coming soon!', 'info');
}

// Show notification function
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    
    // Set background color based on type
    switch (type) {
        case 'success':
            notification.style.backgroundColor = '#10b981';
            break;
        case 'error':
            notification.style.backgroundColor = '#ef4444';
            break;
        case 'warning':
            notification.style.backgroundColor = '#f59e0b';
            break;
        default:
            notification.style.backgroundColor = '#3b82f6';
    }
    
    // Add to page
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

// Initialize Chart.js charts
function initializeCharts() {
    // Real-time vital signs chart
    const vitalCtx = document.getElementById('vitalChart').getContext('2d');
    vitalChart = new Chart(vitalCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Heart Rate (bpm)',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'SpO2 (%)',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm'
                        }
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    min: 40,
                    max: 200,
                    title: {
                        display: true,
                        text: 'Heart Rate (bpm)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    min: 80,
                    max: 100,
                    title: {
                        display: true,
                        text: 'SpO2 (%)'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });

    // ECG waveform chart
    const ecgCtx = document.getElementById('ecgChart').getContext('2d');
    ecgChart = new Chart(ecgCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'ECG',
                data: [],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.1,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: false
                },
                y: {
                    min: -2,
                    max: 2,
                    title: {
                        display: true,
                        text: 'Amplitude (mV)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            },
            animation: false
        }
    });

    // Historical data chart
    const historyCtx = document.getElementById('historyChart').getContext('2d');
    historyChart = new Chart(historyCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Heart Rate',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'SpO2',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Temperature',
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'hour',
                        displayFormats: {
                            hour: 'MMM dd HH:mm'
                        }
                    }
                },
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Values'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}

// Initialize Socket.IO connection
function initializeSocketIO() {
    const token = localStorage.getItem('token');
    if (!token) {
        console.log('No token available for Socket.IO connection');
        updateConnectionStatus('error');
        return;
    }

    console.log('Initializing Socket.IO connection...');
    updateConnectionStatus('connecting');

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
            console.log('✅ Socket.IO connected successfully');
            console.log('Socket ID:', socket.id);
            isConnected = true;
            updateConnectionStatus('connected');
        });

        socket.on('connection_success', function(data) {
            console.log('✅ Connection success:', data.message);
            showNotification('Connected to real-time updates', 'success');
        });

        socket.on('disconnect', function(reason) {
            console.log('❌ Socket.IO disconnected:', reason);
            isConnected = false;
            updateConnectionStatus('disconnected');
        });

        socket.on('connect_error', function(error) {
            console.error('❌ Socket.IO connection error:', error);
            console.error('Error details:', error.message);
            updateConnectionStatus('error');
            
            // Show user-friendly error message
            showNotification('Failed to connect to real-time updates', 'error');
        });

        // Listen for real-time vital signs updates
        socket.on('vital_signs_update', function(data) {
            console.log('📊 Received vital signs update:', data);
            handleRealtimeData(data);
        });

        // Listen for device data updates
        socket.on('device_data_update', function(data) {
            console.log('📱 Received device data update:', data);
            if (data.device_id === currentDeviceId || !currentDeviceId) {
                updateVitalCards(data);
                updateRealtimeChart(data);
                
                // Update ECG if available
                if (data.ecg_data && data.ecg_data.length > 0) {
                    updateECGChart({ values: data.ecg_data, timestamps: data.ecg_data.map((_, i) => i) });
                }
            }
        });

        // Debug events
        socket.onAny((event, ...args) => {
            console.log('🔍 Socket.IO event received:', event, args);
        });

        // Store socket reference globally
        window.socket = socket;

        console.log('Socket.IO initialization completed');

    } catch (error) {
        console.error('❌ Failed to initialize Socket.IO:', error);
        updateConnectionStatus('error');
        showNotification('Failed to initialize real-time connection', 'error');
    }
}

// Handle real-time data from WebSocket
function handleRealtimeData(data) {
    if (data.type === 'vital_signs') {
        updateVitalCards(data.data);
        updateRealtimeChart(data.data);
    } else if (data.type === 'ecg_data') {
        updateECGChart(data.data);
    } else if (data.type === 'alert') {
        addAlert(data.data);
    }
}

// Update vital sign cards
function updateVitalCards(data) {
    // Heart Rate
    if (data.heart_rate !== undefined) {
        document.getElementById('heartRate').textContent = data.heart_rate;
        document.getElementById('heartRateStatus').textContent = getHeartRateStatus(data.heart_rate);
        document.getElementById('heartRateStatus').className = 'vital-status ' + getStatusClass(data.heart_rate, 60, 100);
    }
    
    // SpO2
    if (data.spo2 !== undefined) {
        document.getElementById('spo2').textContent = data.spo2;
        document.getElementById('spo2Status').textContent = getSpO2Status(data.spo2);
        document.getElementById('spo2Status').className = 'vital-status ' + getStatusClass(data.spo2, 95, 100);
    }
    
    // Temperature (use Fahrenheit from ESP8266)
    if (data.temperature_f !== undefined && data.temperature_f !== null) {
        document.getElementById('temperature').textContent = data.temperature_f.toFixed(1) + '°F';
        document.getElementById('temperatureStatus').textContent = getTemperatureStatusF(data.temperature_f);
        document.getElementById('temperatureStatus').className = 'vital-status ' + getStatusClassF(data.temperature_f, 97.0, 99.5);
    } else if (data.temperature !== undefined) {
        // Fallback for old temperature format
        document.getElementById('temperature').textContent = data.temperature.toFixed(1) + '°F';
        document.getElementById('temperatureStatus').textContent = getTemperatureStatusF(data.temperature);
        document.getElementById('temperatureStatus').className = 'vital-status ' + getStatusClassF(data.temperature, 97.0, 99.5);
    }
    
    // Data Quality
    if (data.data_quality !== undefined) {
        document.getElementById('dataQuality').textContent = data.data_quality;
        document.getElementById('dataQualityStatus').textContent = data.data_quality;
        document.getElementById('dataQualityStatus').className = 'vital-status ' + getQualityClass(data.data_quality);
    }
}

// Update real-time chart
function updateRealtimeChart(data) {
    const now = new Date();
    
    // Add new data point
    vitalChart.data.labels.push(now);
    vitalChart.data.datasets[0].data.push(data.heart_rate);
    vitalChart.data.datasets[1].data.push(data.spo2);
    
    // Keep only last 20 data points
    if (vitalChart.data.labels.length > 20) {
        vitalChart.data.labels.shift();
        vitalChart.data.datasets[0].data.shift();
        vitalChart.data.datasets[1].data.shift();
    }
    
    vitalChart.update('none');
}

// Update ECG chart
function updateECGChart(ecgData) {
    ecgChart.data.labels = ecgData.timestamps;
    ecgChart.data.datasets[0].data = ecgData.values;
    ecgChart.update('none');
}

// Load initial data
async function loadInitialData() {
    try {
        const response = await fetch('/api/vital-signs/current');
        if (response.ok) {
            const data = await response.json();
            updateVitalCards(data);
        }
    } catch (error) {
        console.error('Failed to load initial data:', error);
        // Use mock data for demonstration
        updateVitalCards({
            heart_rate: 72,
            spo2: 98,
            temperature: 36.5,
            data_quality: 'Good'
        });
    }
    
    // Load historical data
    loadHistoricalData(currentTimeRange);
}

// Load historical data
async function loadHistoricalData(timeRange) {
    try {
        const response = await fetch(`/api/vital-signs/history?range=${timeRange}`);
        if (response.ok) {
            const data = await response.json();
            updateHistoryChart(data);
        }
    } catch (error) {
        console.error('Failed to load historical data:', error);
        // Generate mock historical data
        generateMockHistoricalData(timeRange);
    }
}

// Update history chart
function updateHistoryChart(data) {
    historyChart.data.labels = data.timestamps;
    historyChart.data.datasets[0].data = data.heart_rate;
    historyChart.data.datasets[1].data = data.spo2;
    historyChart.data.datasets[2].data = data.temperature;
    historyChart.update();
}

// Generate mock historical data for demonstration
function generateMockHistoricalData(timeRange) {
    const now = new Date();
    const data = {
        timestamps: [],
        heart_rate: [],
        spo2: [],
        temperature: []
    };
    
    let points, interval;
    switch (timeRange) {
        case '1h':
            points = 60;
            interval = 60000; // 1 minute
            break;
        case '6h':
            points = 72;
            interval = 300000; // 5 minutes
            break;
        case '24h':
            points = 96;
            interval = 900000; // 15 minutes
            break;
        case '7d':
            points = 168;
            interval = 3600000; // 1 hour
            break;
        default:
            points = 60;
            interval = 60000;
    }
    
    for (let i = points; i >= 0; i--) {
        const timestamp = new Date(now.getTime() - (i * interval));
        data.timestamps.push(timestamp);
        data.heart_rate.push(70 + Math.random() * 20);
        data.spo2.push(96 + Math.random() * 3);
        data.temperature.push(36.2 + Math.random() * 1.0);
    }
    
    updateHistoryChart(data);
}

// Update vital signs (called periodically)
function updateVitalSigns() {
    if (!isConnected) {
        // Generate mock data when not connected
        const mockData = {
            heart_rate: 70 + Math.floor(Math.random() * 20),
            spo2: 96 + Math.floor(Math.random() * 4),
            temperature: 36.2 + Math.random() * 1.0,
            data_quality: ['Good', 'Fair', 'Poor'][Math.floor(Math.random() * 3)]
        };
        updateVitalCards(mockData);
        updateRealtimeChart(mockData);
    }
}

// Utility functions
function getHeartRateStatus(hr) {
    if (hr < 60) return 'Low';
    if (hr > 100) return 'High';
    return 'Normal';
}

function getSpO2Status(spo2) {
    if (spo2 < 95) return 'Low';
    return 'Normal';
}

// Removed duplicate getTemperatureStatus function - using getTemperatureStatusF instead

function getStatusClass(value, min, max) {
    if (value < min || value > max) return 'warning';
    return 'normal';
}

function getQualityClass(quality) {
    switch (quality.toLowerCase()) {
        case 'good': return 'normal';
        case 'fair': return 'warning';
        case 'poor': return 'critical';
        default: return 'normal';
    }
}

function updateConnectionStatus(status) {
    let statusElement = document.querySelector('.connection-status');
    if (!statusElement) {
        statusElement = document.createElement('div');
        statusElement.className = 'connection-status';
        document.body.appendChild(statusElement);
    }
    
    statusElement.className = `connection-status ${status}`;
    switch (status) {
        case 'connected':
            statusElement.textContent = '🟢 Connected';
            break;
        case 'disconnected':
            statusElement.textContent = '🔴 Disconnected';
            break;
        case 'connecting':
            statusElement.textContent = '🟡 Connecting...';
            break;
        case 'error':
            statusElement.textContent = '❌ Connection Error';
            break;
    }
}

function updateLastUpdated() {
    const now = new Date();
    document.getElementById('lastUpdated').textContent = now.toLocaleTimeString();
}

// Time range selection
function selectTimeRange(range) {
    currentTimeRange = range;
    
    // Update button states
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Load new data
    loadHistoricalData(range);
}

// Add alert to alerts section
function addAlert(alertData) {
    const alertsContainer = document.getElementById('alertsContainer');
    const alertElement = document.createElement('div');
    alertElement.className = `alert-item ${alertData.type}`;
    
    alertElement.innerHTML = `
        <div class="alert-icon">${getAlertIcon(alertData.type)}</div>
        <div class="alert-content">
            <h4>${alertData.title}</h4>
            <p>${alertData.message}</p>
            <span class="alert-time">${new Date().toLocaleTimeString()}</span>
        </div>
    `;
    
    alertsContainer.insertBefore(alertElement, alertsContainer.firstChild);
    
    // Remove old alerts (keep only last 5)
    while (alertsContainer.children.length > 5) {
        alertsContainer.removeChild(alertsContainer.lastChild);
    }
}

function getAlertIcon(type) {
    switch (type) {
        case 'warning': return '⚠️';
        case 'critical': return '🚨';
        case 'info': return 'ℹ️';
        default: return 'ℹ️';
    }
}

// Export functions for global access
window.linkDevice = linkDevice;
window.unlinkDevice = unlinkDevice;
window.refreshData = refreshData;
window.selectTimeRange = selectTimeRange;
