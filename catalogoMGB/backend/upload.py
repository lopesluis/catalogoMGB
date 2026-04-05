import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image

UPLOAD_FOLDER = 'uploads'
THUMBNAIL_FOLDER = 'thumbnails'

def salvar_arquivo(arquivo):
    """Salva um arquivo enviado e retorna o nome gerado"""
    if not arquivo or not arquivo.filename:
        return None
    
    nome_original = secure_filename(arquivo.filename)
    extensao = nome_original.rsplit('.', 1)[1].lower() if '.' in nome_original else ''
    nome_gerado = f"{uuid.uuid4().hex}.{extensao}" if extensao else uuid.uuid4().hex
    caminho = os.path.join(UPLOAD_FOLDER, nome_gerado)
    arquivo.save(caminho)
    return nome_gerado

def salvar_thumbnail(arquivo_imagem):
    """Salva uma imagem de thumbnail e retorna o nome gerado"""
    if not arquivo_imagem or not arquivo_imagem.filename:
        return None
    
    # Verificar se é imagem
    if not arquivo_imagem.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        return None
    
    nome_original = secure_filename(arquivo_imagem.filename)
    extensao = nome_original.rsplit('.', 1)[1].lower() if '.' in nome_original else 'png'
    nome_gerado = f"thumb_{uuid.uuid4().hex}.{extensao}"
    caminho = os.path.join(THUMBNAIL_FOLDER, nome_gerado)
    
    # Redimensionar para thumbnail
    try:
        img = Image.open(arquivo_imagem)
        img.thumbnail((300, 300))
        img.save(caminho)
        return nome_gerado
    except:
        return None

def gerar_thumbnail(arquivo):
    """Compatibilidade com código antigo - gera thumbnail a partir de arquivo enviado"""
    return salvar_thumbnail(arquivo)

def gerar_thumbnail_from_file(caminho_arquivo):
    """Gera thumbnail a partir de um arquivo já salvo"""
    try:
        img = Image.open(caminho_arquivo)
        img.thumbnail((300, 300))
        thumb_name = f"thumb_{uuid.uuid4().hex}.png"
        thumb_path = os.path.join(THUMBNAIL_FOLDER, thumb_name)
        img.save(thumb_path, 'PNG')
        return thumb_name
    except:
        return None