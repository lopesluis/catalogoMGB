@echo off
echo ========================================
echo   Instalador do Catalogo de Metadados MGB
echo ========================================
echo.
echo Instalando dependencias...
echo.

pip install flask flask-login flask-sqlalchemy werkzeug pillow pyshp pyproj geojson

echo.
echo ========================================
echo   Instalacao concluida!
echo   Execute start.bat para iniciar o sistema
echo ========================================
echo.
echo Dependencias instaladas:
echo   - Flask (servidor web)
echo   - Flask-Login (autenticacao)
echo   - SQLAlchemy (banco de dados)
echo   - Pillow (manipulacao de imagens)
echo   - PySHP (leitura de Shapefile)
echo   - PyProj (conversao de projecao)
echo   - GeoJSON (manipulacao de GeoJSON)
echo.
pause