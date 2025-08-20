"""
BIST Analiz Uygulaması - Hızlı Kurulum ve Çalıştırma
"""
import subprocess
import sys
import os

def install_requirements():
    """Gerekli modülleri kur"""
    requirements = [
        "streamlit>=1.28.0",
        "pandas>=2.0.0", 
        "numpy>=1.24.0",
        "yfinance>=0.2.18",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0"
    ]
    
    print("🔧 Gerekli modüller kuruluyor...")
    
    for requirement in requirements:
        try:
            print(f"⬇️  {requirement} kuruluyor...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", requirement])
            print(f"✅ {requirement} başarıyla kuruldu")
        except subprocess.CalledProcessError as e:
            print(f"❌ {requirement} kurulumunda hata: {e}")
            return False
    
    return True

def check_files():
    """Gerekli dosyaların varlığını kontrol et"""
    required_files = ["app.py", "bist_analyzer.py", "data_fetcher.py"]
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Eksik dosyalar: {', '.join(missing_files)}")
        return False
    
    print("✅ Tüm gerekli dosyalar mevcut")
    return True

def run_application():
    """Streamlit uygulamasını başlat"""
    try:
        print("\n🚀 BIST Analiz Uygulaması başlatılıyor...")        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        install.bat        install.bat        install.bat        install.bat        install.bat        run_app.bat        pip install -r requirements.txt        pip install -r requirements.txt        pip install -r requirements.txt        python test_app.py        python test_app.py        python test_app.py        python test_app.py        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        python setup_and_run.py        pip install -r requirements.txt
        streamlit run app.py        python test_app.py        python test_app.py        python test_app.py
        print("📱 Tarayıcınızda http://localhost:8501 adresine gidin")
        print("⏹️  Uygulamayı durdurmak için Ctrl+C basın")
        print("-" * 50)
        
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
        
    except KeyboardInterrupt:
        print("\n🛑 Uygulama durduruldu")
    except Exception as e:
        print(f"❌ Uygulama başlatılırken hata: {e}")

def main():
    """Ana fonksiyon"""
    print("=" * 60)
    print("🏦 BIST Hisse Senetleri Analiz Uygulaması")
    print("📈 Hacim Bazlı Teknik Analiz ve Tarama Aracı")
    print("=" * 60)
    
    # Dosya kontrolü
    if not check_files():
        print("\n❌ Gerekli dosyalar bulunamadı!")
        input("Çıkmak için Enter'a basın...")
        return
    
    # Modül kurulumu
    print("\n1️⃣  Modül kurulum kontrolü...")
    
    choice = input("Modülleri yeniden kurmak ister misiniz? (y/N): ").lower()
    
    if choice == 'y' or choice == 'yes':
        if not install_requirements():
            print("\n❌ Modül kurulumunda hata!")
            input("Çıkmak için Enter'a basın...")
            return
        print("\n✅ Tüm modüller başarıyla kuruldu!")
    else:
        print("⏭️  Modül kurulumu atlandı")
    
    # Uygulama başlatma
    print("\n2️⃣  Uygulama başlatılıyor...")
    input("Başlatmak için Enter'a basın...")
    
    run_application()

if __name__ == "__main__":
    main()
