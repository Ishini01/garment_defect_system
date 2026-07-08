/**
 * ============================================
 * GARMENT DEFECT DETECTION SYSTEM - MAIN JAVASCRIPT
 * SDS Compliant - Team Aurors
 * ============================================
 */

// ============================================
// TOAST NOTIFICATIONS
// ============================================

function showToast(message, type = 'info') {
    const colors = {
        success: '#2e7d32',
        danger: '#c62828',
        warning: '#f57c00',
        info: '#0d47a1'
    };

    // Create toast container if it doesn't exist
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.position = 'fixed';
        container.style.top = '80px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        container.style.maxWidth = '400px';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white border-0 fade show';
    toast.style.backgroundColor = colors[type] || colors.info;
    toast.style.borderRadius = '8px';
    toast.style.marginBottom = '10px';
    toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'times-circle' : 'info-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// ============================================
// CAMERA FUNCTIONS
// ============================================

let stream = null;
let videoElement = null;
let canvasElement = null;
let capturedImageElement = null;

function initCameraElements() {
    videoElement = document.getElementById('videoFeed');
    canvasElement = document.getElementById('canvas');
    capturedImageElement = document.getElementById('capturedImage');
}

function startCamera() {
    initCameraElements();
    
    if (!videoElement) {
        console.error('Video element not found');
        return;
    }

    navigator.mediaDevices.getUserMedia({
        video: {
            facingMode: 'environment',
            width: { ideal: 1280 },
            height: { ideal: 720 }
        },
        audio: false
    })
    .then(s => {
        stream = s;
        videoElement.srcObject = stream;
        videoElement.style.display = 'block';
        if (capturedImageElement) {
            capturedImageElement.style.display = 'none';
        }
        const captureBtn = document.getElementById('captureBtn');
        if (captureBtn) {
            captureBtn.removeAttribute('disabled');
        }
        showToast('Camera started successfully!', 'success');
    })
    .catch(err => {
        showToast('Camera error: ' + err.message, 'danger');
        console.error('Camera error:', err);
    });
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    if (videoElement) {
        videoElement.srcObject = null;
    }
    const captureBtn = document.getElementById('captureBtn');
    if (captureBtn) {
        captureBtn.setAttribute('disabled', 'disabled');
    }
    showToast('Camera stopped.', 'info');
}

function captureImage() {
    if (!stream) {
        showToast('Please start the camera first.', 'warning');
        return;
    }

    if (!videoElement || !canvasElement || !capturedImageElement) {
        initCameraElements();
    }

    const context = canvasElement.getContext('2d');
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    context.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);

    capturedImageElement.src = canvasElement.toDataURL('image/jpeg');
    capturedImageElement.style.display = 'block';
    videoElement.style.display = 'none';

    // Auto-detect after capture
    detectImage(capturedImageElement.src);
}

function resetInspection() {
    if (capturedImageElement) {
        capturedImageElement.style.display = 'none';
    }
    if (videoElement) {
        videoElement.style.display = 'block';
    }
    const resultsCard = document.getElementById('resultsCard');
    if (resultsCard) {
        resultsCard.style.display = 'none';
    }
    const fileInput = document.getElementById('imageFile');
    if (fileInput) {
        fileInput.value = '';
    }
    showToast('Reset successful.', 'info');
}

// ============================================
// DEFECT DETECTION
// ============================================

