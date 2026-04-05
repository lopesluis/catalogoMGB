# Catálogo de Metadados Geoespaciais - MGB

Sistema para catalogação, busca e compartilhamento de metadados geoespaciais, seguindo o Perfil MGB (Metadados Geoespaciais do Brasil) baseado na norma **ISO 19115**.

## Funcionalidades

- ✅ Cadastro de metadados com campos obrigatórios (ISO 19115)
- ✅ Upload de arquivos (Shapefile, GeoJSON, CSV, KML, ZIP)
- ✅ Thumbnail personalizada para cada metadado
- ✅ Busca por texto e filtro por categoria temática
- ✅ Paginação de resultados
- ✅ Mapa interativo com conversão automática de projeção
- ✅ Exportação para XML (ISO 19115)
- ✅ Fluxo de aprovação (pendente → aprovado/rejeitado)
- ✅ Edição de metadados rejeitados
- ✅ Painel administrativo completo
- ✅ Dashboard com estatísticas
- ✅ Múltiplos usuários (admin e cadastradores)

## Tecnologias

- **Backend:** Python + Flask
- **Banco de Dados:** SQLite
- **Frontend:** HTML5, CSS3, JavaScript
- **Mapas:** Leaflet
- **Geoprocessamento:** PySHP, PyProj

## Instalação

### Windows

1. Instale o Python 3.10 ou superior
2. Clone o repositório
3. Execute `install.bat` como administrador
4. Execute `start.bat`
5. Acesse `http://localhost:5000`

### Login padrão

- Usuário: `admin`
- Senha: `admin123`

## Estrutura de Pastas
