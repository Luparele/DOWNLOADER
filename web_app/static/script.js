document.addEventListener('DOMContentLoaded', () => {
    const fetchBtn = document.getElementById('fetch-btn');
    const downloadBtn = document.getElementById('download-btn');
    const urlInput = document.getElementById('video-url');
    const errorMsg = document.getElementById('error-msg');
    const resultsSection = document.getElementById('results-section');
    const fetchLoader = document.getElementById('fetch-loader');
    const downloadLoader = document.getElementById('download-loader');
    const downloadStatus = document.getElementById('download-status');
    const qualitySelector = document.getElementById('quality-selector');
    const browserSelector = document.getElementById('browser-selector');
    const openFolderBtn = document.getElementById('open-folder-btn');

    let currentVideoData = null;

    // Define API backend path depending on the environment. 
    // Uses relative path so it works locally and in production.
    const API_BASE = '';

    const showError = (msg) => {
        errorMsg.textContent = msg;
        errorMsg.classList.remove('hidden');
        resultsSection.classList.add('hidden');
    };

    const hideError = () => {
        errorMsg.classList.add('hidden');
    };

    const formatDuration = (seconds) => {
        if (!seconds) return '';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    fetchBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            showError("Por favor, insira um link válido de vídeo.");
            return;
        }

        hideError();
        fetchBtn.disabled = true;
        fetchBtn.querySelector('span').style.opacity = '0';
        fetchLoader.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        openFolderBtn.classList.add('hidden'); // Ocultar botão de pasta ao buscar novo

        try {
            const browserId = browserSelector.value;
            const response = await fetch(`${API_BASE}/api/info`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, browser: browserId })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Falha ao buscar informações do vídeo.");
            }

            currentVideoData = url;

            // Populate UI
            document.getElementById('video-title').textContent = data.title || "Título Desconhecido";
            document.getElementById('video-thumbnail').src = data.thumbnail || "";
            document.getElementById('video-duration').textContent = formatDuration(data.duration);

            const platformName = data.platform || "unknown";
            document.getElementById('video-platform').textContent = platformName.charAt(0).toUpperCase() + platformName.slice(1);

            // Populate quality options
            qualitySelector.innerHTML = '<option value="best">Melhor Qualidade Automática</option>';
            if (data.formats && data.formats.length > 0) {
                data.formats.forEach(f => {
                    const option = document.createElement('option');
                    option.value = f.format_id;
                    const sizeMB = f.filesize ? ` (~${(f.filesize / 1024 / 1024).toFixed(1)}MB)` : '';
                    option.textContent = `${f.resolution} - ${f.ext}${sizeMB}`;
                    qualitySelector.appendChild(option);
                });
                qualitySelector.classList.remove('hidden');
            } else {
                qualitySelector.classList.add('hidden');
            }

            // Show results
            resultsSection.classList.remove('hidden');
            downloadStatus.classList.add('hidden');

        } catch (err) {
            showError(err.message);
        } finally {
            fetchBtn.disabled = false;
            fetchBtn.querySelector('span').style.opacity = '1';
            fetchLoader.classList.add('hidden');
        }
    });

    downloadBtn.addEventListener('click', async () => {
        if (!currentVideoData) return;

        downloadBtn.disabled = true;
        downloadBtn.querySelector('span').style.opacity = '0';
        downloadLoader.classList.remove('hidden');
        downloadStatus.classList.add('hidden');

        try {
            const formatId = qualitySelector.value || 'best';
            const browserId = browserSelector.value;

            const response = await fetch(`${API_BASE}/api/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: currentVideoData, format_id: formatId, browser: browserId })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Falha ao iniciar download");
            }

            const taskId = data.task_id;
            const progressContainer = document.getElementById('progress-container');
            const progressText = document.getElementById('progress-text');
            const progressSpeed = document.getElementById('progress-speed');
            const progressBarFill = document.getElementById('progress-bar-fill');
            const progressEta = document.getElementById('progress-eta');
            
            progressContainer.classList.remove('hidden');
            
            let downloadComplete = false;
            let finalData = null;
            
            // Poll for progress updates
            while (!downloadComplete) {
                await new Promise(r => setTimeout(r, 1000));
                
                const progRes = await fetch(`${API_BASE}/api/progress/${taskId}`);
                if (!progRes.ok) continue;
                
                const progData = await progRes.json();
                
                if (progData.status === 'error') {
                    throw new Error(progData.error || "Ocorreu um erro no servidor durante o download");
                }
                
                if (progData.status === 'downloading') {
                    progressText.textContent = `[download] ${progData.percent}`;
                    progressSpeed.textContent = progData.speed;
                    progressEta.textContent = `ETA ${progData.eta}`;
                    if (progData.percent) {
                        progressBarFill.style.width = progData.percent;
                    }
                } else if (progData.status === 'processing') {
                    progressText.textContent = `Processando arquivo final (isso pode demorar).../`;
                    progressSpeed.textContent = '';
                    progressEta.textContent = 'Mesclando áudio e vídeo...';
                    progressBarFill.style.width = '100%';
                } else if (progData.status === 'success') {
                    downloadComplete = true;
                    finalData = progData;
                }
            }

            progressContainer.classList.add('hidden');
            downloadStatus.textContent = `Sucesso! O vídeo está pronto.`;
            downloadStatus.classList.remove('hidden');
            downloadStatus.style.borderColor = 'rgba(0, 243, 255, 0.3)';
            downloadStatus.style.color = 'var(--secondary)';
            downloadStatus.style.background = 'rgba(0, 243, 255, 0.1)';

            // Set up open folder button
            openFolderBtn.innerHTML = `<span>Abrir a pasta do arquivo</span>`;
            openFolderBtn.onclick = async () => {
                try {
                    await fetch(`${API_BASE}/api/open-folder?path=${encodeURIComponent(finalData.file)}`);
                } catch (e) {
                    console.error("Erro ao abrir pasta:", e);
                }
            };
            openFolderBtn.classList.remove('hidden');

        } catch (err) {
            downloadStatus.textContent = `Erro: ${err.message}`;
            downloadStatus.classList.remove('hidden');
            downloadStatus.style.borderColor = 'rgba(255, 51, 102, 0.3)';
            downloadStatus.style.color = 'var(--error)';
            downloadStatus.style.background = 'rgba(255, 51, 102, 0.1)';
        } finally {
            downloadBtn.disabled = false;
            downloadBtn.querySelector('span').style.opacity = '1';
            downloadLoader.classList.add('hidden');
        }
    });

    // Listender for folder opening is now handled by onclick in download block
});
