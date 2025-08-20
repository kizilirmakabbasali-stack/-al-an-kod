@echo off
echo BIST Analiz Uygulamasi - Gerekli Moduller Kuruluyor...
echo.

pip install --upgrade pip
pip install streamlit>=1.28.0
pip install pandas>=2.0.0
pip install numpy>=1.24.0
pip install yfinance>=0.2.18
pip install requests>=2.31.0
pip install beautifulsoup4>=4.12.0
pip install lxml>=4.9.0

echo.
echo Moduller basariyla kuruldu!
echo Uygulamayi baslatmak icin: streamlit run app.py
pause
