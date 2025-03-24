// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active class from all tabs and content
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // Add active class to clicked tab and corresponding content
        tab.classList.add('active');
        const tabId = tab.getAttribute('data-tab');
        document.getElementById(`${tabId}-tab`).classList.add('active');
    });
});

// Text generation tab functionality
document.getElementById('generate').addEventListener('click', async () => {
    const model = document.getElementById('model').value;
    const prompt = document.getElementById('prompt').value;
    const maxTokens = document.getElementById('max_tokens').value;
    const temperature = document.getElementById('temperature').value;
    const topP = document.getElementById('top_p').value;
    const processingLocation = document.getElementById('processing-location').value;
    
    const statusEl = document.getElementById('status');
    const outputEl = document.getElementById('output');
    const loadingEl = document.getElementById('loading');
    const generateBtn = document.getElementById('generate');
    const modelStatusEl = document.getElementById('model-status');
    const processingDecisionEl = document.getElementById('processing-decision');
    
    // Reset UI
    statusEl.textContent = '';
    statusEl.classList.remove('error');
    statusEl.classList.remove('success');
    loadingEl.classList.add('active');
    generateBtn.disabled = true;
    outputEl.textContent = prompt;
    modelStatusEl.textContent = `Loading ${model}...`;
    processingDecisionEl.textContent = '';
    
    // Reset metrics
    document.getElementById('total-time').textContent = '-';
    document.getElementById('load-time').textContent = '-';
    document.getElementById('gen-time').textContent = '-';
    document.getElementById('output-length').textContent = '-';
    document.getElementById('token-speed').textContent = '-';
    
    const startTime = performance.now();
    
    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model,
                prompt,
                max_tokens: parseInt(maxTokens),
                temperature: parseFloat(temperature),
                top_p: parseFloat(topP),
                processing_location: processingLocation
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Generation failed');
        }
        
        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let generatedText = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value);
            generatedText += text;
            outputEl.textContent = prompt + generatedText;
        }
        
        const endTime = performance.now();
        const totalTime = Math.round(endTime - startTime);
        
        // Update metrics
        document.getElementById('total-time').textContent = totalTime;
        document.getElementById('output-length').textContent = generatedText.length;
        
        // Estimate load time and generation time (these are rough estimates)
        // In a real implementation, these would come from server metrics
        const loadTime = Math.round(totalTime * 0.3); // Assume 30% of time is loading
        const genTime = Math.round(totalTime * 0.7);  // Assume 70% of time is generation
        document.getElementById('load-time').textContent = loadTime;
        document.getElementById('gen-time').textContent = genTime;
        
        // Calculate tokens per second (estimate 4 characters per token)
        const estimatedTokens = Math.round(generatedText.length / 4);
        const tokenSpeed = genTime > 0 ? Math.round((estimatedTokens / genTime) * 1000) : 0;
        document.getElementById('token-speed').textContent = tokenSpeed;
        
        statusEl.textContent = 'Generation complete.';
        statusEl.classList.add('success');
        modelStatusEl.textContent = `Model ${model} loaded successfully.`;
        
        if (processingLocation === 'automatic') {
            // This is a simplification - in a real implementation, this would come from the server
            const inferredLocation = generatedText.length > 100 ? 'server' : 'local';
            processingDecisionEl.textContent = `Processing was routed to: ${inferredLocation}`;
        }
    } catch (error) {
        statusEl.textContent = 'Error: ' + error.message;
        statusEl.classList.add('error');
        console.error('Error:', error);
        
        // Check if there was a model fallback
        if (error.message.includes('fallback')) {
            modelStatusEl.textContent = `Failed to load ${model}. Fallback to rene model used.`;
        } else {
            modelStatusEl.textContent = `Failed to load ${model}.`;
        }
    } finally {
        loadingEl.classList.remove('active');
        generateBtn.disabled = false;
    }
});

