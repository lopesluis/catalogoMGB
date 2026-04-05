from database import User
from werkzeug.security import check_password_hash, generate_password_hash

def verificar_login(username, password):
    """Verifica se o usuário existe e a senha está correta"""
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.senha_hash, password):
        return user
    return None

def criar_usuario_inicial():
    """Cria o usuário administrador padrão se não existir"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            nome='Administrador',
            email='admin@catalogo.local',
            papel='admin',
            senha_hash=generate_password_hash('admin123')
        )
        from database import db
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado: admin / admin123")