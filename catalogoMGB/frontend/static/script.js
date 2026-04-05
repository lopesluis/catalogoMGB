// Variável global para armazenar todos os metadados
let todosMetadados = [];

// Função para carregar metadados do servidor
function carregarMetadados() {
    fetch('/api/buscar?q=&tipo=all')
        .then(response => response.json())
        .then(data => {
            todosMetadados = data;
            renderizarCards(data, '');
            atualizarStats(data.length, todosMetadados.length, '', 'all');
        })
        .catch(error => {
            console.error('Erro ao carregar metadados:', error);
            document.getElementById('metadataGrid').innerHTML = '<div class="empty">❌ Erro ao carregar metadados. Verifique se o servidor está rodando.</div>';
        });
}

// Função para buscar metadados
function buscarMetadados() {
    const termo = document.getElementById('searchInput').value.trim();
    const tipoFiltro = document.getElementById('filterType').value;
    
    // Construir URL da busca
    let url = `/api/buscar?q=${encodeURIComponent(termo)}&tipo=${tipoFiltro}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            renderizarCards(data, termo);
            atualizarStats(data.length, todosMetadados.length, termo, tipoFiltro);
        })
        .catch(error => {
            console.error('Erro na busca:', error);
            document.getElementById('metadataGrid').innerHTML = '<div class="empty">❌ Erro na busca. Tente novamente.</div>';
        });
}

// Função para limpar a busca
function limparBusca() {
    document.getElementById('searchInput').value = '';
    document.getElementById('filterType').value = 'all';
    
    fetch('/api/buscar?q=&tipo=all')
        .then(response => response.json())
        .then(data => {
            renderizarCards(data, '');
            atualizarStats(data.length, todosMetadados.length, '', 'all');
        })
        .catch(error => {
            console.error('Erro ao limpar busca:', error);
        });
}

// Função para destacar texto
function highlightText(text, termo) {
    if (!termo || termo.trim() === "" || !text) return text;
    try {
        const regex = new RegExp(`(${termo.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<mark class="highlight">$1</mark>');
    } catch(e) {
        return text;
    }
}

// Função para renderizar os cards
function renderizarCards(metadadosLista, termoBusca) {
    const grid = document.getElementById('metadataGrid');
    
    if (!metadadosLista || metadadosLista.length === 0) {
        grid.innerHTML = '<div class="empty">🔍 Nenhum metadado encontrado com os critérios de busca.<br><br>Tente outros termos ou <a href="#" onclick="limparBusca(); return false;">limpar a busca</a>.</div>';
        return;
    }
    
    grid.innerHTML = metadadosLista.map(m => {
        // Aplicar destaque nos textos se houver busca
        const tituloDestacado = termoBusca ? highlightText(m.titulo, termoBusca) : m.titulo;
        const resumoDestacado = termoBusca && m.resumo ? highlightText(m.resumo.substring(0, 250), termoBusca) : (m.resumo ? m.resumo.substring(0, 250) : 'Sem descrição');
        const responsavelDestacado = termoBusca && m.responsavel ? highlightText(m.responsavel, termoBusca) : (m.responsavel || 'Não informado');
        
        // Determinar thumbnail
        const thumbnailUrl = m.thumbnail ? `/thumbnail/${m.thumbnail}` : null;
        
        return `
            <div class="card">
                <div class="thumbnail">
                    ${thumbnailUrl ? `<img src="${thumbnailUrl}" alt="${m.titulo}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22 viewBox=%220 0 100 100%22%3E%3Crect width=%22100%22 height=%22100%22 fill=%22%232d6a4f%22/%3E%3Ctext x=%2250%22 y=%2255%22 text-anchor=%22middle%22 fill=%22white%22 font-size=%2240%22%3E🗺️%3C/text%3E%3C/svg%3E'">` : 
                        '<div class="no-thumbnail">🗺️<br>Sem preview</div>'}
                </div>
                <div class="card-content">
                    <h3>${tituloDestacado || 'Sem título'}</h3>
                    <div class="meta">
                        <span>📅 ${m.data_referencia || 'Data não informada'}</span>
                        <span>🗺️ ${m.escala || 'Escala não informada'}</span>
                        <span>✅ ${m.status || 'Aprovado'}</span>
                    </div>
                    <p class="resumo">${resumoDestacado}${m.resumo && m.resumo.length > 250 ? '...' : ''}</p>
                    ${m.palavras_chave && m.palavras_chave.length ? `
                        <div class="keywords">
                            ${m.palavras_chave.map(kw => `<span class="badge">${termoBusca ? highlightText(kw.trim(), termoBusca) : kw.trim()}</span>`).join('')}
                        </div>
                    ` : ''}
                    ${m.arquivos && m.arquivos.length ? `
                        <div class="files">
                            <strong>📎 Anexos:</strong>
                            ${m.arquivos.map(f => `<a href="/download/${f.nome_salvo}" target="_blank">${f.nome_original}</a>`).join('')}
                        </div>
                    ` : ''}
                    <p class="responsavel">👤 Responsável: ${responsavelDestacado}</p>
                </div>
            </div>
        `;
    }).join('');
}

// Função para atualizar estatísticas
function atualizarStats(resultadosCount, totalCount, termo, tipoFiltro) {
    const statsDiv = document.getElementById('searchStats');
    if (!termo && tipoFiltro === 'all') {
        statsDiv.innerHTML = `<span id="statsText">📊 Mostrando ${resultadosCount} metadado(s) de ${totalCount} no total</span>`;
    } else {
        let filtros = [];
        if (termo) filtros.push(`"${termo}"`);
        if (tipoFiltro !== 'all') {
            const tipoNome = {
                '.shp': 'Shapefile',
                '.gpkg': 'GeoPackage',
                '.tif': 'GeoTIFF',
                '.pdf': 'PDF'
            }[tipoFiltro] || tipoFiltro;
            filtros.push(`tipo: ${tipoNome}`);
        }
        statsDiv.innerHTML = `<span id="statsText">🔍 Encontrados ${resultadosCount} resultado(s) para ${filtros.join(' + ')}. </span><a href="#" onclick="limparBusca(); return false;" class="clear-search">Limpar busca</a>`;
    }
}

// Buscar ao pressionar Enter
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                buscarMetadados();
            }
        });
    }
});