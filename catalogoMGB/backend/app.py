from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from database import db, User, Metadado
from auth import verificar_login, criar_usuario_inicial
from upload import salvar_arquivo, salvar_thumbnail, gerar_thumbnail_from_file
from workflow import StatusMetadado
import os
from datetime import datetime
import json

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
app.config['SECRET_KEY'] = 'chave-secreta-catalogo-mgb'

# Caminho absoluto para o banco de dados
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_db_path = os.path.join(_base_dir, 'data', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{_db_path}'

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['THUMBNAIL_FOLDER'] = 'thumbnails'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Inicializar extensões
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Criar pastas necessárias
os.makedirs('uploads', exist_ok=True)
os.makedirs('thumbnails', exist_ok=True)
os.makedirs(os.path.dirname(_db_path), exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==============================================
# PÁGINAS PRINCIPAIS
# ==============================================

@app.route('/')
def index():
    metadados = Metadado.query.filter_by(status=StatusMetadado.APROVADO.value).order_by(Metadado.data_criacao.desc()).all()
    return render_template('index.html', metadados=metadados, usuario=current_user if current_user.is_authenticated else None)

@app.route('/metadado/<int:id>')
def visualizar_publico(id):
    metadado = Metadado.query.get_or_404(id)
    if metadado.status != StatusMetadado.APROVADO.value:
        if not current_user.is_authenticated or current_user.papel != 'admin':
            flash('Este metadado não está disponível para visualização pública', 'warning')
            return redirect(url_for('index'))
     # PRECISA PASSAR O USUARIO
    return render_template('visualizar_publico.html', metadado=metadado, usuario=current_user if current_user.is_authenticated else None)

@app.route('/api/buscar')
def buscar_metadados():
    termo = request.args.get('q', '').strip().lower()
    tipo_filtro = request.args.get('tipo', 'all')
    categoria_filtro = request.args.get('categoria', 'all')
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 12
    
    query = Metadado.query.filter_by(status=StatusMetadado.APROVADO.value)
    
    # Filtrar por tipo de arquivo
    if tipo_filtro != 'all':
        query = query.filter(Metadado.arquivos_json.like(f'%{tipo_filtro}%'))
    
    # Filtrar por categoria temática
    if categoria_filtro != 'all':
        query = query.filter(Metadado.categorias_tematicas.like(f'%{categoria_filtro}%'))
    
    # Filtrar por termo de busca
    if termo:
        query = query.filter(
            db.or_(
                Metadado.titulo.ilike(f'%{termo}%'),
                Metadado.resumo.ilike(f'%{termo}%'),
                Metadado.palavras_chave.ilike(f'%{termo}%'),
                Metadado.responsavel.ilike(f'%{termo}%')
            )
        )
    
    # Total de resultados (para paginação)
    total = query.count()
    
    # Paginação
    query = query.order_by(Metadado.data_criacao.desc())
    query = query.offset((pagina - 1) * por_pagina).limit(por_pagina)
    metadados = query.all()
    
    # Converter para JSON
    resultados = []
    for m in metadados:
        resultados.append({
            'id': m.id,
            'titulo': m.titulo,
            'resumo': m.resumo,
            'palavras_chave': m.palavras_chave.split(',') if m.palavras_chave else [],
            'data_referencia': m.data_referencia,
            'responsavel': m.responsavel,
            'thumbnail': m.thumbnail,
            'categorias_tematicas': m.categorias_lista
        })
    
    return jsonify({
        'total': total,
        'pagina': pagina,
        'por_pagina': por_pagina,
        'total_paginas': (total + por_pagina - 1) // por_pagina,
        'resultados': resultados
    })
@app.route('/api/estatisticas')
def estatisticas():
    """API para estatísticas do dashboard"""
    from sqlalchemy import func
    
    # Totais por status
    total_metadados = Metadado.query.count()
    aprovados = Metadado.query.filter_by(status=StatusMetadado.APROVADO.value).count()
    pendentes = Metadado.query.filter_by(status=StatusMetadado.PENDENTE.value).count()
    rejeitados = Metadado.query.filter_by(status=StatusMetadado.REJEITADO.value).count()
    
    # Metadados por mês
    meses = db.session.query(
        func.strftime('%Y-%m', Metadado.data_criacao).label('mes'),
        func.count(Metadado.id).label('total')
    ).group_by('mes').order_by('mes').all()
    
    meses_lista = [{'mes': m.mes, 'total': m.total} for m in meses]
    
    # Categorias mais usadas
    categorias_count = {}
    todos_metadados = Metadado.query.all()
    for m in todos_metadados:
        for cat in m.categorias_lista:
            categorias_count[cat] = categorias_count.get(cat, 0) + 1
    
    categorias_lista = [{'categoria': k, 'total': v} for k, v in sorted(categorias_count.items(), key=lambda x: x[1], reverse=True)]
    
    # Atividade por usuário
    usuarios = db.session.query(
        User.id, User.nome, User.papel,
        func.count(Metadado.id).label('total')
    ).outerjoin(Metadado, User.id == Metadado.criado_por_id).group_by(User.id).all()
    
    usuarios_lista = [{'id': u.id, 'nome': u.nome, 'papel': u.papel, 'total': u.total} for u in usuarios]
    
    return jsonify({
        'total_metadados': total_metadados,
        'aprovados': aprovados,
        'pendentes': pendentes,
        'rejeitados': rejeitados,
        'meses': meses_lista,
        'categorias': categorias_lista,
        'usuarios': usuarios_lista
    })
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    return render_template('dashboard.html')
@app.route('/exportar_xml/<int:id>')  # Sem @login_required
def exportar_xml(id):
    """Exporta metadado no formato XML (ISO 19139) - Público"""
    metadado = Metadado.query.get_or_404(id)
    
    # Só permite exportar se aprovado (ou admin pode exportar pendentes?)
    if metadado.status != StatusMetadado.APROVADO.value:
        # Se não for admin, não pode exportar pendente/rejeitado
        if not current_user.is_authenticated or current_user.papel != 'admin':
            flash('Metadado não disponível para exportação', 'warning')
            return redirect(url_for('index'))
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xsi:schemaLocation="http://www.isotc211.org/2005/gmd http://www.isotc211.org/2005/schema/gmd.xsd">
    
    <!-- Identificação -->
    <gmd:fileIdentifier>
        <gco:CharacterString>MGB_{metadado.id}</gco:CharacterString>
    </gmd:fileIdentifier>
    
    <gmd:language>
        <gmd:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/" codeListValue="por">Português</gmd:LanguageCode>
    </gmd:language>
    
    <gmd:characterSet>
        <gmd:MD_CharacterSetCode codeListValue="utf8">UTF-8</gmd:MD_CharacterSetCode>
    </gmd:characterSet>
    
    <gmd:hierarchyLevel>
        <gmd:MD_ScopeCode codeListValue="dataset">Conjunto de dados</gmd:MD_ScopeCode>
    </gmd:hierarchyLevel>
    
    <gmd:contact>
        <gmd:CI_ResponsibleParty>
            <gmd:organisationName>
                <gco:CharacterString>{metadado.responsavel or 'Não informado'}</gco:CharacterString>
            </gmd:organisationName>
            <gmd:contactInfo>
                <gmd:CI_Contact>
                    <gmd:address>
                        <gmd:CI_Address>
                            <gmd:electronicMailAddress>
                                <gco:CharacterString>{metadado.contato_metadados or 'Não informado'}</gco:CharacterString>
                            </gmd:electronicMailAddress>
                        </gmd:CI_Address>
                    </gmd:address>
                </gmd:CI_Contact>
            </gmd:contactInfo>
            <gmd:role>
                <gmd:CI_RoleCode codeListValue="pointOfContact">Ponto de contato</gmd:CI_RoleCode>
            </gmd:role>
        </gmd:CI_ResponsibleParty>
    </gmd:contact>
    
    <gmd:dateStamp>
        <gco:Date>{datetime.now().strftime('%Y-%m-%d')}</gco:Date>
    </gmd:dateStamp>
    
    <gmd:metadataStandardName>
        <gco:CharacterString>ISO 19115:2003 - Perfil MGB</gco:CharacterString>
    </gmd:metadataStandardName>
    
    <gmd:metadataStandardVersion>
        <gco:CharacterString>2.0</gco:CharacterString>
    </gmd:metadataStandardVersion>
    
    <!-- Conjunto de dados -->
    <gmd:identificationInfo>
        <gmd:MD_DataIdentification>
            <gmd:citation>
                <gmd:CI_Citation>
                    <gmd:title>
                        <gco:CharacterString>{metadado.titulo}</gco:CharacterString>
                    </gmd:title>
                    <gmd:date>
                        <gmd:CI_Date>
                            <gmd:date>
                                <gco:Date>{metadado.data_referencia or datetime.now().strftime('%Y-%m-%d')}</gco:Date>
                            </gmd:date>
                            <gmd:dateType>
                                <gmd:CI_DateTypeCode codeListValue="publication">Publicação</gmd:CI_DateTypeCode>
                            </gmd:dateType>
                        </gmd:CI_Date>
                    </gmd:date>
                </gmd:CI_Citation>
            </gmd:citation>
            
            <gmd:abstract>
                <gco:CharacterString>{metadado.resumo or ''}</gco:CharacterString>
            </gmd:abstract>
            
            <gmd:language>
                <gmd:LanguageCode codeListValue="por">Português</gmd:LanguageCode>
            </gmd:language>
            
            <gmd:topicCategory>
                <gmd:MD_TopicCategoryCode>{metadado.categorias_lista[0] if metadado.categorias_lista else 'environment'}</gmd:MD_TopicCategoryCode>
            </gmd:topicCategory>
            
            <gmd:extent>
                <gmd:EX_Extent>
                    <gmd:geographicElement>
                        <gmd:EX_GeographicBoundingBox>
                            <gmd:westBoundLongitude>
                                <gco:Decimal>{metadado.extensao_oeste or -180}</gco:Decimal>
                            </gmd:westBoundLongitude>
                            <gmd:eastBoundLongitude>
                                <gco:Decimal>{metadado.extensao_leste or 180}</gco:Decimal>
                            </gmd:eastBoundLongitude>
                            <gmd:southBoundLatitude>
                                <gco:Decimal>{metadado.extensao_sul or -90}</gco:Decimal>
                            </gmd:southBoundLatitude>
                            <gmd:northBoundLatitude>
                                <gco:Decimal>{metadado.extensao_norte or 90}</gco:Decimal>
                            </gmd:northBoundLatitude>
                        </gmd:EX_GeographicBoundingBox>
                    </gmd:geographicElement>
                </gmd:EX_Extent>
            </gmd:extent>
        </gmd:MD_DataIdentification>
    </gmd:identificationInfo>
    
    <!-- Distribuição -->
    <gmd:distributionInfo>
        <gmd:MD_Distribution>
            <gmd:distributionFormat>
                <gmd:MD_Format>
                    <gmd:name>
                        <gco:CharacterString>{metadado.formato_distribuicao or 'Shapefile'}</gco:CharacterString>
                    </gmd:name>
                </gmd:MD_Format>
            </gmd:distributionFormat>
        </gmd:MD_Distribution>
    </gmd:distributionInfo>
    
    <!-- Qualidade dos dados -->
    <gmd:dataQualityInfo>
        <gmd:DQ_DataQuality>
            <gmd:lineage>
                <gmd:LI_Lineage>
                    <gmd:statement>
                        <gco:CharacterString>Metadado submetido em {metadado.data_criacao.strftime('%d/%m/%Y') if metadado.data_criacao else 'data desconhecida'}</gco:CharacterString>
                    </gmd:statement>
                </gmd:LI_Lineage>
            </gmd:lineage>
        </gmd:DQ_DataQuality>
    </gmd:dataQualityInfo>
    
    <!-- Sistema de referência -->
    <gmd:referenceSystemInfo>
        <gmd:MD_ReferenceSystem>
            <gmd:referenceSystemIdentifier>
                <gmd:RS_Identifier>
                    <gmd:code>
                        <gco:CharacterString>{metadado.sistema_referencia or 'SIRGAS 2000'}</gco:CharacterString>
                    </gmd:code>
                </gmd:RS_Identifier>
            </gmd:referenceSystemIdentifier>
        </gmd:MD_ReferenceSystem>
    </gmd:referenceSystemInfo>
    
</gmd:MD_Metadata>'''
from geo_utils import converter_para_geojson, obter_bounding_box_geojson

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/api/geojson/<int:id>')
def api_geojson(id):
    """Retorna GeoJSON do metadado para exibição no mapa"""
    from geo_utils import converter_para_geojson, obter_bounding_box_geojson
    import os
    
    print("\n" + "="*50)
    print("GEOJSON DEBUG")
    print("="*50)
    
    metadado = Metadado.query.get_or_404(id)
    print(f"Metadado ID: {id}")
    print(f"Status: {metadado.status}")
    print(f"Arquivos anexados: {len(metadado.arquivos)}")
    
    # Tentar converter arquivos anexados
    for i, arquivo in enumerate(metadado.arquivos):
        nome_original = arquivo['nome_original']
        print(f"\nArquivo {i+1}: {nome_original}")
        
        caminho = os.path.join('uploads', arquivo['nome_salvo'])
        print(f"  Caminho: {caminho}")
        print(f"  Existe: {os.path.exists(caminho)}")
        
        if os.path.exists(caminho):
            print(f"  Tentando converter...")
            geojson, erro = converter_para_geojson(caminho, nome_original)
            if geojson:
                num_features = len(geojson.get('features', []))
                print(f"  ✅ SUCESSO! Features: {num_features}")
                return jsonify(geojson)
            else:
                print(f"  ❌ ERRO: {erro}")
    
    # Fallback para bounding box
    print("\nNenhum arquivo convertido, usando bounding box...")
    geojson_bbox = obter_bounding_box_geojson(
        metadado.extensao_norte,
        metadado.extensao_sul,
        metadado.extensao_leste,
        metadado.extensao_oeste
    )
    
    if geojson_bbox:
        print("Usando bounding box do metadado")
        return jsonify(geojson_bbox)
    
    # Mapa padrão do Brasil
    print("Usando mapa padrão do Brasil")
    return jsonify({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-74.0, -33.8], [-34.8, -33.8],
                    [-34.8, 5.3], [-74.0, 5.3],
                    [-74.0, -33.8]
                ]]
            },
            "properties": {"name": "Brasil"}
        }]
    })
# ==============================================
# AUTENTICAÇÃO
# ==============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = verificar_login(username, password)
        if user:
            login_user(user)
            flash(f'Bem-vindo, {user.nome}!', 'success')
            if user.papel == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso', 'info')
    return redirect(url_for('index'))

# ==============================================
# CADASTRO E EDIÇÃO (CADASTRADOR)
# ==============================================

@app.route('/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar():
    if current_user.papel not in ['admin', 'cadastrador']:
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        categorias = request.form.getlist('categorias_tematicas')
        
        metadado = Metadado(
            titulo=request.form['titulo'],
            resumo=request.form['resumo'],
            data_referencia=request.form['data_referencia'],
            responsavel=request.form['responsavel'],
            idioma=request.form.get('idioma', 'Português'),
            formato_distribuicao=request.form['formato_distribuicao'],
            sistema_referencia=request.form['sistema_referencia'],
            contato_metadados=request.form['contato_metadados'],
            data_metadados=request.form['data_metadados'],
            status_metadado=request.form['status_metadado'],
            palavras_chave=request.form.get('palavras_chave', ''),
            escala=request.form.get('escala', ''),
            sistema_coordenadas=request.form.get('sistema_coordenadas', 'Geográficas'),
            datum=request.form.get('datum', 'SIRGAS2000'),
            extensao_norte=float(request.form['ext_norte']) if request.form.get('ext_norte') else None,
            extensao_sul=float(request.form['ext_sul']) if request.form.get('ext_sul') else None,
            extensao_leste=float(request.form['ext_leste']) if request.form.get('ext_leste') else None,
            extensao_oeste=float(request.form['ext_oeste']) if request.form.get('ext_oeste') else None,
            status=StatusMetadado.PENDENTE.value,
            criado_por_id=current_user.id
        )
        
        metadado.categorias_lista = categorias
        db.session.add(metadado)
        db.session.commit()
        
        # Processar upload dos arquivos de dados
        arquivos = request.files.getlist('anexos')
        arquivos_lista = []
        for arquivo in arquivos:
            if arquivo and arquivo.filename:
                nome_salvo = salvar_arquivo(arquivo)
                if nome_salvo:
                    arquivos_lista.append({
                        'nome_original': arquivo.filename,
                        'nome_salvo': nome_salvo
                    })
        metadado.arquivos = arquivos_lista
        
        # Processar upload da thumbnail
        thumbnail_file = request.files.get('thumbnail_imagem')
        if thumbnail_file and thumbnail_file.filename:
            thumb_nome = salvar_thumbnail(thumbnail_file)
            if thumb_nome:
                metadado.thumbnail = thumb_nome
        
        db.session.commit()
        flash(f'Metadado "{metadado.titulo}" enviado para aprovação!', 'success')
        return redirect(url_for('index'))
    
    return render_template('cadastro.html')

@app.route('/meus_metadados')
@login_required
def meus_metadados():
    if current_user.papel not in ['admin', 'cadastrador']:
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    if current_user.papel == 'admin':
        metadados = Metadado.query.order_by(Metadado.data_criacao.desc()).all()
    else:
        metadados = Metadado.query.filter_by(criado_por_id=current_user.id).order_by(Metadado.data_criacao.desc()).all()
    
    return render_template('meus_metadados.html', metadados=metadados, usuario=current_user)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_metadado(id):
    metadado = Metadado.query.get_or_404(id)
    
    if current_user.papel != 'admin' and metadado.criado_por_id != current_user.id:
        flash('Você não tem permissão para editar este metadado', 'danger')
        return redirect(url_for('index'))
    
    if metadado.status == StatusMetadado.APROVADO.value and current_user.papel != 'admin':
        flash('Metadado aprovado não pode ser editado. Contate o administrador.', 'warning')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        metadado.titulo = request.form['titulo']
        metadado.resumo = request.form['resumo']
        metadado.data_referencia = request.form['data_referencia']
        metadado.responsavel = request.form['responsavel']
        metadado.idioma = request.form.get('idioma', 'Português')
        metadado.formato_distribuicao = request.form['formato_distribuicao']
        metadado.sistema_referencia = request.form['sistema_referencia']
        metadado.contato_metadados = request.form['contato_metadados']
        metadado.data_metadados = request.form['data_metadados']
        metadado.status_metadado = request.form['status_metadado']
        metadado.palavras_chave = request.form.get('palavras_chave', '')
        metadado.escala = request.form.get('escala', '')
        metadado.sistema_coordenadas = request.form.get('sistema_coordenadas', 'Geográficas')
        metadado.datum = request.form.get('datum', 'SIRGAS2000')
        metadado.extensao_norte = float(request.form['ext_norte']) if request.form.get('ext_norte') else None
        metadado.extensao_sul = float(request.form['ext_sul']) if request.form.get('ext_sul') else None
        metadado.extensao_leste = float(request.form['ext_leste']) if request.form.get('ext_leste') else None
        metadado.extensao_oeste = float(request.form['ext_oeste']) if request.form.get('ext_oeste') else None
        
        categorias = request.form.getlist('categorias_tematicas')
        metadado.categorias_lista = categorias
        
        # Processar novos arquivos
        arquivos = request.files.getlist('anexos')
        if arquivos and arquivos[0].filename:
            arquivos_lista = metadado.arquivos
            for arquivo in arquivos:
                if arquivo and arquivo.filename:
                    nome_salvo = salvar_arquivo(arquivo)
                    if nome_salvo:
                        arquivos_lista.append({
                            'nome_original': arquivo.filename,
                            'nome_salvo': nome_salvo
                        })
            metadado.arquivos = arquivos_lista
        
        # Processar nova thumbnail
        thumbnail_file = request.files.get('thumbnail_imagem')
        if thumbnail_file and thumbnail_file.filename:
            thumb_nome = salvar_thumbnail(thumbnail_file)
            if thumb_nome:
                metadado.thumbnail = thumb_nome
        
        metadado.status = StatusMetadado.PENDENTE.value
        metadado.motivo_rejeicao = None
        
        db.session.commit()
        flash(f'Metadado "{metadado.titulo}" foi reenviado para aprovação!', 'success')
        return redirect(url_for('meus_metadados'))
    
    return render_template('editar_metadado.html', metadado=metadado)

# ==============================================
# ADMIN - APROVAÇÃO E REJEIÇÃO
# ==============================================

@app.route('/pendentes')
@login_required
def pendentes():
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    pendentes = Metadado.query.filter_by(status=StatusMetadado.PENDENTE.value).all()
    return render_template('pendentes.html', pendentes=pendentes)

@app.route('/visualizar_pendente/<int:id>')
@login_required
def visualizar_pendente(id):
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    metadado = Metadado.query.get_or_404(id)
    return render_template('visualizar_pendente.html', metadado=metadado)

@app.route('/aprovar/<int:id>')
@login_required
def aprovar(id):
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    metadado = Metadado.query.get_or_404(id)
    metadado.status = StatusMetadado.APROVADO.value
    metadado.data_aprovacao = datetime.now()
    metadado.aprovado_por_id = current_user.id
    db.session.commit()
    
    flash(f'Metadado "{metadado.titulo}" aprovado com sucesso!', 'success')
    return redirect(url_for('pendentes'))

@app.route('/rejeitar/<int:id>', methods=['GET', 'POST'])
@login_required
def rejeitar(id):
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    metadado = Metadado.query.get_or_404(id)
    
    if request.method == 'POST':
        motivo = request.form.get('motivo', '')
        metadado.status = StatusMetadado.REJEITADO.value
        metadado.motivo_rejeicao = motivo
        db.session.commit()
        
        flash(f'Metadado "{metadado.titulo}" foi rejeitado. Motivo enviado ao cadastrador.', 'warning')
        return redirect(url_for('pendentes'))
    
    return render_template('rejeitar_motivo.html', metadado=metadado)

# ==============================================
# ADMIN - EDIÇÃO AVANÇADA
# ==============================================

@app.route('/admin/editar_metadado/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_editar_metadado(id):
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    metadado = Metadado.query.get_or_404(id)
    
    if request.method == 'POST':
        metadado.titulo = request.form['titulo']
        metadado.resumo = request.form['resumo']
        metadado.data_referencia = request.form['data_referencia']
        metadado.responsavel = request.form['responsavel']
        metadado.idioma = request.form.get('idioma', 'Português')
        metadado.formato_distribuicao = request.form['formato_distribuicao']
        metadado.sistema_referencia = request.form['sistema_referencia']
        metadado.contato_metadados = request.form['contato_metadados']
        metadado.data_metadados = request.form['data_metadados']
        metadado.status_metadado = request.form['status_metadado']
        metadado.palavras_chave = request.form.get('palavras_chave', '')
        metadado.escala = request.form.get('escala', '')
        metadado.sistema_coordenadas = request.form.get('sistema_coordenadas', 'Geográficas')
        metadado.datum = request.form.get('datum', 'SIRGAS2000')
        metadado.extensao_norte = float(request.form['ext_norte']) if request.form.get('ext_norte') else None
        metadado.extensao_sul = float(request.form['ext_sul']) if request.form.get('ext_sul') else None
        metadado.extensao_leste = float(request.form['ext_leste']) if request.form.get('ext_leste') else None
        metadado.extensao_oeste = float(request.form['ext_oeste']) if request.form.get('ext_oeste') else None
        
        categorias = request.form.getlist('categorias_tematicas')
        metadado.categorias_lista = categorias
        
        # Processar novos arquivos
        arquivos = request.files.getlist('anexos')
        if arquivos and arquivos[0].filename:
            arquivos_lista = metadado.arquivos
            for arquivo in arquivos:
                if arquivo and arquivo.filename:
                    nome_salvo = salvar_arquivo(arquivo)
                    if nome_salvo:
                        arquivos_lista.append({
                            'nome_original': arquivo.filename,
                            'nome_salvo': nome_salvo
                        })
            metadado.arquivos = arquivos_lista
        
        # Processar nova thumbnail
        thumbnail_file = request.files.get('thumbnail_imagem')
        if thumbnail_file and thumbnail_file.filename:
            thumb_nome = salvar_thumbnail(thumbnail_file)
            if thumb_nome:
                metadado.thumbnail = thumb_nome
        
        # Reativar se checkbox marcado
        if request.form.get('reativar') == '1':
            metadado.descontinuado = False
            metadado.data_descontinuacao = None
            metadado.motivo_descontinuacao = None
        
        metadado.data_ultima_edicao = datetime.now()
        metadado.editado_por_id = current_user.id
        
        db.session.commit()
        flash(f'Metadado "{metadado.titulo}" atualizado com sucesso!', 'success')
        return redirect(url_for('visualizar_publico', id=metadado.id))
    
    return render_template('admin_editar_metadado.html', metadado=metadado)

@app.route('/admin/desaprovar/<int:id>')
@login_required
def admin_desaprovar(id):
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    metadado = Metadado.query.get_or_404(id)
    
    if metadado.status != StatusMetadado.APROVADO.value:
        flash('Este metadado não está aprovado', 'warning')
        return redirect(url_for('visualizar_publico', id=metadado.id))
    
    metadado.status = StatusMetadado.PENDENTE.value
    metadado.data_ultima_edicao = datetime.now()
    metadado.editado_por_id = current_user.id
    
    db.session.commit()
    flash(f'Metadado "{metadado.titulo}" voltou para pendente.', 'warning')
    return redirect(url_for('pendentes'))


@app.route('/admin/descontinuar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_descontinuar(id):
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    metadado = Metadado.query.get_or_404(id)
    
    if request.method == 'POST':
        motivo = request.form.get('motivo', '')
        metadado.descontinuado = True
        metadado.data_descontinuacao = datetime.now()
        metadado.motivo_descontinuacao = motivo
        metadado.editado_por_id = current_user.id
        metadado.data_ultima_edicao = datetime.now()
        
        db.session.commit()
        flash(f'Metadado "{metadado.titulo}" foi marcado como descontinuado.', 'warning')
        return redirect(url_for('visualizar_publico', id=metadado.id))
    
    return render_template('admin_descontinuar.html', metadado=metadado)


@app.route('/admin/excluir/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_excluir(id):
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    metadado = Metadado.query.get_or_404(id)
    
    if request.method == 'POST':
        confirmar = request.form.get('confirmar', '')
        if confirmar == metadado.titulo:
            # Excluir arquivos físicos
            import os
            for arquivo in metadado.arquivos:
                caminho = os.path.join('uploads', arquivo['nome_salvo'])
                if os.path.exists(caminho):
                    os.remove(caminho)
            
            if metadado.thumbnail:
                caminho_thumb = os.path.join('thumbnails', metadado.thumbnail)
                if os.path.exists(caminho_thumb):
                    os.remove(caminho_thumb)
            
            db.session.delete(metadado)
            db.session.commit()
            flash(f'Metadado "{metadado.titulo}" foi excluído permanentemente.', 'danger')
            return redirect(url_for('index'))
        else:
            flash('Título não confere. Exclusão cancelada.', 'danger')
    
    return render_template('admin_excluir.html', metadado=metadado)

# ==============================================
# ADMIN - USUÁRIOS
# ==============================================
# ==============================================
# ADMIN - GERENCIAMENTO DE USUÁRIOS
# ==============================================

@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    """Lista de usuários para gerenciamento"""
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    usuarios = User.query.all()
    return render_template('admin_usuarios.html', usuarios=usuarios)


@app.route('/admin/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_editar_usuario(id):
    """Editar usuário (admin apenas)"""
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    usuario = User.query.get_or_404(id)
    
    # Não permitir excluir a si mesmo
    if usuario.id == current_user.id:
        flash('Você não pode editar seu próprio usuário nesta tela. Use o perfil.', 'warning')
        return redirect(url_for('admin_usuarios'))
    
    if request.method == 'POST':
        usuario.nome = request.form['nome']
        usuario.email = request.form['email']
        usuario.papel = request.form['papel']
        
        # Se uma nova senha foi fornecida
        nova_senha = request.form.get('nova_senha', '')
        if nova_senha and len(nova_senha) >= 4:
            from werkzeug.security import generate_password_hash
            usuario.senha_hash = generate_password_hash(nova_senha)
            flash(f'Senha alterada para o usuário {usuario.nome}', 'info')
        
        db.session.commit()
        flash(f'Usuário {usuario.nome} atualizado com sucesso!', 'success')
        return redirect(url_for('admin_usuarios'))
    
    return render_template('admin_editar_usuario.html', usuario=usuario)


@app.route('/admin/excluir_usuario/<int:id>', methods=['POST'])
@login_required
def admin_excluir_usuario(id):
    """Excluir usuário (admin apenas)"""
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return jsonify({'erro': 'Acesso negado'}), 403
    
    usuario = User.query.get_or_404(id)
    
    # Não permitir excluir a si mesmo
    if usuario.id == current_user.id:
        flash('Você não pode excluir seu próprio usuário', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    # Verificar se o usuário tem metadados
    metadados_count = Metadado.query.filter_by(criado_por_id=usuario.id).count()
    
    if metadados_count > 0:
        flash(f'O usuário {usuario.nome} possui {metadados_count} metadado(s). Transfira ou exclua os metadados primeiro.', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    db.session.delete(usuario)
    db.session.commit()
    flash(f'Usuário {usuario.nome} foi excluído com sucesso!', 'success')
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/transferir_metadados/<int:id>', methods=['POST'])
@login_required
def admin_transferir_metadados(id):
    """Transferir metadados de um usuário para outro antes de excluir"""
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    usuario_origem = User.query.get_or_404(id)
    usuario_destino_id = request.form.get('usuario_destino')
    
    if not usuario_destino_id:
        flash('Selecione um usuário de destino', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    usuario_destino = User.query.get(usuario_destino_id)
    
    # Transferir metadados
    Metadado.query.filter_by(criado_por_id=usuario_origem.id).update({'criado_por_id': usuario_destino.id})
    db.session.commit()
    
    flash(f'Metadados de {usuario_origem.nome} transferidos para {usuario_destino.nome}', 'success')
    return redirect(url_for('admin_excluir_usuario', id=usuario_origem.id))

@app.route('/admin')
@login_required
def admin():
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    usuarios = User.query.all()
    metadados = Metadado.query.all()
    return render_template('admin.html', usuarios=usuarios, metadados=metadados)

@app.route('/criar_usuario', methods=['GET', 'POST'])
@login_required
def criar_usuario():
    """Criar novo usuário (admin apenas)"""
    if current_user.papel != 'admin':
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        from werkzeug.security import generate_password_hash
        
        # Verificar se usuário já existe
        existe = User.query.filter_by(username=request.form['username']).first()
        if existe:
            flash('Nome de usuário já existe', 'danger')
            return redirect(url_for('criar_usuario'))
        
        novo_usuario = User(
            username=request.form['username'],
            nome=request.form['nome'],
            email=request.form['email'],
            papel=request.form['papel'],
            senha_hash=generate_password_hash(request.form['senha'])
        )
        db.session.add(novo_usuario)
        db.session.commit()
        flash(f'Usuário {novo_usuario.nome} criado com sucesso!', 'success')
        return redirect(url_for('admin_usuarios'))
    
    # GET - mostrar formulário
    return render_template('criar_usuario.html')

# ==============================================
# ARQUIVOS E THUMBNAILS
# ==============================================

@app.route('/download/<nome_arquivo>')
def download(nome_arquivo):
    return send_from_directory('uploads', nome_arquivo)

@app.route('/thumb/<nome_arquivo>')
def thumb(nome_arquivo):
    from flask import send_file
    import os
    
    # Caminho absoluto para a pasta thumbnails
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho = os.path.join(base_dir, 'thumbnails', nome_arquivo)
    
    print(f"Procurando: {caminho}")
    
    if os.path.exists(caminho):
        print(f"Enviando: {caminho}")
        return send_file(caminho)
    else:
        print(f"Não encontrado: {caminho}")
        return "Arquivo não encontrado", 404

@app.after_request
def adicionar_creditos_automaticos(response):
    """Adiciona créditos no HTML se não existirem"""
    if response.content_type == 'text/html' and response.direct_passthrough is False:
        try:
            html = response.get_data(as_text=True)
            if 'Desenvolvido por' not in html and 'geo.luislopes@gmail.com' not in html:
                # Adiciona créditos antes do </body>
                html = html.replace('</body>', '''
                    <footer style="text-align: center; padding: 20px; margin-top: 30px; border-top: 1px solid #ddd; font-size: 12px; color: #888;">
                        <strong>Catálogo MGB</strong> - Desenvolvido por Luís Lopes
                    </footer>
                </body>''')
                response.set_data(html)
        except:
            pass
    return response

# ==============================================
# INICIALIZAÇÃO
# ==============================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        criar_usuario_inicial()
    
    app.run(debug=True, host='0.0.0.0', port=5000)