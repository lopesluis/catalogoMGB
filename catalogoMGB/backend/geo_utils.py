"""
Utilitários para conversão de arquivos geoespaciais para GeoJSON
Com suporte a conversão de projeção para WGS84 (Leaflet)
"""
import os
import json
import csv
import zipfile
import tempfile
import shutil


def converter_para_geojson(caminho_arquivo, nome_arquivo):
    """Converte diversos formatos para GeoJSON (sempre em WGS84)"""
    
    extensao = nome_arquivo.lower().split('.')[-1]
    
    if extensao == 'zip':
        return _converter_zip(caminho_arquivo)
    elif extensao == 'shp':
        return _converter_shapefile(caminho_arquivo, nome_arquivo)
    elif extensao == 'geojson':
        return _converter_geojson(caminho_arquivo)
    elif extensao == 'gpkg':
        return _converter_geopackage(caminho_arquivo)
    elif extensao == 'csv':
        return _converter_csv(caminho_arquivo)
    elif extensao in ['kml', 'kmz']:
        return _converter_kml(caminho_arquivo, extensao)
    else:
        return None, f"Formato não suportado: .{extensao}"


def _converter_zip(caminho_zip):
    """Descompacta ZIP e procura por arquivos geoespaciais"""
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        with zipfile.ZipFile(caminho_zip, 'r') as zf:
            zf.extractall(temp_dir)
        
        print(f"ZIP descompactado. Arquivos: {os.listdir(temp_dir)}")
        
        arquivos_encontrados = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                ext = file.lower().split('.')[-1] if '.' in file else ''
                if ext in ['shp', 'geojson', 'gpkg', 'kml', 'kmz', 'csv']:
                    arquivos_encontrados.append({
                        'caminho': os.path.join(root, file),
                        'nome': file,
                        'extensao': ext
                    })
                    print(f"Encontrado: {file}")
        
        ordem_prioridade = ['shp', 'geojson', 'gpkg', 'kml', 'kmz', 'csv']
        arquivo_escolhido = None
        
        for ext in ordem_prioridade:
            for arq in arquivos_encontrados:
                if arq['extensao'] == ext:
                    arquivo_escolhido = arq
                    break
            if arquivo_escolhido:
                break
        
        if not arquivo_escolhido:
            return None, "Nenhum arquivo geoespacial encontrado no ZIP"
        
        print(f"Convertendo: {arquivo_escolhido['nome']}")
        
        if arquivo_escolhido['extensao'] == 'shp':
            return _converter_shapefile(arquivo_escolhido['caminho'], arquivo_escolhido['nome'])
        elif arquivo_escolhido['extensao'] == 'geojson':
            return _converter_geojson(arquivo_escolhido['caminho'])
        elif arquivo_escolhido['extensao'] == 'gpkg':
            return _converter_geopackage(arquivo_escolhido['caminho'])
        elif arquivo_escolhido['extensao'] in ['kml', 'kmz']:
            return _converter_kml(arquivo_escolhido['caminho'], arquivo_escolhido['extensao'])
        elif arquivo_escolhido['extensao'] == 'csv':
            return _converter_csv(arquivo_escolhido['caminho'])
        
        return None, "Falha na conversão"
        
    except Exception as e:
        return None, f"Erro: {str(e)}"
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def _reprojetar_para_wgs84(coordenadas, proj_origem):
    """
    Converte coordenadas de qualquer projeção para WGS84 (latitude/longitude)
    proj_origem: código EPSG da projeção original (ex: 31983 para UTM 23S)
    """
    if proj_origem is None or proj_origem == 'EPSG:4326':
        return coordenadas
    
    try:
        from pyproj import Transformer
        
        # Criar transformador
        transformer = Transformer.from_crs(proj_origem, "EPSG:4326", always_xy=True)
        
        # Converter cada coordenada
        novas_coords = []
        for coord in coordenadas:
            # coord pode ser [x, y] ou [x, y, z]
            x, y = coord[0], coord[1]
            lon, lat = transformer.transform(x, y)
            novas_coords.append([lon, lat])
        
        return novas_coords
        
    except Exception as e:
        print(f"Erro na reprojeção: {e}")
        return coordenadas


