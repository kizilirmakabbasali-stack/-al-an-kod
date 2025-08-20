"""
BIST Analiz Uygulaması - Test Scripti
Uygulamanın temel fonksiyonlarını test eder
"""
import sys
import traceback

def test_imports():
    """Gerekli modüllerin import edilip edilemediğini test et"""
    print("📦 Modül import testleri...")
    
    modules = [
        ('streamlit', 'streamlit'),
        ('pandas', 'pandas'), 
        ('numpy', 'numpy'),
        ('yfinance', 'yfinance'),
        ('requests', 'requests'),
        ('beautifulsoup4', 'bs4'),
        ('lxml', 'lxml')
    ]
    
    failed = []
    
    for module_name, import_name in modules:
        try:
            __import__(import_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            failed.append(module_name)
    
    return len(failed) == 0, failed

def test_local_imports():
    """Yerel modüllerin import edilip edilemediğini test et"""
    print("\n🔧 Yerel modül testleri...")
    
    try:
        from data_fetcher import TradingViewDataFetcher
        print("✅ data_fetcher.py")
    except Exception as e:
        print(f"❌ data_fetcher.py: {e}")
        return False
    
    try:
        from bist_analyzer import BISTVolumeAnalyzer
        print("✅ bist_analyzer.py")
    except Exception as e:
        print(f"❌ bist_analyzer.py: {e}")
        return False
    
    return True

def test_data_fetching():
    """Veri çekme fonksiyonunu test et"""
    print("\n📊 Veri çekme testi...")
    
    try:
        from data_fetcher import TradingViewDataFetcher
        
        fetcher = TradingViewDataFetcher()
        
        # BIST100'den bir test hissesi
        test_symbol = "THYAO"
        print(f"🔍 {test_symbol} verisi test ediliyor...")
        
        data = fetcher.get_stock_data(test_symbol, period='5d', interval='1d')
        
        if data is not None and len(data) > 0:
            print(f"✅ {test_symbol} verisi başarıyla alındı ({len(data)} satır)")
            print(f"📅 Tarih aralığı: {data.index[0].date()} - {data.index[-1].date()}")
            return True
        else:
            print(f"❌ {test_symbol} verisi alınamadı")
            return False
            
    except Exception as e:
        print(f"❌ Veri çekme hatası: {e}")
        traceback.print_exc()
        return False

def test_analyzer():
    """Analiz fonksiyonunu test et"""
    print("\n🔬 Analiz motoru testi...")
    
    try:
        from bist_analyzer import BISTVolumeAnalyzer
        
        analyzer = BISTVolumeAnalyzer()
        
        # BIST hisse listesi testi
        print("📋 BIST hisse listesi alınıyor...")
        stocks = analyzer.get_bist_stocks()
        
        if len(stocks) > 100:
            print(f"✅ BIST hisse listesi alındı ({len(stocks)} hisse)")
        else:
            print(f"⚠️  BIST hisse listesi kısa ({len(stocks)} hisse)")
        
        # Tek hisse analizi testi
        test_symbol = "THYAO" if "THYAO" in stocks else stocks[0]
        print(f"🔍 {test_symbol} analiz ediliyor...")
        
        analysis = analyzer.analyze_stock_volume(test_symbol, period='5d', interval='1d')
        
        if analysis:
            print(f"✅ {test_symbol} analizi başarılı")
            print(f"📊 Hacim oranı: {analysis['volume_ratio']:.2f}x")
            return True
        else:
            print(f"❌ {test_symbol} analizi başarısız")
            return False
            
    except Exception as e:
        print(f"❌ Analiz hatası: {e}")
        traceback.print_exc()
        return False

def main():
    """Ana test fonksiyonu"""
    print("=" * 60)
    print("🧪 BIST Analiz Uygulaması - Test Scripti")
    print("=" * 60)
    
    all_passed = True
    
    # 1. Modül import testleri
    import_success, failed_modules = test_imports()
    if not import_success:
        print(f"\n❌ Başarısız modüller: {', '.join(failed_modules)}")
        print("💡 Çözüm: pip install " + " ".join(failed_modules))
        all_passed = False
    
    # 2. Yerel modül testleri
    if not test_local_imports():
        print("\n❌ Yerel modül hatası! Dosyaların doğru dizinde olduğundan emin olun.")
        all_passed = False
    
    # 3. Veri çekme testi
    if import_success and not test_data_fetching():
        print("\n❌ Veri çekme hatası! İnternet bağlantınızı kontrol edin.")
        all_passed = False
    
    # 4. Analiz motoru testi
    if import_success and not test_analyzer():
        print("\n❌ Analiz motoru hatası!")
        all_passed = False
    
    # Sonuç
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TÜM TESTLER BAŞARILI!")
        print("🚀 Uygulamayı çalıştırmaya hazır: streamlit run app.py")
    else:
        print("❌ BAZI TESTLER BAŞARISIZ!")
        print("🔧 Yukarıdaki hataları düzelttikten sonra tekrar deneyin.")
    
    print("=" * 60)
    input("\nÇıkmak için Enter'a basın...")

if __name__ == "__main__":
    main()
