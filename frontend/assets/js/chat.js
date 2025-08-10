// Check authentication
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

if (!token) {
    window.location.href = 'login.html';
}

// Global form submission preventer for chat page
document.addEventListener('DOMContentLoaded', () => {
  // Prevent all form submissions on this page
  document.addEventListener('submit', (e) => {
    console.log('Global form submission prevented');
    e.preventDefault();
    e.stopPropagation();
    return false;
  });
});

// Socket functionality with Gemini integration
const socket = io("http://localhost:5001", {
    transports: ['polling', 'websocket'],
    upgrade: true,
    rememberUpgrade: false,
    timeout: 20000,
    forceNew: true,
    auth: {
        token: token
    }
});

// DOM elements - will be initialized after DOM loads
let messageInput, sendBtn, chatMessages, fileInput, attachmentPreview, previewImage, fileName;

// Global variables for attachment and session
let currentAttachment = null;
let sessionId = generateSessionId();

// Generate unique session ID
function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Socket connection events
socket.on('connect', () => {
  console.log('✅ Connected to Kare Healthcare Assistant');
  
  // Join user room for personalized chat
  socket.emit('join_room', {
    user_email: user.email,
    session_id: sessionId
  });
  
  // Get conversation history
  socket.emit('get_conversation_history', {
    user_email: user.email,
    session_id: sessionId
  });
});

// Listen for messages from the server
socket.on('message', (data) => {
  hideTypingIndicator();
  
  if (data.role === 'assistant') {
    // Format and display AI response
    const formattedResponse = formatResponse(data.content);
    addMessage(formattedResponse, "bot", true);
  } else if (data.role === 'user') {
    // This is an echo of our own message, we can ignore it
    // since we already added it to the UI when sending
  }
  
  messageInput.disabled = false;
  sendBtn.disabled = false;
  messageInput.focus();
});

// Listen for conversation history
socket.on('conversation_history', (data) => {
  console.log('📜 Received conversation history');
  
  // Clear current messages except welcome message
  const welcomeMessage = chatMessages.querySelector('.message.bot');
  chatMessages.innerHTML = '';
  if (welcomeMessage) {
    chatMessages.appendChild(welcomeMessage);
  }
  
  // Add historical messages
  data.history.forEach(msg => {
    if (msg.role === 'user') {
      addMessage(msg.content, 'user');
    } else if (msg.role === 'assistant') {
      const formattedResponse = formatResponse(msg.content);
      addMessage(formattedResponse, 'bot', true);
    }
  });
});

// Listen for conversation cleared event
socket.on('conversation_cleared', (data) => {
  console.log("✅ Conversation cleared:", data.msg);
  
  // Reset the chat to welcome message
  chatMessages.innerHTML = `
    <div class="message bot">
      <p>Hello! I'm Kare, your AI healthcare assistant. I'm here to help answer your health questions and provide general medical guidance. How can I assist you today?</p>
      <div class="welcome-note">
        <small>💡 Please note: I provide general health information and should not replace professional medical advice.</small>
      </div>
    </div>
  `;
});

// Listen for status messages
socket.on('status', (data) => {
  console.log('ℹ️ Status:', data.msg);
});

// Listen for errors
socket.on('error', (data) => {
  console.error("❌ Socket error:", data.msg);
  hideTypingIndicator();
  
  // Show error message to user
  addMessage(`Error: ${data.msg}`, "bot");
  messageInput.disabled = false;
  sendBtn.disabled = false;
  messageInput.focus();
});

// Handle connection errors
socket.on("connect_error", (error) => {
  console.error("Connection failed:", error);
  hideTypingIndicator();
  
  if (error.message === 'Authentication error') {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = 'login.html';
  } else {
    // Show generic error message for connection errors
    addMessage("Could not reach server, try again later", "bot");
    messageInput.disabled = false;
    sendBtn.disabled = false;
    if (messageInput) messageInput.focus();
  }
});

// Handle disconnection
socket.on("disconnect", (reason) => {
  console.error("Socket disconnected:", reason);
  hideTypingIndicator();
  
  // Show error message for unexpected disconnections
  if (reason !== 'io client disconnect') {
    addMessage("Could not reach server, try again later", "bot");
    messageInput.disabled = false;
    sendBtn.disabled = false;
    if (messageInput) messageInput.focus();
  }
});