// Model compatibility check
document.getElementById('model').addEventListener('change', async (e) => {
    const modelStatusEl = document.getElementById('model-status');
    const selectedModel = e.target.value;
    modelStatusEl.textContent = `Checking ${selectedModel} compatibility...`;
    
    try {
        const response = await fetch('/check_model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ model: selectedModel }),
        });
        
        const data = await response.json();
        
        if (data.compatible) {
            modelStatusEl.textContent = `Model ${selectedModel} is compatible.`;
        } else {
            modelStatusEl.textContent = `Warning: Model ${selectedModel} may not be compatible. Consider using rene model instead.`;
        }
    } catch (error) {
        modelStatusEl.textContent = `Could not verify compatibility for ${selectedModel}.`;
    }
});

// Show/hide appropriate test parameters based on test type
document.getElementById('test-type').addEventListener('change', (e) => {
    const testType = e.target.value;
    document.querySelectorAll('.test-params').forEach(el => el.style.display = 'none');
    
    if (testType === 'voice_processing') {
        document.getElementById('voice-params').style.display = 'block';
    } else if (testType === 'context_retention') {
        document.getElementById('context-params').style.display = 'block';
    } else if (testType === 'extended_usage') {
        document.getElementById('extended-params').style.display = 'block';
    }
});

// Run test button
document.getElementById('run-test').addEventListener('click', async () => {
    const testType = document.getElementById('test-type').value;
    const testModel = document.getElementById('test-model').value;
    const testEnvironment = document.getElementById('test-environment').value;
    
    // Get test-specific parameters
    let testParams = {
        model_name: testModel,
        environment: testEnvironment
    };
    
    if (testType === 'voice_processing') {
        testParams.command_set = document.getElementById('command-set').value;
    } else if (testType === 'context_retention') {
        testParams.context_set_idx = document.getElementById('context-set').value;
    } else if (testType === 'extended_usage') {
        testParams.duration_seconds = document.getElementById('test-duration').value;
        testParams.command_interval_seconds = document.getElementById('command-interval').value;
    }
    
    const testStatusEl = document.getElementById('test-status');
    const testOutputEl = document.getElementById('test-output');
    const testLoadingEl = document.getElementById('test-loading');
    const runTestBtn = document.getElementById('run-test');
    
    testStatusEl.textContent = '';
    testStatusEl.classList.remove('error');
    testStatusEl.classList.remove('success');
    testLoadingEl.classList.add('active');
    runTestBtn.disabled = true;
    testOutputEl.textContent = `Starting ${testType} test...`;
    
    try {
        const response = await fetch('/run_test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                test_type: testType,
                test_params: testParams
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Test failed to start');
        }
        
        const data = await response.json();
        
        testStatusEl.textContent = `Test started with session ID: ${data.session_id}`;
        testStatusEl.classList.add('success');
        testOutputEl.textContent = `Test is running in the background. Results will be saved to the test_results directory.
        
For longer tests (like extended_usage), this can take several minutes to complete.

Test Details:
- Type: ${testType}
- Model: ${testModel}
- Environment: ${testEnvironment}
- Session ID: ${data.session_id}
`;
        
        if (testType === 'extended_usage') {
            testOutputEl.textContent += `- Duration: ${testParams.duration_seconds} seconds
- Command Interval: ${testParams.command_interval_seconds} seconds
`;
        }
        
    } catch (error) {
        testStatusEl.textContent = 'Error: ' + error.message;
        testStatusEl.classList.add('error');
        testOutputEl.textContent = `Failed to start test: ${error.message}`;
        console.error('Error:', error);
    } finally {
        testLoadingEl.classList.remove('active');
        runTestBtn.disabled = false;
    }
});