def _detectar_projecao(caminho_shp):
    """Tenta detectar a projeção do shapefile a partir do arquivo .prj"""
    prj_path = caminho_shp.replace('.shp', '.prj')
    
    if not os.path.exists(prj_path):
        return None
    
    try:
        with open(prj_path, 'r') as f:
            prj_text = f.read()
        
        # Mapeamento básico de projeções comuns no Brasil
        mapeamento = {
            'SIRGAS 2000 / UTM zone 22S': 'EPSG:31982',
            'SIRGAS 2000 / UTM zone 23S': 'EPSG:31983',
            'SIRGAS 2000 / UTM zone 24S': 'EPSG:31984',
            'SIRGAS 2000 / UTM zone 25S': 'EPSG:31985',
            'SIRGAS 2000': 'EPSG:4674',
            'WGS 84': 'EPSG:4326',
            'SAD69 / UTM zone 22S': 'EPSG:29192',
            'SAD69 / UTM zone 23S': 'EPSG:29193',
            'SAD69 / UTM zone 24S': 'EPSG:29194',
            'SAD69 / UTM zone 25S': 'EPSG:29195',
        }
        
        for nome, epsg in mapeamento.items():
            if nome.lower() in prj_text.lower():
                print(f"Projeção detectada: {nome} ({epsg})")
                return epsg
        
        return None
        
    except:
        return None


def _converter_shapefile(caminho_shp, nome_arquivo):
    """Converte Shapefile para GeoJSON com reprojeção para WGS84"""
    try:
        import shapefile
        
        if not os.path.exists(caminho_shp):
            return None, f"Arquivo não encontrado"
        
        # Detectar projeção original
        proj_origem = _detectar_projecao(caminho_shp)
        print(f"Projeção original: {proj_origem}")
        
        reader = shapefile.Reader(caminho_shp)
        
        if reader.numRecords == 0:
            return None, "Shapefile vazio"
        
        # Obter nomes dos campos
        campos = [campo[0] for campo in reader.fields[1:]]  # Pula o primeiro campo (DeletionFlag)
        print(f"Campos encontrados: {len(campos)}")
        
        features = []
        for shape_rec in reader.shapeRecords():
            # Extrair geometria
            geometry = shape_rec.shape.__geo_interface__
            
            # Converter coordenadas para WGS84 se necessário
            if proj_origem and proj_origem != 'EPSG:4326':
                if geometry['type'] == 'Polygon':
                    novas_coords = []
                    for ring in geometry['coordinates']:
                        novas_coords.append(_reprojetar_para_wgs84(ring, proj_origem))
                    geometry['coordinates'] = novas_coords
                    
                elif geometry['type'] == 'MultiPolygon':
                    novas_coords = []
                    for polygon in geometry['coordinates']:
                        novo_polygon = []
                        for ring in polygon:
                            novo_polygon.append(_reprojetar_para_wgs84(ring, proj_origem))
                        novas_coords.append(novo_polygon)
                    geometry['coordinates'] = novas_coords
                    
                elif geometry['type'] == 'Point':
                    coords = _reprojetar_para_wgs84([geometry['coordinates']], proj_origem)
                    geometry['coordinates'] = coords[0]
                    
                elif geometry['type'] == 'LineString':
                    geometry['coordinates'] = _reprojetar_para_wgs84(geometry['coordinates'], proj_origem)
            
            # Construir propriedades corretamente
            properties = {}
            for i, campo in enumerate(campos):
                valor = shape_rec.record[i]
                # Converter bytes para string se necessário
                if isinstance(valor, bytes):
                    valor = valor.decode('utf-8', errors='ignore')
                properties[campo] = valor
            
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": properties
            })
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        print(f"Shapefile convertido! {len(features)} features")
        return geojson, None
        
    except ImportError:
        return None, "Instale pyshp: pip install pyshp"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"Erro: {str(e)}"