// Handle reconnection attempts
socket.on("reconnect_attempt", (attemptNumber) => {
  console.log(`Reconnection attempt ${attemptNumber}`);
  addMessage("Reconnecting to server...", "bot");
});

// Handle successful reconnection
socket.on("reconnect", (attemptNumber) => {
  console.log(`Reconnected after ${attemptNumber} attempts`);
  addMessage("Connection restored", "bot");
});

// Handle failed reconnection
socket.on("reconnect_failed", () => {
  console.error("Failed to reconnect");
  addMessage("Could not reach server, try again later", "bot");
});

// Format API response
function formatResponse(rawText) {
  // Enhanced Markdown processing
  let formatted = rawText
    // First handle bold formatting (before paragraph processing)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    // Handle italic formatting
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    // Convert #### headers to h4
    .replace(/####\s*(.*?)$/gm, "<h4>$1</h4>")
    // Convert ### headers to h3
    .replace(/###\s*(.*?)$/gm, "<h3>$1</h3>")
    // Convert ## headers to h2
    .replace(/##\s*(.*?)$/gm, "<h2>$1</h2>")
    // Convert # headers to h1
    .replace(/#\s*(.*?)$/gm, "<h1>$1</h1>")
    // Convert double newlines to paragraph breaks
    .replace(/\n\n+/g, "</p><p>")
    // Convert single newlines to line breaks
    .replace(/\n(?!\n)/g, "<br>")
    // Convert bullet points to list items
    .replace(/\* (.*?)(<br>|$)/g, "<li>$1</li>")
    // Wrap consecutive list items in UL
    .replace(/(<li>.*?<\/li>(<br>)?)+/g, (match) => {
      return `<ul>${match.replace(/<br>/g, "")}</ul>`;
    })
    // Wrap content in paragraphs (but not headers)
    .replace(/^(?!<h[1-6]>|<ul>|<\/ul>)(.+)$/gm, "<p>$1</p>")
    // Remove empty paragraphs
    .replace(/<p><\/p>/g, "")
    // Clean up list formatting
    .replace(/<p><ul>/g, "<ul>")
    .replace(/<\/ul><\/p>/g, "</ul>")
    .replace(/<p><li>/g, "<li>")
    .replace(/<\/li><\/p>/g, "</li>")
    // Clean up header formatting
    .replace(/<p><h([1-6])>/g, "<h$1>")
    .replace(/<\/h([1-6])><\/p>/g, "</h$1>");

  return formatted;
}

// --- Chat Functionality ---
document.addEventListener("DOMContentLoaded", () => {
  // Initialize DOM elements
  messageInput = document.getElementById("messageInput");
  sendBtn = document.getElementById("sendBtn");
  chatMessages = document.getElementById("chatMessages");
  fileInput = document.getElementById("fileInput");
  attachmentPreview = document.getElementById("attachmentPreview");
  previewImage = document.getElementById("previewImage");
  fileName = document.getElementById("fileName");

  if (!messageInput || !sendBtn || !chatMessages) {
    console.error("Required DOM elements missing!");
    return;
  }

  console.log("Chat functionality initialized"); // Debug log

  // Handle form submission
  const chatForm = document.getElementById('chatForm');
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      console.log("Form submit event triggered"); // Debug log
      e.preventDefault(); // Prevent form submission and page refresh
      e.stopPropagation(); // Stop event bubbling
      sendMessage();
      return false; // Extra prevention
    });
  }

  // Enter key to send message
  messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      console.log("Enter key pressed"); // Debug log
      e.preventDefault();
      e.stopPropagation();
      sendMessage();
      return false;
    }
  });

  // Send button click (backup - form submission should handle this)
  sendBtn.addEventListener("click", (e) => {
    console.log("Send button clicked"); // Debug log
    e.preventDefault(); // Prevent any default button behavior
    e.stopPropagation(); // Stop event bubbling
    sendMessage();
    return false;
  });

  // Auto-resize input
  messageInput.addEventListener("input", autoResizeInput);
});

function autoResizeInput() {
  messageInput.style.height = "auto";
  messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + "px";
}