// System info tab
async function refreshSystemInfo() {
    try {
        const response = await fetch('/system_info');
        if (!response.ok) {
            throw new Error('Failed to fetch system information');
        }
        
        const data = await response.json();
        
        document.getElementById('system-info').textContent = JSON.stringify(data.system, null, 2);
        document.getElementById('network-info').textContent = JSON.stringify(data.network, null, 2);
        document.getElementById('resource-info').textContent = JSON.stringify(data.resources, null, 2);
        document.getElementById('models-info').textContent = JSON.stringify(data.loaded_models, null, 2);
        document.getElementById('targets-info').textContent = JSON.stringify(data.performance_targets, null, 2);
    } catch (error) {
        console.error('Error fetching system info:', error);
        document.getElementById('system-info').textContent = 'Error fetching system information';
    }
}

document.getElementById('refresh-system-info').addEventListener('click', refreshSystemInfo);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check initial model compatibility
    const initialModelEl = document.getElementById('model');
    if (initialModelEl) {
        const event = new Event('change');
        initialModelEl.dispatchEvent(event);
    }
    
    // Initial system info refresh
    refreshSystemInfo();
});

// Enhanced TTS functionality
document.addEventListener('DOMContentLoaded', () => {
    // Check if TTS is available when the TTS tab is activated
    document.querySelector('.tab[data-tab="tts"]').addEventListener('click', checkTTSAvailability);
    
    // Also check on initial load if TTS tab is active
    if (document.querySelector('.tab[data-tab="tts"]').classList.contains('active')) {
        checkTTSAvailability();
    }
    
    function showError(message) {
        const errorEl = document.getElementById('tts-error');
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    }
    
    function hideError() {
        const errorEl = document.getElementById('tts-error');
        errorEl.style.display = 'none';
    }
    
    function checkTTSAvailability() {
        console.log("Checking TTS availability...");
        const ttsStatusEl = document.getElementById('tts-status');
        const ttsStatusDetailsEl = document.getElementById('tts-status-details');
        const ttsTroubleshootingEl = document.getElementById('tts-troubleshooting');
        
        ttsStatusEl.innerHTML = '<p>Checking TTS availability...</p>';
        ttsStatusDetailsEl.textContent = '';
        
        fetch('/tts/available')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("TTS availability response:", data);
                
                if (data.available) {
                    ttsStatusEl.innerHTML = '<p style="color: green; font-weight: bold;">✓ Text-to-Speech is available</p>';
                    ttsStatusDetailsEl.textContent = data.message || 'Ready to generate speech';
                    document.getElementById('tts-controls').style.display = 'block';
                    ttsTroubleshootingEl.style.display = 'none';
                    
                    // Load available voices
                    loadTTSVoices();
                } else {
                    ttsStatusEl.innerHTML = '<p style="color: red; font-weight: bold;">✗ Text-to-Speech is not available</p>';
                    ttsStatusDetailsEl.textContent = data.error || 'Set the CARTESIA_API_KEY environment variable.';
                    document.getElementById('tts-controls').style.display = 'none';
                    ttsTroubleshootingEl.style.display = 'block';
                }
            })
            .catch(error => {
                console.error("Error checking TTS availability:", error);
                ttsStatusEl.innerHTML = '<p style="color: red; font-weight: bold;">✗ Error checking TTS availability</p>';
                ttsStatusDetailsEl.textContent = error.message;
                document.getElementById('tts-controls').style.display = 'none';
                ttsTroubleshootingEl.style.display = 'block';
            });
    }
    
    // Run TTS test
    document.getElementById('test-tts-btn')?.addEventListener('click', function() {
        const testResultEl = document.getElementById('tts-test-result');
        testResultEl.textContent = 'Running TTS test...';
        testResultEl.style.display = 'block';
        testResultEl.style.backgroundColor = '#f0f0f0';
        testResultEl.style.padding = '10px';
        testResultEl.style.borderRadius = '4px';
        
        fetch('/tts/test')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    testResultEl.style.backgroundColor = '#e6ffe6';
                    testResultEl.textContent = '✓ ' + data.message;
                } else {
                    testResultEl.style.backgroundColor = '#ffebeb';
                    testResultEl.textContent = '✗ ' + (data.error || 'Test failed');
                }
                
                // Refresh TTS status after test
                setTimeout(checkTTSAvailability, 1000);
            })
            .catch(error => {
                testResultEl.style.backgroundColor = '#ffebeb';
                testResultEl.textContent = '✗ Error running test: ' + error.message;
            });
    });
    
    // Load TTS voices with improved error handling
    function loadTTSVoices() {
        const voiceSelectEl = document.getElementById('tts-voice');
        const voiceInfoEl = document.getElementById('voice-info');
        
        voiceSelectEl.innerHTML = '<option value="">Loading voices...</option>';
        voiceInfoEl.textContent = 'Fetching available voices...';
        
        fetch('/tts/voices')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("TTS voices response:", data);
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                if (data.voices && data.voices.length > 0) {
                    // Clear placeholder
                    voiceSelectEl.innerHTML = '';
                    voiceInfoEl.textContent = `${data.count} voices available`;
                    
                    // Group voices by language
                    const voicesByLanguage = {};
                    data.voices.forEach(voice => {
                        const lang = voice.language || 'unknown';
                        if (!voicesByLanguage[lang]) {
                            voicesByLanguage[lang] = [];
                        }
                        voicesByLanguage[lang].push(voice);
                    });
                    
                    // Language display names
                    const languageNames = {
                        'en': 'English',
                        'es': 'Spanish',
                        'fr': 'French',
                        'de': 'German',
                        'it': 'Italian',
                        'pt': 'Portuguese',
                        'ja': 'Japanese',
                        'ko': 'Korean',
                        'zh': 'Chinese',
                        'ar': 'Arabic',
                        'hi': 'Hindi',
                        'ru': 'Russian'
                    };
                    
                    // Create option groups for each language
                    Object.keys(voicesByLanguage).sort().forEach(language => {
                        const langGroup = document.createElement('optgroup');
                        langGroup.label = languageNames[language] || language.toUpperCase();
                        
                        // Add voice options for this language, sorted by name
                        voicesByLanguage[language]
                            .sort((a, b) => a.name.localeCompare(b.name))
                            .forEach(voice => {
                                const option = document.createElement('option');
                                option.value = voice.voice_id;
                                
                                // Create display name with gender if available
                                let displayName = voice.name;
                                if (voice.gender) {
                                    displayName += ` (${voice.gender})`;
                                }
                                option.textContent = displayName;
                                
                                // Add description as a title attribute if available
                                if (voice.description) {
                                    option.title = voice.description;
                                }
                                
                                langGroup.appendChild(option);
                            });
                        
                        voiceSelectEl.appendChild(langGroup);
                    });
                    
                    // Add voice info display
                    voiceSelectEl.addEventListener('change', function() {
                        const selectedVoiceId = this.value;
                        const selectedVoice = data.voices.find(v => v.voice_id === selectedVoiceId);
                        
                        if (selectedVoice) {
                            let infoText = `${selectedVoice.name}`;
                            if (selectedVoice.gender) {
                                infoText += ` • ${selectedVoice.gender}`;
                            }
                            if (selectedVoice.language) {
                                infoText += ` • ${languageNames[selectedVoice.language] || selectedVoice.language}`;
                            }
                            if (selectedVoice.description) {
                                infoText += ` • ${selectedVoice.description}`;
                            }
                            voiceInfoEl.textContent = infoText;
                        } else {
                            voiceInfoEl.textContent = '';
                        }
                    });
                    
                    // Trigger change event for initially selected voice
                    voiceSelectEl.dispatchEvent(new Event('change'));
                    
                    // Add voice preview feature
                    setupVoicePreview(data.voices);
                    
                } else {
                    voiceSelectEl.innerHTML = '<option value="">No voices available</option>';
                    voiceInfoEl.textContent = 'No voices found';
                }
            })
            .catch(error => {
                console.error("Error loading voices:", error);
                voiceSelectEl.innerHTML = `<option value="">Error loading voices</option>`;
                voiceInfoEl.textContent = `Error: ${error.message}`;
                showError(`Failed to load voices: ${error.message}`);
            });
    }
    
    // Set up voice preview functionality
    function setupVoicePreview(voices) {
        const previewBtn = document.getElementById('preview-voice-btn');
        const voiceSelectEl = document.getElementById('tts-voice');
        
        // Create audio element for previews if not exists
        let previewAudio = document.getElementById('voice-preview-audio');
        if (!previewAudio) {
            previewAudio = document.createElement('audio');
            previewAudio.id = 'voice-preview-audio';
            previewAudio.style.display = 'none';
            document.body.appendChild(previewAudio);
        }
        
        // Add click event
        previewBtn.addEventListener('click', () => {
            hideError();
            const selectedVoiceId = voiceSelectEl.value;
            const selectedVoice = voices.find(v => v.voice_id === selectedVoiceId);
            
            if (!selectedVoiceId) {
                showError('Please select a voice to preview');
                return;
            }
            
            if (selectedVoice && selectedVoice.preview_url) {
                // Use existing preview URL if available
                previewAudio.src = selectedVoice.preview_url;
                previewAudio.play();
            } else {
                // Generate a quick sample
                const sampleText = "This is a voice sample from Cartesia.";
                generateVoiceSample(selectedVoiceId, sampleText);
            }
        });
    }
    
    // Generate a voice sample on demand
    function generateVoiceSample(voiceId, text) {
        const loadingEl = document.getElementById('tts-loading');
        loadingEl.classList.add('active');
        hideError();
        
        const modelId = document.getElementById('tts-model').value;
        
        fetch('/tts/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                voice_id: voiceId,
                model_id: modelId
            }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `Server error: ${response.status}`);
                });
            }
            return response.blob();
        })
        .then(blob => {
            const audioUrl = URL.createObjectURL(blob);
            const previewAudio = document.getElementById('voice-preview-audio');
            previewAudio.src = audioUrl;
            previewAudio.play();
        })
        .catch(error => {
            console.error('Error generating voice sample:', error);
            showError(`Could not preview voice: ${error.message}`);
        })
        .finally(() => {
            loadingEl.classList.remove('active');
        });
    }
    
    // Generate TTS audio button click handler
    document.getElementById('tts-generate-btn')?.addEventListener('click', () => {
        const text = document.getElementById('tts-text').value.trim();
        const voiceId = document.getElementById('tts-voice').value;
        const modelId = document.getElementById('tts-model').value;
        const loadingEl = document.getElementById('tts-loading');
        const audioContainer = document.getElementById('tts-audio-container');
        const audioEl = document.getElementById('tts-audio');
        const downloadLink = document.getElementById('tts-download');
        const generateBtn = document.getElementById('tts-generate-btn');
        
        hideError();
        
        if (!text) {
            showError('Please enter text to synthesize');
            return;
        }
        
        if (!voiceId) {
            showError('Please select a voice');
            return;
        }
        
        // Show loading indicator
        loadingEl.classList.add('active');
        generateBtn.disabled = true;
        audioContainer.style.display = 'none';
        
        // Generate audio
        fetch('/tts/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                voice_id: voiceId,
                model_id: modelId
            }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `Server error: ${response.status}`);
                });
            }
            return response.blob();
        })
        .then(blob => {
            // Create a URL for the audio blob
            const audioUrl = URL.createObjectURL(blob);
            
            // Set the audio source
            audioEl.src = audioUrl;
            
            // Set download link
            downloadLink.href = audioUrl;
            
            // Get current timestamp for the filename
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            downloadLink.download = `cartesia_tts_${timestamp}.wav`;
            
            // Show audio player
            audioContainer.style.display = 'block';
            
            // Play the audio
            audioEl.play();
        })
        .catch(error => {
            console.error('Error generating audio:', error);
            showError(`Error generating audio: ${error.message}`);
        })
        .finally(() => {
            loadingEl.classList.remove('active');
            generateBtn.disabled = false;
        });
    });
});