function detectImage(imageData) {
    const resultsCard = document.getElementById('resultsCard');
    const resultsHeader = document.getElementById('resultsHeader');
    const resultsBody = document.getElementById('resultsBody');

    if (resultsCard) {
        resultsCard.style.display = 'block';
    }
    if (resultsHeader) {
        resultsHeader.className = 'card-header bg-warning text-white';
        resultsHeader.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    }
    if (resultsBody) {
        resultsBody.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;" role="status"></div>
                <p class="mt-3 text-muted">Analyzing garment for defects...</p>
            </div>
        `;
    }

    // Convert image to blob
    fetch(imageData)
        .then(response => response.blob())
        .then(blob => {
            const formData = new FormData();
            formData.append('image', blob, 'captured_image.jpg');

            return fetch('/api/detect', {
                method: 'POST',
                body: formData
            });
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    if (text.includes('login')) {
                        throw new Error('Please login first. Redirecting...');
                    }
                    throw new Error('Server error. Please try again.');
                });
            }
            return response.json();
        })
        .then(data => {
            displayResults(data);
            if (data.has_defect) {
                playAlarm(data.defects);
            }
        })
        .catch(error => {
            const resultsBody = document.getElementById('resultsBody');
            if (resultsBody) {
                resultsBody.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle"></i> ${error.message}
                    </div>
                    ${error.message.includes('login') ? `
                        <div class="text-center mt-3">
                            <a href="/login" class="btn btn-primary">Go to Login</a>
                        </div>
                    ` : ''}
                `;
            }
            console.error('Detection error:', error);
        });
}

