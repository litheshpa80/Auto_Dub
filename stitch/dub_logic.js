// Handles file upload and calls the FastAPI backend for transcribe, translate, or dub

document.addEventListener('DOMContentLoaded', function () {
    const uploadSection = document.querySelector('[id="upload-tool"]');
    const dropArea = uploadSection.querySelector('.border-dashed');
    const transcriptBox = document.getElementById('transcript-box');
    
    // Selectors by ID
    const languageSelect = document.getElementById('language-select');
    const modelSelect = document.getElementById('model-select');
    
    const taskButtons = uploadSection.querySelectorAll('[data-task-button]');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    // New UI Elements for Media Preview
    const videoPlayer = document.getElementById('video-player');
    const placeholderBars = document.getElementById('placeholder-bars');
    const downloadMediaBtn = document.getElementById('download-media-btn');
    const mediaHeader = document.getElementById('media-header');
    const lipsyncOption = document.getElementById('lipsync-option');
    const lipsyncCheckbox = document.getElementById('lipsync-checkbox');

    let selectedTask = 'transcribe';
    let currentBlobUrl = null;
    let pollInterval = null;

    async function readErrorMessage(response, fallbackMessage) {
        const contentType = response.headers.get('content-type') || '';

        if (contentType.includes('application/json')) {
            try {
                const data = await response.json();
                return data.error || fallbackMessage;
            } catch (_) {
                return fallbackMessage;
            }
        }

        try {
            const text = await response.text();
            return text || fallbackMessage;
        } catch (_) {
            return fallbackMessage;
        }
    }

    function setActiveTaskButton(activeButton) {
        taskButtons.forEach(button => {
            button.classList.remove('bg-primary', 'text-on-primary', 'shadow-ambient');
            button.classList.add('text-on-surface-variant');
        });

        activeButton.classList.remove('text-on-surface-variant');
        activeButton.classList.add('bg-primary', 'text-on-primary', 'shadow-ambient');
    }

    // Highlight the starting button
    if (taskButtons.length) {
        setActiveTaskButton(taskButtons[0]);
    }

    // Task button logic
    const liveDubControls = document.getElementById('live-dub-controls');
    const dropAreaBox = document.getElementById('drop-area-box');

    taskButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            setActiveTaskButton(this);
            const text = this.textContent.trim().toLowerCase();
            
            // Reset UI states
            lipsyncOption.classList.add('hidden');
            liveDubControls.classList.add('hidden');
            dropAreaBox.classList.remove('hidden');

            if (text === 'dub video') {
                selectedTask = 'dub';
                lipsyncOption.classList.remove('hidden');
            } else if (text === 'live dub') {
                selectedTask = 'live-dub';
                liveDubControls.classList.remove('hidden');
                dropAreaBox.classList.add('hidden');
            } else {
                selectedTask = text;
            }
        });
    });

    // Drag & drop + click-to-upload logic
    const hiddenFileInput = document.getElementById('hidden-file-input');
    
    hiddenFileInput.addEventListener('change', () => {
        handleFiles(hiddenFileInput.files);
    });

    dropArea.addEventListener('click', () => {
        hiddenFileInput.click();
    });
    dropArea.addEventListener('dragover', e => { e.preventDefault(); dropArea.classList.add('border-primary'); });
    dropArea.addEventListener('dragleave', e => { e.preventDefault(); dropArea.classList.remove('border-primary'); });
    dropArea.addEventListener('drop', e => {
        e.preventDefault();
        dropArea.classList.remove('border-primary');
        handleFiles(e.dataTransfer.files);
    });

    function pollStatus(jobId) {
        if (pollInterval) clearInterval(pollInterval);
        
        pollInterval = setInterval(() => {
            fetch(`/status/${jobId}`)
            .then(r => r.json())
            .then(data => {
                if (data.status && data.status !== 'Waiting...') {
                    transcriptBox.textContent = data.status;
                    if (data.status === 'DONE') {
                        clearInterval(pollInterval);
                    }
                }
            })
            .catch(() => { /* keep polling */ });
        }, 2000);
    }

    function handleFiles(files) {
        if (!files.length) return;
        const file = files[0];
        
        // Reset UI for new upload
        if (currentBlobUrl) {
            window.URL.revokeObjectURL(currentBlobUrl);
            currentBlobUrl = null;
        }
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
        
        videoPlayer.classList.add('hidden');
        placeholderBars.classList.remove('hidden');
        downloadMediaBtn.classList.add('hidden');

        // Show loading screen
        loadingOverlay.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', file);
        formData.append('language', languageSelect.value);
        formData.append('model_size', modelSelect.value);
        formData.append('lipsync', lipsyncCheckbox.checked);

        if (selectedTask === 'dub') {
            const jobId = 'job_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
            formData.append('job_id', jobId);
            mediaHeader.textContent = 'Processing Video...';
            transcriptBox.textContent = `Uploading "${file.name}" for AI dubbing...\nInitializing high-quality "${modelSelect.value}" pipeline.`;
            pollStatus(jobId);

            fetch('/dub/', {
                method: 'POST',
                body: formData
            })
            .then(async response => {
                if (!response.ok) {
                    const message = await readErrorMessage(response, 'Dubbing failed');
                    throw new Error(message);
                }
                return response.blob();
            })
            .then(blob => {
                clearInterval(pollInterval);
                loadingOverlay.classList.add('hidden');
                transcriptBox.textContent = 'Dubbing complete! You can now watch and download the result below.';
                mediaHeader.textContent = 'Dubbed Video Preview';

                currentBlobUrl = window.URL.createObjectURL(blob);
                videoPlayer.src = currentBlobUrl;
                videoPlayer.classList.remove('hidden');
                placeholderBars.classList.add('hidden');

                downloadMediaBtn.classList.remove('hidden');
                downloadMediaBtn.onclick = () => {
                    const a = document.createElement('a');
                    a.href = currentBlobUrl;
                    a.download = file.name.replace(/\.[^.]+$/, '_dubbed.mp4');
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                };
                transcriptBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
            })
            .catch((err) => {
                if (pollInterval) clearInterval(pollInterval);
                loadingOverlay.classList.add('hidden');
                transcriptBox.textContent = `Dubbing error: ${err.message}`;
                mediaHeader.textContent = 'Media Preview';
                transcriptBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
            });
        } else {
            transcriptBox.textContent = `Uploading "${file.name}" for ${selectedTask}...\n\nProcessing using "${modelSelect.value}" quality model.`;
            formData.append('task', selectedTask);
            fetch('/transcribe/', {
                method: 'POST',
                body: formData
            })
            .then(async r => {
                if (!r.ok) {
                    const message = await readErrorMessage(r, 'Request failed');
                    throw new Error(message);
                }
                return r.json();
            })
            .then(data => {
                loadingOverlay.classList.add('hidden');
                transcriptBox.textContent = data.text || 'No transcript.';
                transcriptBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
            })
            .catch((err) => {
                loadingOverlay.classList.add('hidden');
                transcriptBox.textContent = `Error: ${err.message}`;
                transcriptBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
            });
        }
    }

    // Live Dubbing Logic
    const startLiveBtn = document.getElementById('start-live-btn');
    const stopLiveBtn = document.getElementById('stop-live-btn');
    const liveStatus = document.getElementById('live-status');
    
    let liveSocket = null;
    let liveStream = null;
    let isRecording = false;
    let audioQueue = [];
    let isPlaying = false;
    let audioContext = null;

    async function initAudio() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }
    }

    startLiveBtn.addEventListener('click', async () => {
        try {
            await initAudio();
            liveStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            liveSocket = new WebSocket(`${wsProtocol}//${window.location.host}/live-dub`);
            liveSocket.binaryType = 'arraybuffer';
            
            liveSocket.onopen = () => {
                isRecording = true;
                const liveTargetLang = document.getElementById('live-target-language');
                liveSocket.send(JSON.stringify({
                    language: liveTargetLang ? liveTargetLang.value : 'spanish',
                    model_size: modelSelect.value || 'base'
                }));
                
                startLiveBtn.classList.add('hidden');
                stopLiveBtn.classList.remove('hidden');
                liveStatus.classList.remove('hidden');
                liveStatus.textContent = 'Connected. Speak now!';
                transcriptBox.textContent = 'Live stream connected. Speak into your microphone...\n';
                
                recordChunk();
            };
            
            function recordChunk() {
                if (!isRecording) return;
                
                let mimeType = 'audio/webm';
                if (!MediaRecorder.isTypeSupported(mimeType)) {
                    if (MediaRecorder.isTypeSupported('audio/mp4')) mimeType = 'audio/mp4';
                    else if (MediaRecorder.isTypeSupported('audio/ogg')) mimeType = 'audio/ogg';
                    else mimeType = '';
                }
                
                let recorder = new MediaRecorder(liveStream, { mimeType: mimeType });
                let chunks = [];
                
                recorder.ondataavailable = e => {
                    if (e.data.size > 0) chunks.push(e.data);
                };
                
                recorder.onstop = () => {
                    if (chunks.length > 0 && liveSocket && liveSocket.readyState === WebSocket.OPEN) {
                        const blob = new Blob(chunks, { type: mimeType });
                        liveSocket.send(blob);
                    }
                    if (isRecording) {
                        recordChunk();
                    }
                };
                
                recorder.start();
                setTimeout(() => {
                    if (recorder.state === 'recording') recorder.stop();
                }, 2500);
            }
            
            liveSocket.onmessage = async (event) => {
                if (typeof event.data === 'string') {
                    const data = JSON.parse(event.data);
                    if (data.type === 'transcript') {
                        transcriptBox.textContent += `\n[Original]: ${data.original}\n[Translated]: ${data.translated}\n`;
                        transcriptBox.scrollTop = transcriptBox.scrollHeight;
                        liveStatus.textContent = "Playing dubbed audio...";
                    } else if (data.type === 'info') {
                        liveStatus.textContent = data.message;
                    } else if (data.type === 'error') {
                        transcriptBox.textContent += `\n[Error]: ${data.message}\n`;
                        transcriptBox.scrollTop = transcriptBox.scrollHeight;
                        liveStatus.textContent = "Error occurred.";
                    }
                } else {
                    transcriptBox.textContent += `\n[System]: Received audio packet (${event.data.byteLength} bytes). Queueing...\n`;
                    transcriptBox.scrollTop = transcriptBox.scrollHeight;
                    audioQueue.push(event.data);
                    playNextAudio();
                }
            };
            
            liveSocket.onclose = () => {
                stopLive();
                liveStatus.textContent = "Connection closed.";
            };
            
        } catch (err) {
            alert('Could not access microphone: ' + err.message);
        }
    });

    async function playNextAudio() {
        if (isPlaying || audioQueue.length === 0) return;
        
        // Ensure AudioContext is active
        try {
            await initAudio();
        } catch (ctxErr) {
            console.error("Failed to resume AudioContext:", ctxErr);
            transcriptBox.textContent += `\n[Playback Error]: Failed to activate Audio Context: ${ctxErr.message || ctxErr}\n`;
            transcriptBox.scrollTop = transcriptBox.scrollHeight;
        }

        isPlaying = true;
        const arrayBuffer = audioQueue.shift();
        try {
            transcriptBox.textContent += `[System]: Decoding audio packet...\n`;
            transcriptBox.scrollTop = transcriptBox.scrollHeight;
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContext.destination);
            
            source.onended = () => {
                isPlaying = false;
                if (isRecording) liveStatus.textContent = "Listening...";
                playNextAudio();
            };
            
            source.start(0);
            transcriptBox.textContent += `[System]: Playing dubbed audio chunk.\n`;
            transcriptBox.scrollTop = transcriptBox.scrollHeight;
        } catch (e) {
            console.error("Audio playback error:", e);
            transcriptBox.textContent += `\n[Playback Error]: Failed to decode/play audio: ${e.message || e}\n`;
            transcriptBox.scrollTop = transcriptBox.scrollHeight;
            isPlaying = false;
            playNextAudio();
        }
    }
    
    stopLiveBtn.addEventListener('click', stopLive);
    
    function stopLive() {
        isRecording = false;
        if (liveStream) {
            liveStream.getTracks().forEach(t => t.stop());
            liveStream = null;
        }
        if (liveSocket) {
            liveSocket.close();
            liveSocket = null;
        }
        
        startLiveBtn.classList.remove('hidden');
        stopLiveBtn.classList.add('hidden');
        liveStatus.classList.add('hidden');
        transcriptBox.textContent += '\n\n--- Live stream ended ---';
        transcriptBox.scrollTop = transcriptBox.scrollHeight;
    }
});