def _converter_geojson(caminho_geojson):
    """Lê GeoJSON e verifica se está em WGS84"""
    try:
        with open(caminho_geojson, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
        
        # GeoJSON já deve estar em WGS84
        return geojson, None
        
    except Exception as e:
        return None, f"Erro: {str(e)}"


def _converter_geopackage(caminho_gpkg):
    """Converte GeoPackage para GeoJSON"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(caminho_gpkg)
        cursor = conn.cursor()
        
        # Tentar obter extensão (bounding box)
        cursor.execute("SELECT min_x, min_y, max_x, max_y FROM gpkg_contents LIMIT 1")
        bbox = cursor.fetchone()
        
        if bbox:
            # Criar um retângulo com a extensão
            min_x, min_y, max_x, max_y = bbox
            
            # Converter para WGS84 se necessário (simplificado)
            features = [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [min_x, min_y],
                        [max_x, min_y],
                        [max_x, max_y],
                        [min_x, max_y],
                        [min_x, min_y]
                    ]]
                },
                "properties": {"name": "Extensão do GeoPackage"}
            }]
        else:
            features = []
        
        conn.close()
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return geojson, None
        
    except Exception as e:
        return None, f"Erro: {str(e)}"


def _converter_csv(caminho_csv):
    """Converte CSV para GeoJSON (pontos)"""
    try:
        colunas_lat = ['lat', 'latitude', 'y', 'northing']
        colunas_lon = ['lon', 'lng', 'longitude', 'long', 'x', 'easting']
        
        features = []
        
        with open(caminho_csv, 'r', encoding='utf-8') as f:
            primeira_linha = f.readline()
            f.seek(0)
            
            delimiter = ';' if ';' in primeira_linha else ',' if ',' in primeira_linha else '\t'
            reader = csv.DictReader(f, delimiter=delimiter)
            colunas = reader.fieldnames
            
            col_lat = col_lon = None
            for col in colunas:
                col_lower = col.lower()
                for lat_name in colunas_lat:
                    if lat_name in col_lower:
                        col_lat = col
                        break
                for lon_name in colunas_lon:
                    if lon_name in col_lower:
                        col_lon = col
                        break
            
            if not col_lat or not col_lon:
                return None, "CSV sem coordenadas"
            
            for row in reader:
                try:
                    lat = float(row[col_lat].replace(',', '.'))
                    lon = float(row[col_lon].replace(',', '.'))
                    
                    props = {k: v for k, v in row.items() if k not in [col_lat, col_lon]}
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "properties": props
                    })
                except:
                    continue
        
        if not features:
            return None, "Nenhum ponto válido"
        
        geojson = {"type": "FeatureCollection", "features": features}
        return geojson, None
        
    except Exception as e:
        return None, f"Erro: {str(e)}"


def _converter_kml(caminho, extensao):
    """Converte KML para GeoJSON"""
    try:
        import xml.etree.ElementTree as ET
        
        if extensao == 'kmz':
            import zipfile
            with zipfile.ZipFile(caminho, 'r') as zf:
                for nome in zf.namelist():
                    if nome.lower().endswith('.kml'):
                        with zf.open(nome) as kml_file:
                            kml_content = kml_file.read().decode('utf-8')
                        break
                else:
                    return None, "Nenhum KML encontrado"
        else:
            with open(caminho, 'r', encoding='utf-8') as f:
                kml_content = f.read()
        
        kml_content = kml_content.replace('kml:', '').replace(':', '')
        root = ET.fromstring(kml_content)
        features = []
        
        for placemark in root.findall('.//Placemark'):
            nome_elem = placemark.find('name')
            nome = nome_elem.text if nome_elem is not None else "Sem nome"
            
            point = placemark.find('.//Point')
            if point is not None:
                coords_elem = point.find('coordinates')
                if coords_elem is not None and coords_elem.text:
                    coords = coords_elem.text.strip().split(',')
                    if len(coords) >= 2:
                        lon, lat = float(coords[0]), float(coords[1])
                        features.append({
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "properties": {"name": nome}
                        })
        
        if not features:
            return None, "Nenhum ponto encontrado"
        
        geojson = {"type": "FeatureCollection", "features": features}
        return geojson, None
        
    except Exception as e:
        return None, f"Erro: {str(e)}"


def obter_bounding_box_geojson(norte, sul, leste, oeste):
    """Cria GeoJSON com bounding box"""
    if norte is None or sul is None or leste is None or oeste is None:
        return None
    
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [oeste, sul], [leste, sul],
                    [leste, norte], [oeste, norte],
                    [oeste, sul]
                ]]
            },
            "properties": {"name": "Extensão geográfica"}
        }]
    }
    
    return geojson