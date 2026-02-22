// Configuração da URL Base da API (Mude a 'URL_DO_RENDER_AQUI' quando hospedar o backend)
const API_BASE = (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')
    ? ''
    : 'https://downloader-nqdv.onrender.com';

const btnInfo = document.getElementById('btn-info');
const btnDl = document.getElementById('btn-dl');
const urlIn = document.getElementById('url');
const browserIn = document.getElementById('browser');
const result = document.getElementById('result');
const error = document.getElementById('error');

// Função auxiliar para forçar o download no navegador com janela "Salvar Como"
async function promptNativeDownload(fileUrl, fileName) {
    try {
        if (window.showSaveFilePicker) {
            // Tenta usar a API moderna para pedir o local de salvamento
            const response = await fetch(fileUrl);
            const blob = await response.blob();

            const handle = await window.showSaveFilePicker({
                suggestedName: fileName,
                types: [{
                    description: 'Media File',
                    accept: {
                        'video/mp4': ['.mp4'],
                        'audio/mpeg': ['.mp3'],
                        'video/webm': ['.webm']
                    }
                }]
            });
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
            return true; // Sucesso com dialogo
        }
    } catch (err) {
        if (err.name !== 'AbortError') {
            console.error('Erro no showSaveFilePicker:', err);
        }
        return false; // Usuário cancelou ou deu erro, não faz o fallback automático
    }

    // Fallback silencioso (baixa direto na pasta Downloads do navegador) para mobile/safari
    const a = document.createElement('a');
    a.href = fileUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    return true;
}

btnInfo.onclick = async () => {
    error.style.display = 'none';
    result.style.display = 'none';

    // Cloud Environment Security Check for Cookies
    const isCloud = API_BASE !== '';
    if (isCloud && browserIn.value !== 'none') {
        alert("🔒 Limitação de Nuvem Detectada:\n\nComo o sistema agora está rodando na Vercel/Render (nas Nuvens), o servidor não tem acesso físico ao seu computador ou celular para ler os cookies locais do Chrome/Edge.\n\nA opção 'Usar Chrome/Edge' só funciona quando você roda o arquivo `app.py` localmente no seu PC. Para vídeos privados na nuvem, use o Padrão.");
        browserIn.value = 'none';
        return;
    }

    btnInfo.disabled = true;
    btnInfo.textContent = '...ing';

    try {
        const res = await fetch(`${API_BASE}/api/info`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlIn.value, browser: browserIn.value })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Falha');

        document.getElementById('res-title').textContent = data.title;
        document.getElementById('res-thumb').src = data.thumbnail;

        // Fill Quality Selector
        const qualitySel = document.getElementById('quality');
        qualitySel.innerHTML = '';
        data.formats.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.id;
            opt.textContent = `${f.type} [${f.ext}] ${f.res} - ${f.note}`;
            qualitySel.appendChild(opt);
        });

        result.style.display = 'block';
    } catch (e) {
        error.textContent = e.message;
        error.style.display = 'block';
    } finally {
        btnInfo.disabled = false;
        btnInfo.textContent = 'Analisar Link';
    }
};

btnDl.onclick = async () => {
    btnDl.disabled = true;
    btnDl.innerHTML = 'Baixando...';

    // UI Elements
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = 'Iniciando extração...';

    const activeUrl = urlIn.value;

    // Start Polling Context
    let pollInterval = setInterval(async () => {
        try {
            const pres = await fetch(`${API_BASE}/api/progress?url=${encodeURIComponent(activeUrl)}`);
            if (pres.ok) {
                const pdata = await pres.json();
                let pct = pdata.progress;
                progressText.textContent = pct;

                // If it looks like a number %, apply to width
                if (pct.includes('%')) {
                    progressBar.style.width = pct;
                }
            }
        } catch (e) { console.error('Poll error', e); }
    }, 500);

    try {
        const res = await fetch(`${API_BASE}/api/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: activeUrl,
                browser: browserIn.value,
                format_id: document.getElementById('quality').value
            })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Erro ao baixar');
        }

        progressBar.style.width = '100%';
        progressText.textContent = 'Entregando arquivo...';

        // Trigger file download to user's PC
        const fullUrl = `${API_BASE}${data.url}`;
        progressText.textContent = 'Aguardando local para salvar...';
        const saved = await promptNativeDownload(fullUrl, data.filename);
        if (saved) {
            progressText.textContent = 'Salvo com sucesso!';
            setTimeout(() => alert(`O arquivo [${data.filename}] foi salvo no seu computador!`), 500);
        } else {
            progressText.textContent = 'Download cancelado pelo usuário.';
        }

    } catch (e) {
        progressText.textContent = 'Falhou!';
        progressBar.style.backgroundColor = 'red';
        alert(e.message);
    } finally {
        clearInterval(pollInterval);
        btnDl.disabled = false;
        btnDl.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 5px; vertical-align: middle;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg> Salvar Arquivo (Vídeo)`;
    }
};

const btnMp3 = document.getElementById('btn-mp3');
btnMp3.onclick = async () => {
    btnMp3.disabled = true;
    btnMp3.innerHTML = 'Convertendo MP3...';
    btnDl.disabled = true; // disable video button too

    // UI Elements
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = 'Iniciando extração de áudio...';

    const activeUrl = urlIn.value;

    // Start Polling Context
    let pollInterval = setInterval(async () => {
        try {
            const pres = await fetch(`${API_BASE}/api/progress?url=${encodeURIComponent(activeUrl)}`);
            if (pres.ok) {
                const pdata = await pres.json();
                let pct = pdata.progress;
                progressText.textContent = pct;
                if (pct.includes('%')) {
                    progressBar.style.width = pct;
                }
            }
        } catch (e) { /* ignore */ }
    }, 500);

    try {
        const res = await fetch(`${API_BASE}/api/download_mp3`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: activeUrl,
                browser: browserIn.value
            })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Erro ao converter MP3');
        }

        progressBar.style.width = '100%';
        progressText.textContent = 'Entregando áudio...';

        // Trigger file download to user's PC
        const fullUrl = `${API_BASE}${data.url}`;
        progressText.textContent = 'Aguardando local para salvar áudio...';
        const saved = await promptNativeDownload(fullUrl, data.filename);
        if (saved) {
            progressText.textContent = 'Salvo com sucesso!';
            setTimeout(() => alert(`O áudio [${data.filename}] foi salvo no seu computador!`), 500);
        } else {
            progressText.textContent = 'Download cancelado pelo usuário.';
        }

    } catch (e) {
        progressText.textContent = 'Falhou!';
        progressBar.style.backgroundColor = 'red';
        alert(e.message);
    } finally {
        clearInterval(pollInterval);
        btnMp3.disabled = false;
        btnDl.disabled = false;
        btnMp3.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 5px; vertical-align: middle;"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg> Baixar Apenas Áudio (MP3)`;
    }
};
