from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    papel = db.Column(db.String(20), default='cadastrador')  # admin, cadastrador
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

class Metadado(db.Model):
    __tablename__ = 'metadados'
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos básicos
    titulo = db.Column(db.String(200), nullable=False)
    resumo = db.Column(db.Text, nullable=False)
    data_referencia = db.Column(db.String(50), nullable=False)  # Data do dado
    responsavel = db.Column(db.String(200), nullable=False)
    
    # NOVOS CAMPOS OBRIGATÓRIOS
    idioma = db.Column(db.String(50), default='Português')
    categorias_tematicas = db.Column(db.String(500))  # Guarda as categorias selecionadas (JSON)
    formato_distribuicao = db.Column(db.String(100), nullable=False)
    sistema_referencia = db.Column(db.String(100), nullable=False)
    contato_metadados = db.Column(db.String(200), nullable=False)
    data_metadados = db.Column(db.String(50), nullable=False)  # Data de criação do metadado
    status_metadado = db.Column(db.String(50), nullable=False)  # Status do metadado
    
    # Campos existentes
    palavras_chave = db.Column(db.String(500))
    escala = db.Column(db.String(50))
    sistema_coordenadas = db.Column(db.String(100))
    datum = db.Column(db.String(50))
    
    # Extensão geográfica
    extensao_norte = db.Column(db.Float)
    extensao_sul = db.Column(db.Float)
    extensao_leste = db.Column(db.Float)
    extensao_oeste = db.Column(db.Float)
    
    # Status e workflow
    status = db.Column(db.String(20), default='pendente')  # pendente, aprovado, rejeitado
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    data_aprovacao = db.Column(db.DateTime)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    aprovado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Arquivos e thumbnails
    arquivos_json = db.Column(db.Text, default='[]')
    thumbnail = db.Column(db.String(200))  # Nome do arquivo da thumbnail
    
    # Relacionamentos
    criado_por = db.relationship('User', foreign_keys=[criado_por_id])
    aprovado_por = db.relationship('User', foreign_keys=[aprovado_por_id])
    
    # Novos campos para edição e controle
    data_ultima_edicao = db.Column(db.DateTime)
    editado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    descontinuado = db.Column(db.Boolean, default=False)
    data_descontinuacao = db.Column(db.DateTime)
    motivo_descontinuacao = db.Column(db.Text)

    # Relacionamento para quem editou
    editado_por = db.relationship('User', foreign_keys=[editado_por_id])
    
    @property
    def arquivos(self):
        return json.loads(self.arquivos_json or '[]')
    
    @arquivos.setter
    def arquivos(self, value):
        self.arquivos_json = json.dumps(value)
    
    @property
    def categorias_lista(self):
        """Retorna a lista de categorias temáticas selecionadas"""
        if self.categorias_tematicas:
            return json.loads(self.categorias_tematicas)
        return []
    
    @categorias_lista.setter
    def categorias_lista(self, value):
        self.categorias_tematicas = json.dumps(value)