function displayResults(data) {
    const isPass = data.overall_status === 'PASS';
    const resultsHeader = document.getElementById('resultsHeader');
    const resultsBody = document.getElementById('resultsBody');

    if (resultsHeader) {
        resultsHeader.className = `card-header text-white ${isPass ? 'bg-success' : 'bg-danger'}`;
        resultsHeader.innerHTML = `
            <i class="fas fa-${isPass ? 'check-circle' : 'times-circle'}"></i> 
            ${isPass ? 'PASS' : 'FAIL'}
        `;
    }

    let defectsHtml = '';
    if (data.defects && data.defects.length > 0) {
        defectsHtml = `
            <div class="mt-3">
                <h6 class="text-danger"><i class="fas fa-bug"></i> Defects Found:</h6>
                <ul class="list-group">
                    ${data.defects.map(d => 
                        `<li class="list-group-item list-group-item-danger"><i class="fas fa-exclamation-triangle me-2"></i> ${d}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (resultsBody) {
        resultsBody.innerHTML = `
            <div class="text-center mb-3">
                <h2 class="${isPass ? 'text-success' : 'text-danger'}">
                    ${isPass ? '✅ PASS' : '❌ FAIL'}
                </h2>
            </div>
            
            <div class="row g-2">
                <div class="col-6">
                    <div class="border rounded p-2 text-center">
                        <small class="text-muted">Buttons Found</small>
                        <h4 class="mb-0">${data.button_count} / ${data.expected}</h4>
                    </div>
                </div>
                <div class="col-6">
                    <div class="border rounded p-2 text-center">
                        <small class="text-muted">Alignment Score</small>
                        <h4 class="mb-0">${(data.alignment_score || 0).toFixed(1)}%</h4>
                    </div>
                </div>
            </div>
            
            <div class="mt-3">
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar ${data.alignment_score > 70 ? 'bg-success' : data.alignment_score > 40 ? 'bg-warning' : 'bg-danger'}" 
                         style="width: ${data.alignment_score || 0}%">
                        ${(data.alignment_score || 0).toFixed(1)}%
                    </div>
                </div>
            </div>
            
            ${defectsHtml}
            
            <div class="mt-3 d-grid gap-2">
                <button class="btn btn-primary" onclick="window.location.href='/history'">
                    <i class="fas fa-history"></i> View History
                </button>
                <button class="btn btn-outline-secondary" onclick="resetInspection()">
                    <i class="fas fa-redo"></i> New Inspection
                </button>
            </div>
        `;
    }
}

// ============================================
// ALARM SYSTEM
// ============================================

function playAlarm(defects) {
    // Show visual alarm
    let overlay = document.getElementById('alarmOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'alarmOverlay';
        overlay.className = 'alarm-indicator';
        overlay.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <div>⚠️ DEFECT DETECTED!</div>
            <small style="font-size: 16px; display: block; margin-top: 10px;"></small>
        `;
        document.body.appendChild(overlay);
    }
    
    overlay.classList.add('show');
    const small = overlay.querySelector('small');
    if (small && defects && defects.length > 0) {
        small.textContent = defects.join(' • ');
    }

    // Play audio alarm
    try {
        const audio = new Audio('/static/sounds/alarm.wav');
        audio.play().catch(() => {
            // Fallback: beep using Web Audio API
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.frequency.value = 880;
                oscillator.type = 'square';
                gainNode.gain.value = 0.3;
                oscillator.start();
                setTimeout(() => oscillator.stop(), 800);
            } catch (err) {
                console.log('Could not play sound');
            }
        });
    } catch (e) {
        console.log('Audio not supported');
    }

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        overlay.classList.remove('show');
    }, 5000);

    // Browser notification
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('⚠️ Defect Detected!', {
            body: defects ? defects.join('\n') : 'Defect found in garment!',
            icon: '/static/favicon.ico'
        });
    }
}

function requestNotificationPermission() {
    if ('Notification' in window) {
        Notification.requestPermission();
    }
}

// ============================================
// UPLOAD HANDLER
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Upload form handler
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const fileInput = document.getElementById('imageFile');
            if (!fileInput.files || !fileInput.files[0]) {
                showToast('Please select an image file.', 'warning');
                return;
            }

            const file = fileInput.files[0];
            const reader = new FileReader();
            reader.onload = function(event) {
                detectImage(event.target.result);
            };
            reader.readAsDataURL(file);
        });
    }

    // Drag and Drop
    const uploadArea = document.querySelector('.upload-area');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) {
                const fileInput = document.getElementById('imageFile');
                if (fileInput) {
                    fileInput.files = e.dataTransfer.files;
                }
                const reader = new FileReader();
                reader.onload = function(event) {
                    detectImage(event.target.result);
                };
                reader.readAsDataURL(file);
                showToast('File uploaded: ' + file.name, 'success');
            }
        });
    }

    // Auto-start camera on inspect page
    if (document.getElementById('videoFeed')) {
        startCamera();
    }

    // Request notification permission
    requestNotificationPermission();

    // Auto-hide flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});

// ============================================
// HISTORY FILTER
// ============================================

function filterHistory(period) {
    const rows = document.querySelectorAll('#historyTable tbody tr');
    const now = new Date();
    const filterDate = new Date();
    
    switch(period) {
        case 'today':
            filterDate.setHours(0, 0, 0, 0);
            break;
        case 'week':
            filterDate.setDate(filterDate.getDate() - 7);
            break;
        case 'month':
            filterDate.setMonth(filterDate.getMonth() - 1);
            break;
        default:
            rows.forEach(row => row.style.display = '');
            return;
    }

    rows.forEach(row => {
        const dateCell = row.querySelector('td:nth-child(2)');
        if (dateCell) {
            const rowDate = new Date(dateCell.textContent);
            if (rowDate >= filterDate) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    });
}

// ============================================
// REPORT GENERATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    const reportForm = document.getElementById('reportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const btn = this.querySelector('button[type="submit"]');
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
            btn.disabled = true;
            
            fetch('/api/generate-report', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('✅ Report generated successfully!', 'success');
                    window.location.href = data.download_url;
                } else {
                    showToast('❌ ' + data.error, 'danger');
                }
            })
            .catch(error => {
                showToast('Error: ' + error.message, 'danger');
            })
            .finally(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            });
        });
    }
});

// ============================================
// EXPORT FUNCTIONS (for inline HTML use)
// ============================================

window.startCamera = startCamera;
window.stopCamera = stopCamera;
window.captureImage = captureImage;
window.resetInspection = resetInspection;
window.detectImage = detectImage;
window.displayResults = displayResults;
window.playAlarm = playAlarm;
window.showToast = showToast;
window.filterHistory = filterHistory;