const btnInfo = document.getElementById('btn-info');
const btnDl = document.getElementById('btn-dl');
const urlIn = document.getElementById('url');
const browserIn = document.getElementById('browser');
const result = document.getElementById('result');
const error = document.getElementById('error');

btnInfo.onclick = async () => {
    error.style.display = 'none';
    result.style.display = 'none';
    btnInfo.disabled = true;
    btnInfo.textContent = '...ing';

    try {
        const res = await fetch('/api/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlIn.value, browser: browserIn.value })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Falha');

        document.getElementById('res-title').textContent = data.title;
        document.getElementById('res-thumb').src = data.thumbnail;
        result.style.display = 'block';
    } catch (e) {
        error.textContent = e.message;
        error.style.display = 'block';
    } finally {
        btnInfo.disabled = false;
        btnInfo.textContent = 'Analisar';
    }
};

btnDl.onclick = async () => {
    btnDl.disabled = true;
    btnDl.textContent = 'Baixando...';
    try {
        const res = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlIn.value, browser: browserIn.value })
        });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Erro');
        }
        alert('Download concluído na pasta Downloads!');
    } catch (e) {
        alert(e.message);
    } finally {
        btnDl.disabled = false;
        btnDl.textContent = 'Salvar Mídia';
    }
};