function sendMessage() {
  const message = messageInput.value.trim();
  if ((message === "" && !currentAttachment) || messageInput.disabled) return;

  // Prepare message data for Gemini integration
  const messageData = {
    message: message,
    user_email: user.email,
    session_id: sessionId,
    attachment: currentAttachment
  };

  // Send message to server
  socket.emit("send_message", messageData);
  
  // Add message to UI immediately
  if (currentAttachment) {
    addMessageWithAttachment(message, currentAttachment, "user");
  } else {
    addMessage(message, "user");
  }

  // Reset input and attachment
  messageInput.value = "";
  messageInput.style.height = "auto";
  messageInput.disabled = true;
  sendBtn.disabled = true;
  removeAttachment();

  showTypingIndicator();
}

// Clear conversation function
function clearConversation() {
  socket.emit("clear_conversation", {
    user_email: user.email,
    session_id: sessionId
  });
  
  // The UI will be updated when we receive the 'conversation_cleared' event
}

// Attachment functions
function triggerFileUpload() {
  if (fileInput) fileInput.click();
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Validate file type
  if (!file.type.startsWith('image/')) {
    alert('Please select an image file.');
    return;
  }

  // Validate file size (max 5MB)
  if (file.size > 5 * 1024 * 1024) {
    alert('File size must be less than 5MB.');
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    currentAttachment = {
      name: file.name,
      type: file.type,
      data: e.target.result,
      size: file.size
    };
    
    showAttachmentPreview();
  };
  reader.readAsDataURL(file);
}

function showAttachmentPreview() {
  if (!currentAttachment || !attachmentPreview) return;
  
  if (previewImage) previewImage.src = currentAttachment.data;
  if (fileName) fileName.textContent = currentAttachment.name;
  attachmentPreview.style.display = 'block';
}

function removeAttachment() {
  currentAttachment = null;
  if (attachmentPreview) attachmentPreview.style.display = 'none';
  if (fileInput) fileInput.value = '';
}

function addMessage(content, sender, isHTML = false) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${sender}`;

  if (isHTML) {
    messageDiv.innerHTML = content;
  } else {
    const p = document.createElement("p");
    p.textContent = content;
    messageDiv.appendChild(p);
  }

  chatMessages.appendChild(messageDiv);
  applyMessageAnimation(messageDiv);
  scrollToBottom();
}

function addMessageWithAttachment(text, attachment, sender) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${sender}`;

  let content = '';
  if (text) {
    content += `<p>${text}</p>`;
  }
  
  if (attachment) {
    content += `<img src="${attachment.data}" alt="${attachment.name}" class="attachment-image" style="max-width: 200px; border-radius: 8px; margin-top: 0.5rem;">`;
  }

  messageDiv.innerHTML = content;
  chatMessages.appendChild(messageDiv);
  applyMessageAnimation(messageDiv);
  scrollToBottom();
}

function applyMessageAnimation(element) {
  element.style.opacity = "0";
  element.style.transform = "translateY(20px)";

  setTimeout(() => {
    element.style.transition = "opacity 0.3s ease, transform 0.3s ease";
    element.style.opacity = "1";
    element.style.transform = "translateY(0)";
  }, 100);
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
  const typingDiv = document.createElement("div");
  typingDiv.className = "message bot typing-indicator";
  typingDiv.id = "typingIndicator";
  typingDiv.innerHTML = `
    <div style="display: flex; align-items: center; gap: 0.5rem;">
      <div class="typing-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span style="font-size: 0.9rem; opacity: 0.7;">Kare is typing...</span>
    </div>
  `;

  chatMessages.appendChild(typingDiv);
  scrollToBottom();
}

function hideTypingIndicator() {
  const typingIndicator = document.getElementById("typingIndicator");
  if (typingIndicator) typingIndicator.remove();
}

// Sidebar functionality
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  
  if (sidebar && overlay) {
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
  }
}

// Logout function
function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  socket.disconnect();
  window.location.href = 'login.html';
}

// Update user info in sidebar
document.addEventListener('DOMContentLoaded', () => {
  if (user.name) {
    // Update any user display elements if they exist
    const userNameElements = document.querySelectorAll('.user-name');
    userNameElements.forEach(el => el.textContent = user.name);
    
    // Show user initials in avatar
    const userAvatarElements = document.querySelectorAll('.user-avatar');
    userAvatarElements.forEach(el => {
      el.textContent = user.name ? user.name.charAt(0).toUpperCase() : 'U';
    });
  }
});