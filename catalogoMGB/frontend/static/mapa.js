// Inicialização do mapa Leaflet
let mapa;

function initMapa(elementId, coordenadasIniciais = [-14.235, -51.925], zoom = 4) {
    // Verificar se o Leaflet está carregado
    if (typeof L === 'undefined') {
        console.error('Leaflet não carregado');
        return;
    }
    
    mapa = L.map(elementId).setView(coordenadasIniciais, zoom);
    
    // Adicionar tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; CartoDB',
        subdomains: 'abcd',
        maxZoom: 19,
        minZoom: 3
    }).addTo(mapa);
    
    return mapa;
}

function carregarGeoJSON(url, cor = '#2d6a4f') {
    if (!mapa) return;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            // Limpar camadas anteriores (exceto tile layer)
            mapa.eachLayer((layer) => {
                if (layer !== mapa._layers[Object.keys(mapa._layers)[0]]) {
                    if (layer.options && layer.options.pane !== 'tilePane') {
                        mapa.removeLayer(layer);
                    }
                }
            });
            
            // Adicionar nova camada
            const geojsonLayer = L.geoJSON(data, {
                style: {
                    color: cor,
                    weight: 2,
                    fillColor: cor,
                    fillOpacity: 0.3
                },
                pointToLayer: function(feature, latlng) {
                    return L.circleMarker(latlng, {
                        radius: 6,
                        fillColor: cor,
                        color: '#fff',
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8
                    });
                },
                onEachFeature: function(feature, layer) {
                    if (feature.properties) {
                        let popupContent = '<b>Informações</b><br>';
                        for (let [key, value] of Object.entries(feature.properties)) {
                            if (value && key !== 'type') {
                                popupContent += `<b>${key}:</b> ${value}<br>`;
                            }
                        }
                        layer.bindPopup(popupContent);
                    }
                }
            }).addTo(mapa);
            
            // Ajustar zoom para mostrar todos os dados
            if (geojsonLayer.getBounds().isValid()) {
                mapa.fitBounds(geojsonLayer.getBounds());
            }
        })
        .catch(error => {
            console.error('Erro ao carregar GeoJSON:', error);
        });
}