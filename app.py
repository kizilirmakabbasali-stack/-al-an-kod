import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import time
import asyncio
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from bist_analyzer import BISTVolumeAnalyzer

def get_market_status():
    """Piyasa durumunu kontrol et"""
    now = datetime.now()
    
    # BIST işlem saatleri: 09:30 - 18:00 (Pazartesi-Cuma)
    weekday = now.weekday()  # 0=Pazartesi, 6=Pazar
    hour = now.hour
    minute = now.minute
    
    if weekday >= 5:  # Hafta sonu
        return "KAPALI", "Hafta sonu"
    
    market_open = hour > 9 or (hour == 9 and minute >= 30)
    market_close = hour < 18
    
    if market_open and market_close:
        return "AÇIK", "Piyasa açık"
    elif hour < 9 or (hour == 9 and minute < 30):
        return "KAPALI", "Piyasa henüz açılmadı"
    else:
        return "KAPALI", "Piyasa kapandı"

def format_number(number, precision=2):
    """Sayıları Türkçe formatta göster"""
    if pd.isna(number) or number == 0:
        return "0"
    
    if abs(number) >= 1_000_000:
        return f"{number/1_000_000:.1f}M"
    elif abs(number) >= 1_000:
        return f"{number/1_000:.1f}K"
    else:
        return f"{number:.{precision}f}"

def create_results_summary_chart(results_df):
    """Sonuçlar için özet grafik oluştur"""
    if results_df.empty:
        return None
    
    # Çoklu grafik oluştur
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=['Volume Dağılımı', 'Hisse Bazında Volume', 'Fiyat Dağılımı', 'Tarih Analizi'],
        specs=[[{"type": "scatter"}, {"type": "bar"}],
               [{"type": "histogram"}, {"type": "scatter"}]]
    )
    
    try:
        # 1. Volume Histogram (sol üst)
        volume_col = None
        for col in ['Volume Oranı', 'Hacim Oranı', 'Hacim Çarpanı']:
            if col in results_df.columns:
                volume_col = col
                break
        
        if volume_col:
            # Volume verilerini temizle
            volume_data = []
            for val in results_df[volume_col]:
                try:
                    if isinstance(val, str):
                        clean_val = float(val.replace('x', '').replace(',', '.'))
                    else:
                        clean_val = float(val)
                    volume_data.append(clean_val)
                except:
                    volume_data.append(1.0)
            
            fig.add_trace(go.Histogram(
                x=volume_data,
                nbinsx=15,
                name='Volume',
                marker_color='#26a69a',
                opacity=0.7,
                showlegend=False
            ), row=1, col=1)
        
        # 2. Hisse bazında Volume Bar (sağ üst)
        if volume_col and 'Hisse' in results_df.columns:
            top_10 = results_df.head(10)
            volume_vals = []
            for val in top_10[volume_col]:
                try:
                    if isinstance(val, str):
                        clean_val = float(val.replace('x', '').replace(',', '.'))
                    else:
                        clean_val = float(val)
                    volume_vals.append(clean_val)
                except:
                    volume_vals.append(1.0)
            
            fig.add_trace(go.Bar(
                x=top_10['Hisse'],
                y=volume_vals,
                name='Volume',
                marker_color='#2196F3',
                showlegend=False
            ), row=1, col=2)
        
        # 3. Fiyat Histogram (sol alt)
        price_col = None
        for col in ['Fiyat', 'Price', 'Güncel Fiyat']:
            if col in results_df.columns:
                price_col = col
                break
        
        if price_col:
            price_data = []
            for val in results_df[price_col]:
                try:
                    if isinstance(val, str):
                        clean_val = float(val.replace(',', '.').replace(' TL', ''))
                    else:
                        clean_val = float(val)
                    price_data.append(clean_val)
                except:
                    continue
            
            if price_data:
                fig.add_trace(go.Histogram(
                    x=price_data,
                    nbinsx=12,
                    name='Fiyat',
                    marker_color='#FF9800',
                    opacity=0.7,
                    showlegend=False
                ), row=2, col=1)
        
        # 4. Zaman Analizi (sağ alt)
        if 'Tarih' in results_df.columns:
            tarih_data = results_df['Tarih'].value_counts().head(7)
            fig.add_trace(go.Scatter(
                x=tarih_data.index,
                y=tarih_data.values,
                mode='lines+markers',
                name='Günlük Bulunan',
                line=dict(color='#E91E63', width=3),
                marker=dict(size=8),
                showlegend=False
            ), row=2, col=2)
        
        # Layout güncelleme
        fig.update_layout(
            title={
                'text': '📊 Tarama Sonuçları Analizi',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': 'white'}
            },
            template='plotly_dark',
            height=500,
            showlegend=False,
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        # Alt başlık güncellemeleri
        fig.update_xaxes(title_text="Volume Oranı", row=1, col=1)
        fig.update_yaxes(title_text="Hisse Sayısı", row=1, col=1)
        
        fig.update_xaxes(title_text="Hisse Kodları", row=1, col=2)
        fig.update_yaxes(title_text="Volume Oranı", row=1, col=2)
        
        fig.update_xaxes(title_text="Fiyat (TL)", row=2, col=1)
        fig.update_yaxes(title_text="Hisse Sayısı", row=2, col=1)
        
        fig.update_xaxes(title_text="Tarih", row=2, col=2)
        fig.update_yaxes(title_text="Bulunan Sayısı", row=2, col=2)
        
        return fig
        
    except Exception as e:
        print(f"Grafik oluşturma hatası: {e}")
        
        # Basit yedek grafik
        fig_simple = go.Figure()
        
        fig_simple.add_trace(go.Scatter(
            x=list(range(len(results_df))),
            y=[1] * len(results_df),
            mode='markers',
            marker=dict(
                size=15,
                color='#26a69a',
                symbol='circle'
            ),
            name='Bulunan Hisseler',
            text=results_df.get('Hisse', [''] * len(results_df)),
            hovertemplate='<b>%{text}</b><br>Sıra: %{x}<extra></extra>'
        ))
        
        fig_simple.update_layout(
            title='📈 Bulunan Hisse Senetleri',
            template='plotly_dark',
            height=300,
            xaxis_title='Sıra',
            yaxis_title='Sonuç'
        )
        
        return fig_simple


def main():
    st.set_page_config(
        page_title="BIST Analiz ve Tarama Aracı",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Modern CSS stil eklemeleri
    st.markdown("""
    <style>
        .main {
            padding-top: 1rem;
        }
        .metric-container {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            color: white;
        }
        .scan-result-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            transition: all 0.3s ease;
        }
        .scan-result-card:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
        }
        .trend-up {
            color: #26a69a;
            font-weight: bold;
        }
        .trend-down {
            color: #ef5350;
            font-weight: bold;
        }
        .progress-container {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 0.5rem;
            margin: 1rem 0;
        }
        /* Mobile optimizations */
        @media (max-width: 768px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .metric-container {
                font-size: 0.9rem;
                padding: 0.5rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("� BIST Hisse Senetleri Analiz ve Tarama Aracı")
    st.markdown("**Modern, Hızlı ve Kapsamlı Analiz Sistemi**")
    st.markdown("---")

    # Global save settings and path hint
    st.sidebar.caption(f"Kayıt klasörü: {BASE_SAVE_DIR}")
    st.sidebar.markdown("### 💾 Kaydetme Ayarları")
    # Defaults
    if 'auto_save' not in st.session_state:
        st.session_state['auto_save'] = True
    if 'save_keep' not in st.session_state:
        st.session_state['save_keep'] = 10
    st.sidebar.checkbox("Her tarama sonunda otomatik kaydet", value=st.session_state['auto_save'], key="auto_save")
    st.sidebar.number_input("Kayıt tutma sayısı (son N)", min_value=1, max_value=100, value=st.session_state['save_keep'], step=1, key="save_keep")
    st.sidebar.markdown("---")

    # Main tabs for different analysis types
    tab1, tab2, tab3 = st.tabs(["📊 Teknik Analiz & Tarama", "📋 Temel Analiz & Tarama", "📁 Kayıtlı Sonuçlar"])
    
    with tab1:
        technical_analysis_section()
    
    with tab2:
        fundamental_analysis_section()
    
    with tab3:
        saved_results_section()


# ---------- Saved Results Helpers ----------
# Use an absolute path anchored to this file's directory to avoid CWD issues
BASE_SAVE_DIR = (Path(__file__).parent / "saved_results").resolve()

def _scan_dir(category: str, scan_code: str) -> Path:
    return BASE_SAVE_DIR / category / scan_code

def save_results_df(df: pd.DataFrame, category: str, scan_code: str) -> Path:
    try:
        target = _scan_dir(category, scan_code)
        target.mkdir(parents=True, exist_ok=True)
        # Include microseconds to prevent filename collisions on rapid consecutive saves
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_path = target / f"{scan_code}_{ts}.csv"
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        return file_path
    except Exception as e:
        st.error(f"Sonuç kaydedilemedi: {e}")
        return None

def prune_saved_files(category: str, scan_code: str, keep: int = 10) -> None:
    """Keep only the most recent 'keep' CSV files for a scan; delete older ones."""
    try:
        d = _scan_dir(category, scan_code)
        if not d.exists():
            return
        files = sorted(d.glob('*.csv'), key=lambda p: p.name, reverse=True)
        for p in files[keep:]:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                # Best-effort cleanup; ignore individual failures
                pass
    except Exception as e:
        st.warning(f"Kayıt temizleme hatası: {e}")

def list_saved_scan_types(category: str):
    root = BASE_SAVE_DIR / category
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])

def list_saved_files(category: str, scan_code: str):
    d = _scan_dir(category, scan_code)
    if not d.exists():
        return []
    files = sorted([p for p in d.glob('*.csv')], key=lambda p: p.name, reverse=True)
    return files

def load_saved_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.error(f"Dosya okunamadı: {e}")
        return pd.DataFrame()


def technical_analysis_section():
    """Technical analysis and screening section"""
    st.header("📊 Teknik Analiz ve Tarama")
    st.markdown("Hacim bazlı teknik analiz ve çeşitli teknik tarama kriterleri")
    st.markdown("---")

    # Sidebar for technical analysis controls
    st.sidebar.header("📊 Teknik Analiz Ayarları")

    # Time period selection with interval - ALWAYS AT TOP
    col1, col2 = st.sidebar.columns([1, 1])

    with col1:
        # Time interval options with Turkish labels
        interval_options = {
            "5 dakika": "5m",
            "15 dakika": "15m",
            "1 saat": "1h",
            "4 saat": "4h",
            "1 gün": "1d",
            "1 hafta": "1wk"
        }

        interval_display = st.selectbox(
            "Zaman Aralığı",
            options=list(interval_options.keys()),
            index=4,  # Default to "1 gün"
            help="Mum grafiği zaman aralığı")

        # Get the actual interval code for yfinance
        interval = interval_options[interval_display]

    with col2:
        # Period options with Turkish labels
        period_options_map = {
            "1 gün": "1d",
            "5 gün": "5d",
            "1 ay": "1mo",
            "3 ay": "3mo",
            "6 ay": "6mo",
            "1 yıl": "1y"
        }

        # Define period options based on interval
        if interval in ["5m", "15m"]:
            period_display_options = ["1 gün", "5 gün", "1 ay"]
            default_period_display = "5 gün"
        elif interval in ["1h", "4h"]:
            period_display_options = ["5 gün", "1 ay", "3 ay"]
            default_period_display = "1 ay"
        else:  # 1d, 1wk
            period_display_options = ["1 ay", "3 ay", "6 ay", "1 yıl"]
            default_period_display = "3 ay"

        period_display = st.selectbox(
            "Veri Periyodu",
            options=period_display_options,
            index=period_display_options.index(default_period_display)
            if default_period_display in period_display_options else 0,
            help="Analiz için kullanılacak toplam veri periyodu")

        # Get the actual period code for yfinance
        period = period_options_map[period_display]

    st.sidebar.markdown("---")

    # Scanning type selection
    st.sidebar.header("Tarama Türü")

    scan_types = {
        "3 Periyot Artış Taraması": "3_period_increase",
        "Hacim Patlaması + EMA Golden Cross": "ema_golden_cross",
        "MACD Zero Line Breakout": "macd_zero_breakout",
        "VWAP Destek Testi + Yükselen Dip": "vwap_support_test",
        "Üçlü Hacim Onayı": "triple_volume_confirmation",
        "Daralan Üçgen + Hacim Kırılımı": "triangle_breakout",
        "RSI Diverjans + Trend Kırılımı": "rsi_divergence_breakout",
        "Bollinger Band Sıkışması + Breakout": "bollinger_squeeze_breakout",
        "Fibonacci Retest + Harmonik Yapı": "fibonacci_harmonic_pattern"
    }

    selected_scan = st.sidebar.selectbox(
        "🔍 Tarama Seçimi",
        options=list(scan_types.keys()),
        index=0,
        help="Farklı tarama kriterlerini seçebilirsiniz")

    scan_code = scan_types[selected_scan]

    st.sidebar.markdown("---")

    # Scan-specific settings
    if scan_code == "3_period_increase":
        st.sidebar.subheader("3 Periyot Artış Ayarları")

        # Period selection for volume progression check
        periods_to_check = st.sidebar.selectbox(
            "Artış Periyot Sayısı",
            options=[1, 2, 3, 4],
            index=2,  # Default to 3 periods
            help="Kaç periyot ardışık hacim artışı aranacak (1-4 arası)")

        # Volume SMA period
        sma_period = st.sidebar.number_input(
            "Hacim SMA Periyodu",
            min_value=5,
            max_value=50,
            value=10,
            help="Hacim basit hareketli ortalama periyodu")

        # Minimum volume threshold
        min_volume_multiplier = st.sidebar.slider(
            "Minimum Hacim Çarpanı",
            min_value=1.0,
            max_value=3.0,
            value=1.5,
            step=0.1,
            help="Son hacim / SMA oranı minimum değeri")

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write("**1. Ardışık Hacim Artışı:**")
            st.write(f"Son {periods_to_check} periyot hacim artışı")
            st.write("**2. SMA Üzeri Hacim:**")
            st.write(f"Hacim > SMA({sma_period}) × {min_volume_multiplier}")
            st.write("**3. Her İki Kriter Birlikte**")

    elif scan_code == "ema_golden_cross":
        st.sidebar.subheader("EMA Golden Cross Ayarları")

        # EMA periods
        col1, col2 = st.sidebar.columns([1, 1])
        with col1:
            ema_short = st.number_input("Kısa EMA",
                                        min_value=20,
                                        max_value=100,
                                        value=50,
                                        help="Kısa dönem EMA periyodu")
        with col2:
            ema_long = st.number_input("Uzun EMA",
                                       min_value=100,
                                       max_value=300,
                                       value=200,
                                       help="Uzun dönem EMA periyodu")

        # Volume settings
        volume_period = st.sidebar.number_input(
            "Hacim Karşılaştırma Periyodu",
            min_value=10,
            max_value=50,
            value=20,
            help="Hacim ortalaması için kullanılacak gün sayısı")

        volume_threshold = st.sidebar.slider(
            "Hacim Artış Eşiği (%)",
            min_value=30,
            max_value=200,
            value=50,
            step=10,
            help="Ortalama hacmin kaç % üzeri olmalı")

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write(f"**1. EMA Golden Cross:**")
            st.write(f"EMA({ema_short}) > EMA({ema_long}) kesişimi")
            st.write("**2. Hacim Patlaması:**")
            st.write(
                f"Hacim > {volume_period} günlük ort. × %{100 + volume_threshold}"
            )
            st.write("**3. Her İki Kriter Birlikte**")

        # Set default values for unused parameters
        sma_period = 10
        min_volume_multiplier = 1.5

    elif scan_code == "macd_zero_breakout":
        st.sidebar.subheader("MACD Zero Line Ayarları")

        # MACD periods
        col1, col2, col3 = st.sidebar.columns([1, 1, 1])
        with col1:
            macd_fast = st.number_input("Hızlı EMA",
                                        min_value=8,
                                        max_value=20,
                                        value=12,
                                        help="MACD hızlı EMA periyodu")
        with col2:
            macd_slow = st.number_input("Yavaş EMA",
                                        min_value=20,
                                        max_value=35,
                                        value=26,
                                        help="MACD yavaş EMA periyodu")
        with col3:
            macd_signal = st.number_input("Sinyal",
                                          min_value=7,
                                          max_value=15,
                                          value=9,
                                          help="MACD sinyal periyodu")

        # Sideways movement detection
        sideways_days = st.sidebar.number_input(
            "Yatay Hareket Günü",
            min_value=3,
            max_value=10,
            value=5,
            help="Breakout öncesi yatay hareket kontrol günü")

        sideways_threshold = st.sidebar.slider(
            "Yatay Hareket Eşiği (%)",
            min_value=1.0,
            max_value=5.0,
            value=2.0,
            step=0.5,
            help="Fiyat dalgalanma toleransı")

        # Volume confirmation
        volume_confirmation = st.sidebar.checkbox(
            "Hacim Teyidi",
            value=True,
            help="Breakout'ta hacim artışı aransın mı?")

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write(f"**1. MACD Zero Breakout:**")
            st.write(f"MACD çizgisi > 0 kesişimi")
            st.write("**2. Histogram Pozitif:**")
            st.write("MACD Histogram > 0")
            st.write("**3. Önceden Yatay Hareket:**")
            st.write(
                f"Son {sideways_days} gün <%{sideways_threshold} dalgalanma")
            if volume_confirmation:
                st.write("**4. Hacim Teyidi**")

        # Set default values for unused parameters
        sma_period = 10
        min_volume_multiplier = 1.5
        ema_short = 50
        ema_long = 200
        volume_period = 20
        volume_threshold = 50

    elif scan_code == "vwap_support_test":
        st.sidebar.subheader("VWAP Destek Testi Ayarları")

        # VWAP calculation periods
        vwap_period = st.sidebar.number_input(
            "VWAP Periyodu",
            min_value=10,
            max_value=100,
            value=20,
            help="VWAP hesaplama için kullanılacak periyot")

        # Support test parameters
        support_tolerance = st.sidebar.slider(
            "Destek Toleransı (%)",
            min_value=0.5,
            max_value=3.0,
            value=1.0,
            step=0.1,
            help="VWAP'tan ne kadar sapma kabul edilebilir")

        # Rising bottom parameters
        bottom_lookback = st.sidebar.number_input(
            "Dip Arama Periyodu",
            min_value=5,
            max_value=20,
            value=10,
            help="Son dipları aramak için geriye bakış periyodu")

        # Volume confirmation for breakout
        vol_confirm_vwap = st.sidebar.checkbox(
            "VWAP Üzeri Çıkışta Hacim Teyidi",
            value=True,
            help="VWAP üzeri çıkışta hacim artışı aransın mı?")

        vol_multiplier_vwap = st.sidebar.slider(
            "Hacim Çarpanı",
            min_value=1.2,
            max_value=3.0,
            value=1.5,
            step=0.1,
            help="Ortalama hacmin kaç katı olmalı"
        ) if vol_confirm_vwap else 1.5

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write(f"**1. VWAP Altına Sarma:**")
            st.write(f"Fiyat VWAP'ın altına iniyor")
            st.write("**2. VWAP Üzeri Çıkış:**")
            st.write("Fiyat tekrar VWAP üzerine çıkıyor")
            st.write("**3. Yükselen Dip:**")
            st.write(f"Son 2 dip yükselme eğiliminde")
            if vol_confirm_vwap:
                st.write(f"**4. Hacim Teyidi:** {vol_multiplier_vwap}x")

        # Set default values for unused parameters
        sma_period = 10
        min_volume_multiplier = 1.5
        ema_short = 50
        ema_long = 200
        volume_period = 20
        volume_threshold = 50
        macd_fast = 12
        macd_slow = 26
        macd_signal = 9
        sideways_days = 5
        sideways_threshold = 2.0
        volume_confirmation = True

    elif scan_code == "triple_volume_confirmation":
        st.sidebar.subheader("Üçlü Hacim Onayı Ayarları")

        # Volume confirmation settings
        volume_avg_period = st.sidebar.number_input(
            "Hacim Ortalama Periyodu",
            min_value=10,
            max_value=50,
            value=20,
            help="Hacim ortalaması için kullanılacak gün sayısı")

        volume_multiplier_triple = st.sidebar.slider(
            "Hacim Çarpanı",
            min_value=1.5,
            max_value=5.0,
            value=2.0,
            step=0.1,
            help="Günlük hacim ortalama hacmin kaç katı olmalı")

        # RSI settings
        rsi_period = st.sidebar.number_input("RSI Periyodu",
                                             min_value=10,
                                             max_value=30,
                                             value=14,
                                             help="RSI hesaplama periyodu")

        col1, col2 = st.sidebar.columns([1, 1])
        with col1:
            rsi_min = st.number_input("RSI Min",
                                      min_value=50,
                                      max_value=70,
                                      value=60,
                                      help="RSI alt sınır")
        with col2:
            rsi_max = st.number_input("RSI Max",
                                      min_value=65,
                                      max_value=80,
                                      value=70,
                                      help="RSI üst sınır")

        # OBV settings
        obv_period = st.sidebar.number_input(
            "OBV Karşılaştırma Periyodu",
            min_value=10,
            max_value=50,
            value=20,
            help="OBV en yüksek seviye kontrolü için periyot")

        obv_threshold = st.sidebar.slider(
            "OBV Eşik (%)",
            min_value=90,
            max_value=100,
            value=95,
            step=1,
            help="OBV'nin son X günün hangi yüzdesinde olmalı")

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write(f"**1. Hacim Onayı:**")
            st.write(
                f"Günlük hacim > {volume_avg_period} günlük ort. × {volume_multiplier_triple}"
            )
            st.write(f"**2. RSI Momentum:**")
            st.write(f"RSI {rsi_min}-{rsi_max} arası (güçlü momentum)")
            st.write(f"**3. OBV Doruğunda:**")
            st.write(
                f"OBV son {obv_period} günün en üst %{100-obv_threshold}'inde")

        # Set default values for unused parameters
        sma_period = 10
        min_volume_multiplier = 1.5
        ema_short = 50
        ema_long = 200
        volume_period = 20
        volume_threshold = 50
        macd_fast = 12
        macd_slow = 26
        macd_signal = 9
        sideways_days = 5
        sideways_threshold = 2.0
        volume_confirmation = True
        vwap_period = 20
        support_tolerance = 1.0
        bottom_lookback = 10
        vol_confirm_vwap = True
        vol_multiplier_vwap = 1.5

    elif scan_code == "triangle_breakout":
        st.sidebar.subheader("Daralan Üçgen + Hacim Kırılımı Ayarları")

        # Triangle detection settings
        triangle_period = st.sidebar.number_input(
            "Üçgen Formasyon Periyodu",
            min_value=10,
            max_value=50,
            value=20,
            help="Üçgen formasyonu tespit etmek için analiz periyodu")

        # Convergence threshold for triangle
        convergence_threshold = st.sidebar.slider(
            "Daralmışlık Eşiği (%)",
            min_value=1.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Üst ve alt trend çizgisi arasındaki daralmışlık yüzdesi")

        # Volume decline requirement
        volume_decline_period = st.sidebar.number_input(
            "Hacim Azalış Periyodu",
            min_value=5,
            max_value=20,
            value=10,
            help="Hacim azalışını kontrol etmek için periyot")

        volume_decline_threshold = st.sidebar.slider(
            "Hacim Azalış Eşiği (%)",
            min_value=10,
            max_value=50,
            value=20,
            step=5,
            help="Hacim ne kadar azalmış olmalı (yüzde)")

        # Breakout volume requirement
        breakout_volume_increase = st.sidebar.slider(
            "Kırılım Hacim Artışı (%)",
            min_value=20,
            max_value=100,
            value=40,
            step=5,
            help="Kırılım anında hacim artış yüzdesi")

        # Breakout direction
        breakout_direction = st.sidebar.selectbox(
            "Kırılım Yönü", ["Yukarı", "Aşağı", "Her İkisi"],
            index=0,
            help="Hangi yöndeki kırılımları tarayacak")

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write(f"**1. Daralan Üçgen:**")
            st.write(
                f"Son {triangle_period} günde fiyat <%{convergence_threshold} daralmış"
            )
            st.write(f"**2. Hacim Azalışı:**")
            st.write(
                f"Son {volume_decline_period} günde hacim -%{volume_decline_threshold} azalmış"
            )
            st.write(f"**3. Kırılım Hacmi:**")
            st.write(
                f"Kırılım anında hacim +%{breakout_volume_increase} artmış")
            st.write(f"**4. Kırılım Yönü:** {breakout_direction}")

        # Set default values for unused parameters
        sma_period = 10
        min_volume_multiplier = 1.5
        ema_short = 50
        ema_long = 200
        volume_period = 20
        volume_threshold = 50
        macd_fast = 12
        macd_slow = 26
        macd_signal = 9
        sideways_days = 5
        sideways_threshold = 2.0
        volume_confirmation = True
        vwap_period = 20
        support_tolerance = 1.0
        bottom_lookback = 10
        vol_confirm_vwap = True
        vol_multiplier_vwap = 1.5
        volume_avg_period = 20
        volume_multiplier_triple = 2.0
        rsi_period = 14
        rsi_min = 60
        rsi_max = 70
        obv_period = 20
        obv_threshold = 95

    elif scan_code == "rsi_divergence_breakout":
        st.sidebar.subheader("RSI Diverjans + Trend Kırılımı Ayarları")

        # RSI settings
        rsi_period = st.sidebar.number_input("RSI Periyodu",
                                             min_value=5,
                                             max_value=30,
                                             value=14,
                                             help="RSI hesaplama periyodu")

        # Divergence detection settings
        divergence_period = st.sidebar.number_input(
            "Diverjans Analiz Periyodu",
            min_value=10,
            max_value=50,
            value=20,
            help="Diverjans tespiti için analiz periyodu")

        # Minimum divergence strength
        min_divergence_strength = st.sidebar.slider(
            "Minimum Diverjans Gücü",
            min_value=0.3,
            max_value=1.0,
            value=0.6,
            step=0.1,
            help="Diverjansın ne kadar güçlü olması gerekir (0.3-1.0)")

        # Resistance breakout settings
        resistance_period = st.sidebar.number_input(
            "Direnç Analiz Periyodu",
            min_value=5,
            max_value=30,
            value=10,
            help="Direnç seviyesi tespit periyodu")

        resistance_breakout_percent = st.sidebar.slider(
            "Direnç Kırılım Yüzdesi (%)",
            min_value=0.5,
            max_value=5.0,
            value=1.5,
            step=0.1,
            help="Direnci kaç yüzde kırması gerekir")

        # Volume confirmation for breakout
        volume_breakout_multiplier = st.sidebar.slider(
            "Kırılım Hacim Çarpanı",
            min_value=1.2,
            max_value=3.0,
            value=1.5,
            step=0.1,
            help="Kırılım anında hacim ne kadar artmalı")

        # RSI oversold threshold for divergence
        rsi_oversold_threshold = st.sidebar.slider(
            "RSI Aşırı Satım Eşiği",
            min_value=20,
            max_value=40,
            value=30,
            help="Diverjans için RSI'ın düşük seviyesi")

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write(f"**1. Pozitif RSI Diverjansı:**")
            st.write(
                f"Son {divergence_period} günde fiyat alçalan, RSI yükselen dipler"
            )
            st.write(f"**2. RSI Aşırı Satım:**")
            st.write(f"RSI {rsi_oversold_threshold} seviyesinin altında")
            st.write(f"**3. Direnç Kırılımı:**")
            st.write(
                f"Son {resistance_period} gün direnci %{resistance_breakout_percent} kırılım"
            )
            st.write(f"**4. Hacim Onayı:**")
            st.write(
                f"Kırılım anında hacim {volume_breakout_multiplier}x artış")

        # Set defaults for other parameters
        sma_period = 10
        min_volume_multiplier = 1.5
        ema_short = 50
        ema_long = 200
        volume_period = 20
        volume_threshold = 50
        macd_fast = 12
        macd_slow = 26
        macd_signal = 9
        sideways_days = 5
        sideways_threshold = 2.0
        volume_confirmation = True
        vwap_period = 20
        support_tolerance = 1.0
        bottom_lookback = 10
        vol_confirm_vwap = True
        vol_multiplier_vwap = 1.5
        volume_avg_period = 20
        volume_multiplier_triple = 2.0
        rsi_min = 60
        rsi_max = 70
        obv_period = 20
        obv_threshold = 95
        triangle_period = 20
        convergence_threshold = 3.0
        volume_decline_period = 10
        volume_decline_threshold = 20
        breakout_volume_increase = 40
        breakout_direction = "Yukarı"

    elif scan_code == "bollinger_squeeze_breakout":
        st.sidebar.subheader("Bollinger Band Sıkışması + Breakout Ayarları")

        # Bollinger Band settings
        bb_period = st.sidebar.number_input(
            "Bollinger Band Periyodu",
            min_value=10,
            max_value=50,
            value=20,
            help="Bollinger Band hesaplama periyodu")

        bb_std_dev = st.sidebar.slider(
            "Standart Sapma",
            min_value=1.5,
            max_value=3.0,
            value=2.0,
            step=0.1,
            help="Bollinger Band standart sapma çarpanı")

        # Squeeze detection settings
        squeeze_period = st.sidebar.number_input(
            "Sıkışma Analiz Periyodu (Ay)",
            min_value=3,
            max_value=12,
            value=6,
            help="Band genişliği karşılaştırma periyodu (ay)")

        squeeze_percentile = st.sidebar.slider(
            "Sıkışma Yüzdelik Dilimi",
            min_value=5,
            max_value=25,
            value=10,
            help="Band genişliği en düşük yüzdelik dilim")

        # Upper band breakout settings
        upper_band_breakout_percent = st.sidebar.slider(
            "Üst Band Kırılım Yüzdesi (%)",
            min_value=0.5,
            max_value=3.0,
            value=1.0,
            step=0.1,
            help="Üst bandı kaç yüzde kırması gerekir")

        # Volume confirmation for breakout
        volume_squeeze_multiplier = st.sidebar.slider(
            "Kırılım Hacim Çarpanı",
            min_value=1.2,
            max_value=4.0,
            value=1.5,
            step=0.1,
            help="Kırılım anında hacim ne kadar artmalı")

        # Consecutive days requirement
        consecutive_days = st.sidebar.number_input(
            "Ardışık Gün Sayısı",
            min_value=1,
            max_value=5,
            value=2,
            help="Kaç gün üst üstte kapanış gerekir")

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write(f"**1. Bollinger Band Sıkışması:**")
            st.write(
                f"Son {squeeze_period} ayın en düşük %{squeeze_percentile} band genişliği"
            )
            st.write(f"**2. Üst Band Kırılımı:**")
            st.write(f"Fiyat üst bandı %{upper_band_breakout_percent} kırıyor")
            st.write(f"**3. Hacim Onayı:**")
            st.write(
                f"Kırılım anında hacim {volume_squeeze_multiplier}x artış")
            st.write(f"**4. Süreklilik:**")
            st.write(f"{consecutive_days} gün ardışık üst banda yakın kapanış")

        # Set defaults for other parameters
        sma_period = 10
        min_volume_multiplier = 1.5
        ema_short = 50
        ema_long = 200
        volume_period = 20
        volume_threshold = 50
        macd_fast = 12
        macd_slow = 26
        macd_signal = 9
        sideways_days = 5
        sideways_threshold = 2.0
        volume_confirmation = True
        vwap_period = 20
        support_tolerance = 1.0
        bottom_lookback = 10
        vol_confirm_vwap = True
        vol_multiplier_vwap = 1.5
        volume_avg_period = 20
        volume_multiplier_triple = 2.0
        rsi_period = 14
        rsi_min = 60
        rsi_max = 70
        obv_period = 20
        obv_threshold = 95
        triangle_period = 20
        convergence_threshold = 3.0
        volume_decline_period = 10
        volume_decline_threshold = 20
        breakout_volume_increase = 40
        breakout_direction = "Yukarı"
        divergence_period = 20
        min_divergence_strength = 0.6
        resistance_period = 10
        resistance_breakout_percent = 1.5
        volume_breakout_multiplier = 1.5
        rsi_oversold_threshold = 30

    elif scan_code == "fibonacci_harmonic_pattern":
        st.sidebar.subheader("Fibonacci Retest + Harmonik Yapı Ayarları")

        # Fibonacci retracement settings
        fib_lookback_period = st.sidebar.number_input(
            "Fibonacci Analiz Periyodu",
            min_value=20,
            max_value=100,
            value=50,
            help="Son yükseliş/düşüş tespiti için geriye bakış periyodu")

        fib_retracement_min = st.sidebar.slider(
            "Minimum Geri Çekilme (%)",
            min_value=30.0,
            max_value=45.0,
            value=38.2,
            step=0.1,
            help="Minimum Fibonacci geri çekilme seviyesi")

        fib_retracement_max = st.sidebar.slider(
            "Maksimum Geri Çekilme (%)",
            min_value=45.0,
            max_value=65.0,
            value=50.0,
            step=0.1,
            help="Maksimum Fibonacci geri çekilme seviyesi")

        # Support tolerance
        fib_support_tolerance = st.sidebar.slider(
            "Destek Toleransı (%)",
            min_value=1.0,
            max_value=5.0,
            value=2.0,
            step=0.1,
            help="Fibonacci seviyesine ne kadar yakın olmalı")

        # Harmonic pattern settings
        harmonic_pattern_type = st.sidebar.selectbox(
            "Harmonik Formasyon Türü",
            ["Gartley", "Bat", "Butterfly", "Crab", "Otomatik"],
            index=4,
            help="Tespit edilecek harmonik formasyon türü")

        harmonic_tolerance = st.sidebar.slider("Harmonik Tolerans (%)",
                                               min_value=2.0,
                                               max_value=10.0,
                                               value=5.0,
                                               step=0.5,
                                               help="Harmonik oran toleransı")

        # Volume confirmation
        fib_volume_multiplier = st.sidebar.slider(
            "Destek Hacim Çarpanı",
            min_value=1.0,
            max_value=3.0,
            value=1.3,
            step=0.1,
            help="Destek testinde hacim onayı")

        # Trend strength requirement
        trend_strength_days = st.sidebar.number_input(
            "Trend Gücü Analiz Günü",
            min_value=5,
            max_value=20,
            value=10,
            help="Önceki trendin gücü analizi")

        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write(f"**1. Fibonacci Geri Çekilme:**")
            st.write(
                f"%{fib_retracement_min} - %{fib_retracement_max} arası destek"
            )
            st.write(f"**2. Harmonik Formasyon:**")
            st.write(f"{harmonic_pattern_type} formasyonu tamamlanma bölgesi")
            st.write(f"**3. Destek Onayı:**")
            st.write(
                f"Fibonacci seviyesinden %{fib_support_tolerance} toleransla rebound"
            )
            st.write(f"**4. Hacim Onayı:**")
            st.write(f"Destek testinde {fib_volume_multiplier}x hacim artışı")

        # Set defaults for other parameters
        sma_period = 10
        min_volume_multiplier = 1.5
        ema_short = 50
        ema_long = 200
        volume_period = 20
        volume_threshold = 50
        macd_fast = 12
        macd_slow = 26
        macd_signal = 9
        sideways_days = 5
        sideways_threshold = 2.0
        volume_confirmation = True
        vwap_period = 20
        support_tolerance = 1.0
        bottom_lookback = 10
        vol_confirm_vwap = True
        vol_multiplier_vwap = 1.5
        volume_avg_period = 20
        volume_multiplier_triple = 2.0
        rsi_period = 14
        rsi_min = 60
        rsi_max = 70
        obv_period = 20
        obv_threshold = 95
        triangle_period = 20
        convergence_threshold = 3.0
        volume_decline_period = 10
        volume_decline_threshold = 20
        breakout_volume_increase = 40
        breakout_direction = "Yukarı"
        divergence_period = 20
        min_divergence_strength = 0.6
        resistance_period = 10
        resistance_breakout_percent = 1.5
        volume_breakout_multiplier = 1.5
        rsi_oversold_threshold = 30
        bb_period = 20
        bb_std_dev = 2.0
        squeeze_period = 6
        squeeze_percentile = 10
        upper_band_breakout_percent = 1.0
        volume_squeeze_multiplier = 1.5
        consecutive_days = 2

    else:
        # Default values for all parameters
        sma_period = 10
        min_volume_multiplier = 1.5
        ema_short = 50
        ema_long = 200
        volume_period = 20
        volume_threshold = 50
        macd_fast = 12
        macd_slow = 26
        macd_signal = 9
        sideways_days = 5
        sideways_threshold = 2.0
        volume_confirmation = True
        vwap_period = 20
        support_tolerance = 1.0
        bottom_lookback = 10
        vol_confirm_vwap = True
        vol_multiplier_vwap = 1.5
        volume_avg_period = 20
        volume_multiplier_triple = 2.0
        rsi_period = 14
        rsi_min = 60
        rsi_max = 70
        obv_period = 20
        obv_threshold = 95
        triangle_period = 20
        convergence_threshold = 3.0
        volume_decline_period = 10
        volume_decline_threshold = 20
        breakout_volume_increase = 40
        breakout_direction = "Yukarı"
        divergence_period = 20
        min_divergence_strength = 0.6
        resistance_period = 10
        resistance_breakout_percent = 1.5
        volume_breakout_multiplier = 1.5
        rsi_oversold_threshold = 30
        bb_period = 20
        bb_std_dev = 2.0
        squeeze_period = 6
        squeeze_percentile = 10
        upper_band_breakout_percent = 1.0
        volume_squeeze_multiplier = 1.5
        consecutive_days = 2
        fib_lookback_period = 50
        fib_retracement_min = 38.2
        fib_retracement_max = 50.0
        fib_support_tolerance = 2.0
        harmonic_pattern_type = "Otomatik"
        harmonic_tolerance = 5.0
        fib_volume_multiplier = 1.3
        trend_strength_days = 10
        st.sidebar.info("Bu tarama henüz geliştirilmemiştir.")

        # Initialize analyzer
        breakout_direction = "Yukarı"
        divergence_period = 20
        min_divergence_strength = 0.6
        resistance_period = 10
        resistance_breakout_percent = 1.5
        volume_breakout_multiplier = 1.5
        rsi_oversold_threshold = 30
        st.sidebar.info("Bu tarama henüz geliştirilmemiştir.")

    # Initialize analyzer
    analyzer = BISTVolumeAnalyzer()

    # Analysis button
    if st.sidebar.button("🔍 Analizi Başlat", type="primary"):
        if scan_code == "ema_golden_cross":
            run_analysis(analyzer,
                         period,
                         interval,
                         sma_period,
                         min_volume_multiplier,
                         scan_code,
                         ema_short=ema_short,
                         ema_long=ema_long,
                         volume_period=volume_period,
                         volume_threshold=volume_threshold)
        elif scan_code == "macd_zero_breakout":
            run_analysis(analyzer,
                         period,
                         interval,
                         sma_period,
                         min_volume_multiplier,
                         scan_code,
                         macd_fast=macd_fast,
                         macd_slow=macd_slow,
                         macd_signal=macd_signal,
                         sideways_days=sideways_days,
                         sideways_threshold=sideways_threshold,
                         volume_confirmation=volume_confirmation)
        elif scan_code == "vwap_support_test":
            run_analysis(analyzer,
                         period,
                         interval,
                         sma_period,
                         min_volume_multiplier,
                         scan_code,
                         vwap_period=vwap_period,
                         support_tolerance=support_tolerance,
                         bottom_lookback=bottom_lookback,
                         vol_confirm_vwap=vol_confirm_vwap,
                         vol_multiplier_vwap=vol_multiplier_vwap)
        elif scan_code == "triple_volume_confirmation":
            run_analysis(analyzer,
                         period,
                         interval,
                         sma_period,
                         min_volume_multiplier,
                         scan_code,
                         volume_avg_period=volume_avg_period,
                         volume_multiplier_triple=volume_multiplier_triple,
                         rsi_period=rsi_period,
                         rsi_min=rsi_min,
                         rsi_max=rsi_max,
                         obv_period=obv_period,
                         obv_threshold=obv_threshold)
        elif scan_code == "triangle_breakout":
            run_analysis(analyzer,
                         period,
                         interval,
                         sma_period,
                         min_volume_multiplier,
                         scan_code,
                         triangle_period=triangle_period,
                         convergence_threshold=convergence_threshold,
                         volume_decline_period=volume_decline_period,
                         volume_decline_threshold=volume_decline_threshold,
                         breakout_volume_increase=breakout_volume_increase,
                         breakout_direction=breakout_direction)
        elif scan_code == "rsi_divergence_breakout":
            run_analysis(
                analyzer,
                period,
                interval,
                sma_period,
                min_volume_multiplier,
                scan_code,
                rsi_period=rsi_period,
                divergence_period=divergence_period,
                min_divergence_strength=min_divergence_strength,
                resistance_period=resistance_period,
                resistance_breakout_percent=resistance_breakout_percent,
                volume_breakout_multiplier=volume_breakout_multiplier,
                rsi_oversold_threshold=rsi_oversold_threshold)
        elif scan_code == "bollinger_squeeze_breakout":
            run_analysis(
                analyzer,
                period,
                interval,
                sma_period,
                min_volume_multiplier,
                scan_code,
                bb_period=bb_period,
                bb_std_dev=bb_std_dev,
                squeeze_period=squeeze_period,
                squeeze_percentile=squeeze_percentile,
                upper_band_breakout_percent=upper_band_breakout_percent,
                volume_squeeze_multiplier=volume_squeeze_multiplier,
                consecutive_days=consecutive_days)
        elif scan_code == "fibonacci_harmonic_pattern":
            run_analysis(analyzer,
                         period,
                         interval,
                         sma_period,
                         min_volume_multiplier,
                         scan_code,
                         fib_lookback_period=fib_lookback_period,
                         fib_retracement_min=fib_retracement_min,
                         fib_retracement_max=fib_retracement_max,
                         fib_support_tolerance=fib_support_tolerance,
                         harmonic_pattern_type=harmonic_pattern_type,
                         harmonic_tolerance=harmonic_tolerance,
                         fib_volume_multiplier=fib_volume_multiplier,
                         trend_strength_days=trend_strength_days)
        else:
            # Default 3 period increase scan  
            run_analysis(analyzer, period, interval, sma_period,
                         min_volume_multiplier, scan_code,
                         periods_to_check=periods_to_check)

    # If no new run, show last cached results for this scan type
    cache = st.session_state.get('tech_cache')
    if cache and cache.get('scan_type') == scan_code:
        st.info("Önceki tarama sonuçları gösteriliyor (yeniden tarama yapılmadı).")
        try:
            display_results(cache.get('results', []), cache.get('total', 0), scan_code, **(cache.get('kwargs', {})))
        except Exception:
            pass

    # Auto refresh option
    auto_refresh = st.sidebar.checkbox("Otomatik Yenileme (5dk)", value=False)
    if auto_refresh:
        placeholder = st.empty()
        while auto_refresh:
            with placeholder.container():
                if scan_code == "ema_golden_cross":
                    run_analysis(analyzer,
                                 period,
                                 interval,
                                 sma_period,
                                 min_volume_multiplier,
                                 scan_code,
                                 ema_short=ema_short,
                                 ema_long=ema_long,
                                 volume_period=volume_period,
                                 volume_threshold=volume_threshold)
                elif scan_code == "macd_zero_breakout":
                    run_analysis(analyzer,
                                 period,
                                 interval,
                                 sma_period,
                                 min_volume_multiplier,
                                 scan_code,
                                 macd_fast=macd_fast,
                                 macd_slow=macd_slow,
                                 macd_signal=macd_signal,
                                 sideways_days=sideways_days,
                                 sideways_threshold=sideways_threshold,
                                 volume_confirmation=volume_confirmation)
                elif scan_code == "vwap_support_test":
                    run_analysis(analyzer,
                                 period,
                                 interval,
                                 sma_period,
                                 min_volume_multiplier,
                                 scan_code,
                                 vwap_period=vwap_period,
                                 support_tolerance=support_tolerance,
                                 bottom_lookback=bottom_lookback,
                                 vol_confirm_vwap=vol_confirm_vwap,
                                 vol_multiplier_vwap=vol_multiplier_vwap)
                elif scan_code == "triple_volume_confirmation":
                    run_analysis(
                        analyzer,
                        period,
                        interval,
                        sma_period,
                        min_volume_multiplier,
                        scan_code,
                        volume_avg_period=volume_avg_period,
                        volume_multiplier_triple=volume_multiplier_triple,
                        rsi_period=rsi_period,
                        rsi_min=rsi_min,
                        rsi_max=rsi_max,
                        obv_period=obv_period,
                        obv_threshold=obv_threshold)
                elif scan_code == "triangle_breakout":
                    run_analysis(
                        analyzer,
                        period,
                        interval,
                        sma_period,
                        min_volume_multiplier,
                        scan_code,
                        triangle_period=triangle_period,
                        convergence_threshold=convergence_threshold,
                        volume_decline_period=volume_decline_period,
                        volume_decline_threshold=volume_decline_threshold,
                        breakout_volume_increase=breakout_volume_increase,
                        breakout_direction=breakout_direction)
                elif scan_code == "rsi_divergence_breakout":
                    run_analysis(
                        analyzer,
                        period,
                        interval,
                        sma_period,
                        min_volume_multiplier,
                        scan_code,
                        rsi_period=rsi_period,
                        divergence_period=divergence_period,
                        min_divergence_strength=min_divergence_strength,
                        resistance_period=resistance_period,
                        resistance_breakout_percent=resistance_breakout_percent,
                        volume_breakout_multiplier=volume_breakout_multiplier,
                        rsi_oversold_threshold=rsi_oversold_threshold)
                elif scan_code == "bollinger_squeeze_breakout":
                    run_analysis(
                        analyzer,
                        period,
                        interval,
                        sma_period,
                        min_volume_multiplier,
                        scan_code,
                        bb_period=bb_period,
                        bb_std_dev=bb_std_dev,
                        squeeze_period=squeeze_period,
                        squeeze_percentile=squeeze_percentile,
                        upper_band_breakout_percent=upper_band_breakout_percent,
                        volume_squeeze_multiplier=volume_squeeze_multiplier,
                        consecutive_days=consecutive_days)
                elif scan_code == "fibonacci_harmonic_pattern":
                    run_analysis(analyzer,
                                 period,
                                 interval,
                                 sma_period,
                                 min_volume_multiplier,
                                 scan_code,
                                 fib_lookback_period=fib_lookback_period,
                                 fib_retracement_min=fib_retracement_min,
                                 fib_retracement_max=fib_retracement_max,
                                 fib_support_tolerance=fib_support_tolerance,
                                 harmonic_pattern_type=harmonic_pattern_type,
                                 harmonic_tolerance=harmonic_tolerance,
                                 fib_volume_multiplier=fib_volume_multiplier,
                                 trend_strength_days=trend_strength_days)
                else:
                    run_analysis(analyzer, period, interval, sma_period,
                                 min_volume_multiplier, scan_code)
            time.sleep(300)  # 5 minutes

    # Information section
    with st.expander("ℹ️ Uygulama Hakkında"):
        st.markdown("""
        ### Özellikler:
        - **Otomatik Veri Çekme**: BIST hisse senetleri otomatik olarak çekilir
        - **Hacim Analizi**: Her hisse için detaylı hacim analizi yapılır
        - **SMA Hesaplama**: Belirtilen periyot için hacim basit hareketli ortalaması
        - **Filtreleme**: Artan hacim ve SMA üzeri koşullarına göre filtreleme
        - **Gerçek Zamanlı**: TradingView verileri ile güncel analiz
        
        ### Tarama Kriterleri:
        1. **Ardışık Hacim Artışı**: Seçilen periyot sayısı kadar ardışık hacim artışı (1-4 periyot arası seçilebilir)
        2. **SMA Üzeri Hacim**: Bugünkü hacim > Hacim SMA × Çarpan değeri
        3. **Her İki Kriterin Aynı Anda Karşılanması**: Hem ardışık artış hem de SMA üzeri olması gerekir
        """)


def apply_scan_criteria(analysis, volume_ratio, volume_progression,
                        min_volume_multiplier, scan_type, stock, **kwargs):
    """Apply different scanning criteria based on scan type"""

    if scan_type == "3_period_increase":
        # 3 Periyot Artış Taraması
        criteria_met = (volume_ratio >= min_volume_multiplier
                        and volume_progression)

        # Get periods_to_check from kwargs for column header
        periods_to_check = kwargs.get('periods_to_check', 3)

        result_row = {
            'Hisse':
            stock,
            'Son Hacim':
            f"{analysis['current_volume']:,.0f}",
            'Hacim SMA':
            f"{analysis['volume_sma']:,.0f}",
            'Hacim Oranı':
            f"{volume_ratio:.2f}x",
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'Hacim Trendi':
            analysis['volume_trend'],
            f'{periods_to_check} Periyot Artış':
            "✅" if volume_progression else "❌",
            'Durum':
            "✅ Her İki Kriter" if criteria_met else "❌"
        }

    elif scan_type == "ema_golden_cross":
        # EMA Golden Cross + Volume Explosion Scan
        ema_short = kwargs.get('ema_short', 50)
        ema_long = kwargs.get('ema_long', 200)
        volume_period = kwargs.get('volume_period', 20)
        volume_threshold = kwargs.get('volume_threshold', 50)

        # Extract EMA and volume data
        golden_cross = analysis.get('golden_cross', False)
        golden_cross_recent = analysis.get('golden_cross_recent', False)
        volume_ma = analysis.get('volume_ma', 0)
        current_volume = analysis['current_volume']

        # Check volume explosion criteria
        volume_explosion = False
        volume_increase_pct = 0
        if volume_ma > 0:
            volume_increase_pct = (
                (current_volume - volume_ma) / volume_ma) * 100
            volume_explosion = volume_increase_pct >= volume_threshold

        # Both criteria must be met
        criteria_met = golden_cross_recent and volume_explosion

        result_row = {
            'Hisse':
            stock,
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            f'EMA({ema_short})':
            f"₺{analysis.get('ema_short', 0):.2f}",
            f'EMA({ema_long})':
            f"₺{analysis.get('ema_long', 0):.2f}",
            'Golden Cross':
            "✅" if golden_cross_recent else "❌",
            'Son Hacim':
            f"{current_volume:,.0f}",
            f'{volume_period}G Ort Hacim':
            f"{volume_ma:,.0f}" if volume_ma > 0 else "N/A",
            'Hacim Artış %':
            f"+{volume_increase_pct:.1f}%" if volume_ma > 0 else "N/A",
            'Hacim Patlaması':
            "✅" if volume_explosion else "❌",
            'Durum':
            "✅ Her İki Kriter" if criteria_met else "❌"
        }

    elif scan_type == "macd_zero_breakout":
        # MACD Zero Line Breakout Scan
        macd_fast = kwargs.get('macd_fast', 12)
        macd_slow = kwargs.get('macd_slow', 26)
        macd_signal = kwargs.get('macd_signal', 9)
        sideways_days = kwargs.get('sideways_days', 5)
        sideways_threshold = kwargs.get('sideways_threshold', 2.0)
        volume_confirmation = kwargs.get('volume_confirmation', True)

        # Extract MACD and movement data
        macd_zero_breakout_recent = analysis.get('macd_zero_breakout_recent',
                                                 False)
        macd_histogram_positive = analysis.get('macd_histogram_positive',
                                               False)
        sideways_movement = analysis.get('sideways_movement', False)
        macd_line = analysis.get('macd_line', 0)
        macd_histogram = analysis.get('macd_histogram', 0)

        # Check volume confirmation if enabled
        volume_ok = True
        if volume_confirmation:
            volume_ok = volume_ratio >= 1.2  # At least 20% above average

        # All criteria must be met
        criteria_met = macd_zero_breakout_recent and macd_histogram_positive and sideways_movement and volume_ok

        result_row = {
            'Hisse':
            stock,
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'MACD Line':
            f"{macd_line:.4f}",
            'MACD Histogram':
            f"{macd_histogram:.4f}",
            'Zero Breakout':
            "✅" if macd_zero_breakout_recent else "❌",
            'Histogram +':
            "✅" if macd_histogram_positive else "❌",
            'Yatay Hareket':
            "✅" if sideways_movement else "❌",
            'Son Hacim':
            f"{analysis['current_volume']:,.0f}",
            'Hacim Oranı':
            f"{volume_ratio:.2f}x",
            'Hacim OK':
            "✅" if volume_ok else "❌" if volume_confirmation else "N/A",
            'Durum':
            "✅ Tüm Kriterler" if criteria_met else "❌"
        }

    elif scan_type == "vwap_support_test":
        # VWAP Support Test + Rising Bottoms Scan
        vwap_period = kwargs.get('vwap_period', 20)
        support_tolerance = kwargs.get('support_tolerance', 1.0)
        bottom_lookback = kwargs.get('bottom_lookback', 10)
        vol_confirm_vwap = kwargs.get('vol_confirm_vwap', True)
        vol_multiplier_vwap = kwargs.get('vol_multiplier_vwap', 1.5)

        # Extract VWAP and bottom data
        vwap_support_test = analysis.get('vwap_support_test', False)
        vwap_breakout_recent = analysis.get('vwap_breakout_recent', False)
        rising_bottoms = analysis.get('rising_bottoms', False)
        vwap_value = analysis.get('vwap', 0)

        # Check volume confirmation if enabled
        volume_ok_vwap = True
        if vol_confirm_vwap:
            volume_ok_vwap = volume_ratio >= vol_multiplier_vwap

        # All criteria must be met
        criteria_met = vwap_support_test and vwap_breakout_recent and rising_bottoms and volume_ok_vwap

        result_row = {
            'Hisse':
            stock,
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'VWAP':
            f"₺{vwap_value:.2f}",
            'Fiyat/VWAP':
            f"{(analysis['current_price']/vwap_value):.3f}"
            if vwap_value > 0 else "N/A",
            'VWAP Altına Sarma':
            "✅" if vwap_support_test else "❌",
            'VWAP Üzeri Çıkış':
            "✅" if vwap_breakout_recent else "❌",
            'Yükselen Dip':
            "✅" if rising_bottoms else "❌",
            'Son Hacim':
            f"{analysis['current_volume']:,.0f}",
            'Hacim Oranı':
            f"{volume_ratio:.2f}x",
            'Hacim OK':
            "✅" if volume_ok_vwap else "❌" if vol_confirm_vwap else "N/A",
            'Durum':
            "✅ Tüm Kriterler" if criteria_met else "❌"
        }

    elif scan_type == "triple_volume_confirmation":
        # Triple Volume Confirmation Scan
        volume_avg_period = kwargs.get('volume_avg_period', 20)
        volume_multiplier_triple = kwargs.get('volume_multiplier_triple', 2.0)
        rsi_period = kwargs.get('rsi_period', 14)
        rsi_min = kwargs.get('rsi_min', 60)
        rsi_max = kwargs.get('rsi_max', 70)
        obv_period = kwargs.get('obv_period', 20)
        obv_threshold = kwargs.get('obv_threshold', 95)

        # Extract triple confirmation data
        triple_volume_confirmed = analysis.get('triple_volume_confirmed',
                                               False)
        rsi_in_range = analysis.get('rsi_in_range', False)
        obv_at_peak = analysis.get('obv_at_peak', False)
        rsi_value = analysis.get('rsi', 0)
        obv_value = analysis.get('obv', 0)

        # Calculate volume ratio for triple confirmation (using custom calculation)
        current_volume = analysis.get('current_volume', 0)
        # Get volume average from analysis if available, otherwise calculate fallback
        volume_avg_triple = analysis.get(
            'volume_sma', current_volume /
            volume_multiplier_triple if current_volume > 0 else 1)
        volume_ratio_triple = current_volume / volume_avg_triple if volume_avg_triple > 0 else 0

        # All three criteria must be met
        criteria_met = triple_volume_confirmed and rsi_in_range and obv_at_peak

        result_row = {
            'Hisse':
            stock,
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'Son Hacim':
            f"{current_volume:,.0f}",
            'Hacim Çarpanı':
            f"{volume_ratio_triple:.2f}x",
            'Hacim Onayı':
            "✅" if triple_volume_confirmed else "❌",
            'RSI':
            f"{rsi_value:.1f}",
            'RSI Aralık':
            f"{rsi_min}-{rsi_max}",
            'RSI OK':
            "✅" if rsi_in_range else "❌",
            'OBV':
            f"{obv_value:,.0f}",
            'OBV Doruğunda':
            "✅" if obv_at_peak else "❌",
            'Durum':
            "✅ Üçlü Onay" if criteria_met else "❌"
        }

    elif scan_type == "triangle_breakout":
        # Triangle Breakout + Volume Surge Scan
        triangle_period = kwargs.get('triangle_period', 20)
        convergence_threshold = kwargs.get('convergence_threshold', 3.0)
        volume_decline_period = kwargs.get('volume_decline_period', 10)
        volume_decline_threshold = kwargs.get('volume_decline_threshold', 20)
        breakout_volume_increase = kwargs.get('breakout_volume_increase', 40)
        breakout_direction = kwargs.get('breakout_direction', "Yukarı")

        # Extract triangle breakout data
        triangle_detected = analysis.get('triangle_detected', False)
        volume_declined = analysis.get('volume_declined', False)
        breakout_confirmed = analysis.get('breakout_confirmed', False)
        breakout_direction_correct = analysis.get('breakout_direction_correct',
                                                  False)

        # All criteria must be met
        criteria_met = triangle_detected and volume_declined and breakout_direction_correct

        result_row = {
            'Hisse':
            stock,
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'Daralan Üçgen':
            "✅" if triangle_detected else "❌",
            'Hacim Azalışı':
            "✅" if volume_declined else "❌",
            'Kırılım Onayı':
            "✅" if breakout_confirmed else "❌",
            'Yön Uyumu':
            "✅" if breakout_direction_correct else "❌",
            'Son Hacim':
            f"{analysis['current_volume']:,.0f}",
            'Hacim Oranı':
            f"{volume_ratio:.2f}x",
            'Kırılım Yönü':
            breakout_direction,
            'Durum':
            "✅ Tüm Kriterler" if criteria_met else "❌"
        }

    elif scan_type == "rsi_divergence_breakout":
        # RSI Divergence + Trend Breakout Scan
        rsi_period = kwargs.get('rsi_period', 14)
        divergence_period = kwargs.get('divergence_period', 20)
        min_divergence_strength = kwargs.get('min_divergence_strength', 0.6)
        resistance_period = kwargs.get('resistance_period', 10)
        resistance_breakout_percent = kwargs.get('resistance_breakout_percent',
                                                 1.5)
        volume_breakout_multiplier = kwargs.get('volume_breakout_multiplier',
                                                1.5)
        rsi_oversold_threshold = kwargs.get('rsi_oversold_threshold', 30)

        # Extract RSI divergence data
        rsi_divergence_detected = analysis.get('rsi_divergence_detected',
                                               False)
        rsi_oversold = analysis.get('rsi_oversold', False)
        resistance_broken = analysis.get('resistance_broken', False)
        volume_confirmed_breakout = analysis.get('volume_confirmed_breakout',
                                                 False)
        rsi_current = analysis.get('rsi', 0)

        # All criteria must be met
        criteria_met = rsi_divergence_detected and rsi_oversold and resistance_broken and volume_confirmed_breakout

        result_row = {
            'Hisse':
            stock,
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'RSI Diverjans':
            "✅" if rsi_divergence_detected else "❌",
            'RSI Aşırı Satım':
            "✅" if rsi_oversold else "❌",
            'Direnç Kırılımı':
            "✅" if resistance_broken else "❌",
            'Hacim Onayı':
            "✅" if volume_confirmed_breakout else "❌",
            'Güncel RSI':
            f"{rsi_current:.1f}",
            'Son Hacim':
            f"{analysis['current_volume']:,.0f}",
            'Hacim Oranı':
            f"{volume_ratio:.2f}x",
            'Durum':
            "✅ Tüm Kriterler" if criteria_met else "❌"
        }

    elif scan_type == "bollinger_squeeze_breakout":
        # Bollinger Band Squeeze + Breakout Scan
        bb_period = kwargs.get('bb_period', 20)
        bb_std_dev = kwargs.get('bb_std_dev', 2.0)
        squeeze_period = kwargs.get('squeeze_period', 6)
        squeeze_percentile = kwargs.get('squeeze_percentile', 10)
        upper_band_breakout_percent = kwargs.get('upper_band_breakout_percent',
                                                 1.0)
        volume_squeeze_multiplier = kwargs.get('volume_squeeze_multiplier',
                                               1.5)
        consecutive_days = kwargs.get('consecutive_days', 2)

        # Extract Bollinger squeeze data
        bb_squeeze_detected = analysis.get('bb_squeeze_detected', False)
        upper_band_broken = analysis.get('upper_band_broken', False)
        volume_confirmed_squeeze = analysis.get('volume_confirmed_squeeze',
                                                False)
        consecutive_upper_closes = analysis.get('consecutive_upper_closes',
                                                False)

        # All criteria must be met
        criteria_met = bb_squeeze_detected and upper_band_broken and volume_confirmed_squeeze and consecutive_upper_closes

        result_row = {
            'Hisse':
            stock,
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'BB Sıkışması':
            "✅" if bb_squeeze_detected else "❌",
            'Üst Band Kırılımı':
            "✅" if upper_band_broken else "❌",
            'Hacim Onayı':
            "✅" if volume_confirmed_squeeze else "❌",
            'Ardışık Kapanış':
            "✅" if consecutive_upper_closes else "❌",
            'Son Hacim':
            f"{analysis['current_volume']:,.0f}",
            'Hacim Oranı':
            f"{volume_ratio:.2f}x",
            'Band Periyodu':
            f"{bb_period}G",
            'Durum':
            "✅ Tüm Kriterler" if criteria_met else "❌"
        }

    elif scan_type == "fibonacci_harmonic_pattern":
        # Fibonacci Retest + Harmonic Pattern Scan
        fib_lookback_period = kwargs.get('fib_lookback_period', 50)
        fib_retracement_min = kwargs.get('fib_retracement_min', 38.2)
        fib_retracement_max = kwargs.get('fib_retracement_max', 50.0)
        fib_support_tolerance = kwargs.get('fib_support_tolerance', 2.0)
        harmonic_pattern_type = kwargs.get('harmonic_pattern_type', "Otomatik")
        harmonic_tolerance = kwargs.get('harmonic_tolerance', 5.0)
        fib_volume_multiplier = kwargs.get('fib_volume_multiplier', 1.3)
        trend_strength_days = kwargs.get('trend_strength_days', 10)

        # Extract Fibonacci and harmonic data
        fib_retracement_detected = analysis.get('fib_retracement_detected',
                                                False)
        harmonic_pattern_detected = analysis.get('harmonic_pattern_detected',
                                                 False)
        fib_support_confirmed = analysis.get('fib_support_confirmed', False)
        volume_confirmed_fib = analysis.get('volume_confirmed_fib', False)

        # All criteria must be met
        criteria_met = fib_retracement_detected and harmonic_pattern_detected and fib_support_confirmed and volume_confirmed_fib

        result_row = {
            'Hisse':
            stock,
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'Fib Geri Çekilme':
            "✅" if fib_retracement_detected else "❌",
            'Harmonik Formasyon':
            "✅" if harmonic_pattern_detected else "❌",
            'Destek Onayı':
            "✅" if fib_support_confirmed else "❌",
            'Hacim Onayı':
            "✅" if volume_confirmed_fib else "❌",
            'Son Hacim':
            f"{analysis['current_volume']:,.0f}",
            'Hacim Oranı':
            f"{volume_ratio:.2f}x",
            'Formasyon':
            harmonic_pattern_type,
            'Durum':
            "✅ Tüm Kriterler" if criteria_met else "❌"
        }

    elif scan_type == "future_scan_3":
        # Placeholder for future scan 3
        criteria_met = False
        result_row = {}

    else:
        # Default to 3 period increase
        criteria_met = (volume_ratio >= min_volume_multiplier
                        and volume_progression)
        result_row = {
            'Hisse':
            stock,
            'Son Hacim':
            f"{analysis['current_volume']:,.0f}",
            'Hacim SMA':
            f"{analysis['volume_sma']:,.0f}",
            'Hacim Oranı':
            f"{volume_ratio:.2f}x",
            'Son Fiyat':
            f"₺{analysis['current_price']:.2f}"
            if analysis['current_price'] else "N/A",
            'Hacim Trendi':
            analysis['volume_trend'],
            '3 Periyot Artış':
            "✅" if volume_progression else "❌",
            'Durum':
            "✅ Her İki Kriter" if criteria_met else "❌"
        }

    return criteria_met, result_row


def run_analysis(analyzer,
                 period,
                 interval,
                 sma_period,
                 min_volume_multiplier,
                 scan_type="3_period_increase",
                 **kwargs):
    """Run the volume analysis and display results"""

    # Modern Progress tracking with metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-container">
            <h5>📊 Tarama Türü</h5>
            <p>{}</p>
        </div>
        """.format(scan_type.replace('_', ' ').title()), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-container">
            <h5>⏱️ Periyod</h5>
            <p>{}</p>
        </div>
        """.format(period), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-container">
            <h5>📈 Interval</h5>
            <p>{}</p>
        </div>
        """.format(interval), unsafe_allow_html=True)
    
    with col4:
        market_status = get_market_status()
        status_color = "#26a69a" if market_status[0] == "AÇIK" else "#ef5350"
        st.markdown(f"""
        <div class="metric-container" style="background: {status_color};">
            <h5>🏛️ Piyasa</h5>
            <p>{market_status[0]}</p>
        </div>
        """, unsafe_allow_html=True)

    progress_bar = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    try:
        # Update status
        status_text.text("🔍 BIST hisse senetleri listesi alınıyor...")
        progress_bar.progress(10)

        # Get BIST stocks
        restrict = kwargs.get('restrict_symbols')
        bist_stocks = restrict if restrict else analyzer.get_bist_stocks()
        if not bist_stocks:
            st.error("BIST hisse senetleri listesi alınamadı!")
            return

        status_text.text(
            f"{len(bist_stocks)} hisse senedi bulundu. Analiz başlıyor...")
        progress_bar.progress(20)

        # Analyze stocks
        results = []
        total_stocks = len(bist_stocks)

        for i, stock in enumerate(bist_stocks):
            try:
                # Update progress
                progress = 20 + (70 * (i + 1) / total_stocks)
                progress_bar.progress(int(progress))
                status_text.text(
                    f"Analiz ediliyor: {stock} ({i+1}/{total_stocks})")

                # Analyze single stock with scan-specific parameters
                if scan_type == "ema_golden_cross":
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        ema_short=kwargs.get('ema_short', 50),
                        ema_long=kwargs.get('ema_long', 200),
                        volume_period=kwargs.get('volume_period', 20))
                elif scan_type == "macd_zero_breakout":
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        macd_fast=kwargs.get('macd_fast', 12),
                        macd_slow=kwargs.get('macd_slow', 26),
                        macd_signal=kwargs.get('macd_signal', 9),
                        sideways_days=kwargs.get('sideways_days', 5),
                        sideways_threshold=kwargs.get('sideways_threshold',
                                                      2.0))
                elif scan_type == "vwap_support_test":
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        vwap_period=kwargs.get('vwap_period', 20),
                        support_tolerance=kwargs.get('support_tolerance', 1.0),
                        bottom_lookback=kwargs.get('bottom_lookback', 10))
                elif scan_type == "triple_volume_confirmation":
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        volume_avg_period=kwargs.get('volume_avg_period', 20),
                        volume_multiplier_triple=kwargs.get(
                            'volume_multiplier_triple', 2.0),
                        rsi_period=kwargs.get('rsi_period', 14),
                        rsi_min=kwargs.get('rsi_min', 60),
                        rsi_max=kwargs.get('rsi_max', 70),
                        obv_period=kwargs.get('obv_period', 20),
                        obv_threshold=kwargs.get('obv_threshold', 95))
                elif scan_type == "triangle_breakout":
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        triangle_period=kwargs.get('triangle_period', 20),
                        convergence_threshold=kwargs.get(
                            'convergence_threshold', 3.0),
                        volume_decline_period=kwargs.get(
                            'volume_decline_period', 10),
                        volume_decline_threshold=kwargs.get(
                            'volume_decline_threshold', 20),
                        breakout_volume_increase=kwargs.get(
                            'breakout_volume_increase', 40),
                        breakout_direction=kwargs.get('breakout_direction',
                                                      "Yukarı"))
                elif scan_type == "rsi_divergence_breakout":
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        rsi_period=kwargs.get('rsi_period', 14),
                        divergence_period=kwargs.get('divergence_period', 20),
                        min_divergence_strength=kwargs.get(
                            'min_divergence_strength', 0.6),
                        resistance_period=kwargs.get('resistance_period', 10),
                        resistance_breakout_percent=kwargs.get(
                            'resistance_breakout_percent', 1.5),
                        volume_breakout_multiplier=kwargs.get(
                            'volume_breakout_multiplier', 1.5),
                        rsi_oversold_threshold=kwargs.get(
                            'rsi_oversold_threshold', 30))
                elif scan_type == "bollinger_squeeze_breakout":
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        bb_period=kwargs.get('bb_period', 20),
                        bb_std_dev=kwargs.get('bb_std_dev', 2.0),
                        squeeze_period=kwargs.get('squeeze_period', 6),
                        squeeze_percentile=kwargs.get('squeeze_percentile',
                                                      10),
                        upper_band_breakout_percent=kwargs.get(
                            'upper_band_breakout_percent', 1.0),
                        volume_squeeze_multiplier=kwargs.get(
                            'volume_squeeze_multiplier', 1.5),
                        consecutive_days=kwargs.get('consecutive_days', 2))
                elif scan_type == "fibonacci_harmonic_pattern":
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        fib_lookback_period=kwargs.get('fib_lookback_period',
                                                       50),
                        fib_retracement_min=kwargs.get('fib_retracement_min',
                                                       38.2),
                        fib_retracement_max=kwargs.get('fib_retracement_max',
                                                       50.0),
                        fib_support_tolerance=kwargs.get(
                            'fib_support_tolerance', 2.0),
                        harmonic_pattern_type=kwargs.get(
                            'harmonic_pattern_type', "Otomatik"),
                        harmonic_tolerance=kwargs.get('harmonic_tolerance',
                                                      5.0),
                        fib_volume_multiplier=kwargs.get(
                            'fib_volume_multiplier', 1.3),
                        trend_strength_days=kwargs.get('trend_strength_days',
                                                       10))
                else:
                    # Default 3 period increase scan
                    analysis = analyzer.analyze_stock_volume(
                        stock,
                        period=period,
                        interval=interval,
                        sma_period=sma_period,
                        periods_to_check=kwargs.get('periods_to_check', 3))

                if analysis and analysis['current_volume'] > 0:
                    volume_ratio = analysis['current_volume'] / analysis[
                        'volume_sma']
                    volume_progression = analysis.get(
                        'volume_progression_check', False)

                    # Apply different criteria based on scan type
                    criteria_met, result_row = apply_scan_criteria(
                        analysis, volume_ratio, volume_progression,
                        min_volume_multiplier, scan_type, stock, **kwargs)

                    # Add to results if criteria are met
                    if criteria_met:
                        results.append(result_row)

                # Small delay to avoid rate limiting
                time.sleep(0.1)

            except Exception as e:
                st.warning(f"{stock} analiz edilirken hata: {str(e)}")
                continue

        # Complete analysis
        progress_bar.progress(100)
        status_text.text("Analiz tamamlandı!")

        # Display results
        display_results(results, len(bist_stocks), scan_type, **kwargs)

        # Cache results in session for persistence
        try:
            st.session_state['tech_cache'] = {
                'scan_type': scan_type,
                'results': results,
                'total': len(bist_stocks),
                'kwargs': kwargs
            }
        except Exception:
            pass

    except Exception as e:
        st.error(f"Analiz sırasında hata oluştu: {str(e)}")
    finally:
        progress_bar.empty()
        status_text.empty()


def display_results(results, total_analyzed, scan_type="3_period_increase", **kwargs):
    """Display analysis results"""

    # Get scan name for display
    scan_names = {
        "3_period_increase": "Periyot Artış Taraması",
        "ema_golden_cross": "Hacim Patlaması + EMA Golden Cross",
        "macd_zero_breakout": "MACD Zero Line Breakout",
        "vwap_support_test": "VWAP Destek Testi + Yükselen Dip",
        "triple_volume_confirmation": "Üçlü Hacim Onayı",
        "triangle_breakout": "Daralan Üçgen + Hacim Kırılımı",
        "rsi_divergence_breakout": "RSI Diverjans + Trend Kırılımı",
        "bollinger_squeeze_breakout": "Bollinger Band Sıkışması + Breakout",
        "fibonacci_harmonic_pattern": "Fibonacci Retest + Harmonik Yapı"
    }

    scan_display_name = scan_names.get(scan_type, "Bilinmeyen Tarama")
    
    # For 3_period_increase, add the period count to the name
    if scan_type == "3_period_increase":
        periods_to_check = kwargs.get('periods_to_check', 3)
        scan_display_name = f"{periods_to_check} {scan_display_name}"

    # Modern Summary metrics with better styling
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-container">
            <h5>📊 Toplam Analiz</h5>
            <h3>{total_analyzed}</h3>
            <p>hisse tarandı</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-container">
            <h5>🎯 Kriterleri Karşılayan</h5>
            <h3>{len(results)}</h3>
            <p>fırsat bulundu</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        success_rate = (len(results) / total_analyzed * 100) if total_analyzed > 0 else 0
        color = "#26a69a" if success_rate > 5 else "#ff9800" if success_rate > 2 else "#f44336"
        st.markdown(f"""
        <div class="metric-container" style="background: {color};">
            <h5>📈 Başarı Oranı</h5>
            <h3>{success_rate:.1f}%</h3>
            <p>eşleşme oranı</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-container">
            <h5>⏱️ Son Güncelleme</h5>
            <h3>{datetime.now().strftime("%H:%M")}</h3>
            <p>{datetime.now().strftime("%d/%m/%Y")}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Results section with enhanced visualization
    if results:
        st.subheader(f"🎯 {scan_display_name} - En İyi Fırsatlar")
        
        # Convert to DataFrame for better display
        df_results = pd.DataFrame(results)
        
        # Create summary chart
        summary_chart = create_results_summary_chart(df_results)
        if summary_chart:
            st.plotly_chart(summary_chart, use_container_width=True)
        
        # Ek interaktif grafik - Volume vs Fiyat scatter plot
        st.subheader("🎯 İnteraktif Analiz")
        
        try:
            # Volume ve fiyat verilerini hazırla
            volume_col = None
            price_col = None
            
            for col in ['Volume Oranı', 'Hacim Oranı', 'Hacim Çarpanı']:
                if col in df_results.columns:
                    volume_col = col
                    break
            
            for col in ['Fiyat', 'Price', 'Güncel Fiyat']:
                if col in df_results.columns:
                    price_col = col
                    break
            
            if volume_col and price_col and 'Hisse' in df_results.columns:
                # Veriler temizleme
                scatter_data = []
                for idx, row in df_results.iterrows():
                    try:
                        volume_val = row[volume_col]
                        price_val = row[price_col]
                        
                        if isinstance(volume_val, str):
                            volume_clean = float(volume_val.replace('x', '').replace(',', '.'))
                        else:
                            volume_clean = float(volume_val)
                        
                        if isinstance(price_val, str):
                            price_clean = float(price_val.replace(',', '.').replace(' TL', ''))
                        else:
                            price_clean = float(price_val)
                        
                        scatter_data.append({
                            'symbol': row['Hisse'],
                            'volume': volume_clean,
                            'price': price_clean,
                            'size': min(volume_clean * 10, 50)  # Nokta boyutu için
                        })
                    except:
                        continue
                
                if scatter_data:
                    scatter_df = pd.DataFrame(scatter_data)
                    
                    fig_scatter = go.Figure()
                    
                    fig_scatter.add_trace(go.Scatter(
                        x=scatter_df['volume'],
                        y=scatter_df['price'],
                        mode='markers',
                        marker=dict(
                            size=scatter_df['size'],
                            color=scatter_df['volume'],
                            colorscale='Viridis',
                            showscale=True,
                            colorbar=dict(title="Volume Oranı"),
                            line=dict(width=2, color='white'),
                            opacity=0.8
                        ),
                        text=scatter_df['symbol'],
                        hovertemplate='<b>%{text}</b><br>' +
                                    'Volume: %{x:.1f}x<br>' +
                                    'Fiyat: %{y:.2f} TL<extra></extra>',
                        name='Hisseler'
                    ))
                    
                    fig_scatter.update_layout(
                        title='💎 Volume vs Fiyat Analizi (Tıklanabilir)',
                        xaxis_title='Volume Oranı (x)',
                        yaxis_title='Fiyat (TL)',
                        template='plotly_dark',
                        height=400,
                        hovermode='closest'
                    )
                    
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # En yüksek volume'ları vurgula
                    top_volume = scatter_df.nlargest(3, 'volume')
                    if not top_volume.empty:
                        st.info(f"🚀 **En Yüksek Volume:** {', '.join(top_volume['symbol'].tolist())}")
        
        except Exception as e:
            st.warning(f"İnteraktif grafik oluşturulamadı: {e}")
        
        # Enhanced results display with cards
        st.subheader("🏆 Top Sonuçlar")
        
        # Show top 5 results as cards
        top_results = results[:5] if len(results) > 5 else results
        
        for i, result in enumerate(top_results):
            with st.container():
                col_info, col_metrics, col_action = st.columns([3, 3, 1])
                
                with col_info:
                    st.markdown(f"""
                    <div class="scan-result-card">
                        <h4>#{i+1} {result.get('Hisse', 'N/A')}</h4>
                        <p><strong>Fiyat:</strong> {result.get('Fiyat', 'N/A')}</p>
                        <p><strong>Tarih:</strong> {result.get('Tarih', 'N/A')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_metrics:
                    volume_ratio = result.get('Hacim Oranı', result.get('Hacim Çarpanı', 'N/A'))
                    volume_color = "#26a69a" if 'x' in str(volume_ratio) and float(str(volume_ratio).replace('x', '')) > 2 else "#ff9800"
                    
                    st.markdown(f"""
                    <div class="metric-container" style="background: {volume_color};">
                        <h5>Volume</h5>
                        <h3>{volume_ratio}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_action:
                    symbol = result.get('Hisse', '')
                    if symbol:
                        chart_url = f"https://www.tradingview.com/chart/?symbol=BIST:{symbol}"
                        st.link_button("📈", chart_url)
        
        st.markdown("---")

        # Convert to DataFrame for better display
        df_results = pd.DataFrame(results)

        # Sort by volume ratio (handle different column names)
        sort_column = None
        if 'Hacim Oranı' in df_results.columns:
            sort_column = 'Hacim Oranı'
        elif 'Hacim Çarpanı' in df_results.columns:
            sort_column = 'Hacim Çarpanı'

        if sort_column:
            try:
                df_results['sort_ratio'] = df_results[sort_column].str.replace(
                    'x', '').astype(float)
                df_results = df_results.sort_values('sort_ratio',
                                                    ascending=False).drop(
                                                        'sort_ratio', axis=1)
            except:
                # If sorting fails, just display without sorting
                pass

        # Display table
        # Add TradingView chart links (clickable)
        if 'Hisse' in df_results.columns:
            df_results = df_results.copy()
            df_results['Grafik'] = [f"https://www.tradingview.com/chart/?symbol=BIST:{s}" for s in df_results['Hisse']]
        st.dataframe(df_results, use_container_width=True, hide_index=True)
        # Quick open section
        if 'Hisse' in df_results.columns:
            with st.expander("🧭 Hızlı Grafik Aç (TradingView)", expanded=False):
                selected = st.selectbox("Hisse seç", options=df_results['Hisse'].tolist())
                link = f"https://www.tradingview.com/chart/?symbol=BIST:{selected}"
                st.link_button("Grafiği Aç", url=link, use_container_width=True)

        # Download option
        csv = df_results.to_csv(index=False)
        scan_code_for_filename = scan_type.replace("_", "-")
        st.download_button(
            label="📥 Sonuçları CSV olarak İndir",
            data=csv,
            file_name=
            f"bist_{scan_code_for_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv")

        # Save to repository
        st.markdown("---")
        colA, colB = st.columns([1,1])
        with colA:
            if st.button("💾 Bu Sonucu Depoya Kaydet", use_container_width=True):
                path = save_results_df(df_results, category="technical", scan_code=scan_type)
                if path:
                    st.success(f"Kaydedildi: {path}")
                    prune_saved_files("technical", scan_type, keep=st.session_state.get('save_keep', 10))
        with colB:
            auto = st.checkbox("Yeni sonuçları otomatik kaydet (teknik)", value=st.session_state.get('auto_save', True))
            if auto:
                p = save_results_df(df_results, category="technical", scan_code=scan_type)
                if p:
                    prune_saved_files("technical", scan_type, keep=st.session_state.get('save_keep', 10))

    else:
        st.warning(
            "🔍 Belirtilen kriterleri karşılayan hisse senedi bulunamadı.")
        st.info("💡 İpucu: Minimum hacim çarpanını düşürmeyi deneyin.")

    # Timestamp
    st.markdown(
        f"**Son Analiz:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")


def fundamental_analysis_section():
    """Fundamental analysis and screening section"""
    st.header("📋 Temel Analiz ve Tarama")
    st.markdown("Finansal oranlar ve temel analiz kriterleri ile hisse senedi taraması")
    st.markdown("---")
    
    # Sidebar for fundamental analysis controls
    st.sidebar.header("📋 Temel Analiz Ayarları")
    
    # Data period selection for fundamental analysis
    col1, col2 = st.sidebar.columns([1, 1])
    
    with col1:
        # Financial data period options
        fundamental_period_options = {
            "Son 3 Ay": "3mo",
            "Son 6 Ay": "6mo", 
            "Son Yıl": "1y",
            "Son 2 Yıl": "2y",
            "Son 5 Yıl": "5y"
        }
        
        selected_period_display = st.selectbox(
            "Finansal Veri Periyodu",
            options=list(fundamental_period_options.keys()),
            index=1,  # Default to "Son Yıl"
            help="Temel analiz için kullanılacak finansal veri periyodu")
        
        fundamental_period = fundamental_period_options[selected_period_display]
    
    with col2:
        # Market cap filter
        market_cap_filter = st.selectbox(
            "Piyasa Değeri Filtresi",
            options=["Tümü", "Büyük Ölçek (>10M TL)", "Orta Ölçek (1M-10M TL)", "Küçük Ölçek (<1M TL)"],
            index=0,
            help="Piyasa değerine göre filtreleme")
    
    st.sidebar.markdown("---")
    
    # Single stock analysis input (list selection only)
    st.subheader("🎯 Tekil Hisse Analizi")
    analyzer_for_list = BISTVolumeAnalyzer()
    with st.expander("BIST listesinden seç", expanded=True):
        try:
            bist_list = analyzer_for_list.get_bist_stocks()
        except Exception:
            bist_list = []
        selected_from_list = st.selectbox("BIST Hisse Seç", options=[""] + bist_list, index=0)
        analyze_list_btn = st.button("Listeden Analiz Et")

    # unify triggers
    chosen_symbol = None
    if analyze_list_btn and selected_from_list:
        chosen_symbol = selected_from_list.strip().upper()

    if chosen_symbol:
        analyzer = BISTVolumeAnalyzer()
        with st.spinner(f"{chosen_symbol} analiz ediliyor..."):
            res = analyzer.analyze_single_stock(chosen_symbol, fundamental_period)
        if not res:
            st.error("Veri bulunamadı veya kriterler için yeterli veri yok")
        else:
            left, right = st.columns([1, 1])
            with left:
                st.metric("Toplam Puan", f"{res['total_points']}/30", help="Max: 30 (20 temel + 10 teknik)")
                st.metric("Temel Puan", f"{res['fundamental_points']}/20")
                st.metric("Teknik Puan", f"{res['technical_points']}/10")
                st.metric("Öneri", res['recommendation'])
            with right:
                st.metric("Fiyat", f"{res['price']:.2f} ₺")

            st.markdown("### 🧮 Temel Analiz Kırılımı")
            fdf = pd.DataFrame(res['fundamental_breakdown'])
            st.dataframe(fdf, hide_index=True)

            st.markdown("### 📈 Teknik Analiz Kırılımı")
            tdf = pd.DataFrame(res['technical_breakdown'])
            st.dataframe(tdf, hide_index=True)

    st.markdown("---")

    # Fundamental scanning type selection
    st.sidebar.header("Temel Tarama Türü")
    
    fundamental_scan_types = {
        "P/E Oranı Taraması": "pe_ratio_scan",
        "P/B Oranı Taraması": "pb_ratio_scan", 
        "ROE Taraması": "roe_scan",
        "Borç/Özkaynak Taraması": "debt_equity_scan",
        "Temettü Verimi Taraması": "dividend_yield_scan",
        "Gelir Artışı Taraması": "revenue_growth_scan",
        "Net Kar Marjı Taraması": "profit_margin_scan",
        "Kombine Değer Taraması": "combined_value_scan",
        "🏆 Kapsamlı Puanlama (30 Puan)": "comprehensive_scoring"
    }
    
    selected_fundamental_scan = st.sidebar.selectbox(
        "🔍 Temel Tarama Seçimi",
        options=list(fundamental_scan_types.keys()),
        index=0,
        help="Farklı temel analiz kriterlerini seçebilirsiniz")
    
    fundamental_scan_code = fundamental_scan_types[selected_fundamental_scan]
    
    st.sidebar.markdown("---")
    
    # Scan-specific settings for fundamental analysis
    # Default values for all parameters
    pe_min = 5.0
    pe_max = 15.0
    pb_min = 0.5
    pb_max = 2.0
    roe_min = 15.0
    roe_max = 50.0
    debt_equity_min = 0.0
    debt_equity_max = 1.0
    dividend_min = 3.0
    dividend_max = 15.0
    revenue_growth_min = 10.0
    revenue_growth_max = 50.0
    profit_margin_min = 10.0
    profit_margin_max = 40.0
    # Combined scan defaults
    combined_pe_max = 15.0
    combined_pb_max = 2.0
    combined_roe_min = 15.0
    combined_debt_max = 1.0
    
    if fundamental_scan_code == "pe_ratio_scan":
        st.sidebar.subheader("P/E Oranı Ayarları")
        
        pe_min = st.sidebar.number_input(
            "Minimum P/E Oranı",
            min_value=0.1,
            max_value=50.0,
            value=5.0,
            step=0.5,
            help="Minimum fiyat/kazanç oranı")
        
        pe_max = st.sidebar.number_input(
            "Maksimum P/E Oranı",
            min_value=0.1,
            max_value=100.0,
            value=15.0,
            step=0.5,
            help="Maksimum fiyat/kazanç oranı")
        
        # Criteria summary
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write("**P/E Oranı Kriterleri:**")
            st.write(f"• P/E Oranı: {pe_min} - {pe_max} arasında")
            st.write(f"• Piyasa Değeri: {market_cap_filter}")
            st.write(f"• Veri Periyodu: {selected_period_display}")
    
    elif fundamental_scan_code == "pb_ratio_scan":
        st.sidebar.subheader("P/B Oranı Ayarları")
        
        pb_min = st.sidebar.number_input(
            "Minimum P/B Oranı",
            min_value=0.1,
            max_value=10.0,
            value=0.5,
            step=0.1,
            help="Minimum fiyat/defter değeri oranı")
        
        pb_max = st.sidebar.number_input(
            "Maksimum P/B Oranı",
            min_value=0.1,
            max_value=10.0,
            value=2.0,
            step=0.1,
            help="Maksimum fiyat/defter değeri oranı")
        
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write("**P/B Oranı Kriterleri:**")
            st.write(f"• P/B Oranı: {pb_min} - {pb_max} arasında")
            st.write(f"• Piyasa Değeri: {market_cap_filter}")
            st.write(f"• Veri Periyodu: {selected_period_display}")
    
    elif fundamental_scan_code == "roe_scan":
        st.sidebar.subheader("ROE Ayarları")
        
        roe_min = st.sidebar.number_input(
            "Minimum ROE (%)",
            min_value=0.0,
            max_value=100.0,
            value=15.0,
            step=1.0,
            help="Minimum özkaynak karlılığı yüzdesi")
        
        roe_max = st.sidebar.number_input(
            "Maksimum ROE (%)",
            min_value=0.0,
            max_value=200.0,
            value=50.0,
            step=1.0,
            help="Maksimum özkaynak karlılığı yüzdesi")
        
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write("**ROE Kriterleri:**")
            st.write(f"• ROE: {roe_min}% - {roe_max}% arasında")
            st.write(f"• Piyasa Değeri: {market_cap_filter}")
            st.write(f"• Veri Periyodu: {selected_period_display}")
    
    elif fundamental_scan_code == "debt_equity_scan":
        st.sidebar.subheader("Borç/Özkaynak Ayarları")
        
        debt_equity_min = st.sidebar.number_input(
            "Minimum Borç/Özkaynak",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.1,
            help="Minimum borç/özkaynak oranı")
        
        debt_equity_max = st.sidebar.number_input(
            "Maksimum Borç/Özkaynak",
            min_value=0.0,
            max_value=10.0,
            value=1.0,
            step=0.1,
            help="Maksimum borç/özkaynak oranı (düşük borçlu şirketler için)")
        
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write("**Borç/Özkaynak Kriterleri:**")
            st.write(f"• Borç/Özkaynak: {debt_equity_min} - {debt_equity_max} arasında")
            st.write(f"• Piyasa Değeri: {market_cap_filter}")
            st.write(f"• Veri Periyodu: {selected_period_display}")
            st.info("💡 Düşük borç/özkaynak oranı daha güvenli şirketleri gösterir")
    
    elif fundamental_scan_code == "dividend_yield_scan":
        st.sidebar.subheader("Temettü Verimi Ayarları")
        
        dividend_min = st.sidebar.number_input(
            "Minimum Temettü Verimi (%)",
            min_value=0.0,
            max_value=20.0,
            value=3.0,
            step=0.5,
            help="Minimum temettü getirisi yüzdesi")
        
        dividend_max = st.sidebar.number_input(
            "Maksimum Temettü Verimi (%)",
            min_value=0.0,
            max_value=30.0,
            value=15.0,
            step=0.5,
            help="Maksimum temettü getirisi yüzdesi")
        
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write("**Temettü Verimi Kriterleri:**")
            st.write(f"• Temettü Verimi: {dividend_min}% - {dividend_max}% arasında")
            st.write(f"• Piyasa Değeri: {market_cap_filter}")
            st.write(f"• Veri Periyodu: {selected_period_display}")
    
    elif fundamental_scan_code == "revenue_growth_scan":
        st.sidebar.subheader("Gelir Artışı Ayarları")
        
        revenue_growth_min = st.sidebar.number_input(
            "Minimum Gelir Artışı (%)",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=1.0,
            help="Minimum yıllık gelir artışı yüzdesi")
        
        revenue_growth_max = st.sidebar.number_input(
            "Maksimum Gelir Artışı (%)",
            min_value=0.0,
            max_value=200.0,
            value=50.0,
            step=1.0,
            help="Maksimum yıllık gelir artışı yüzdesi")
        
        revenue_period = st.sidebar.selectbox(
            "Gelir Karşılaştırma Periyodu",
            options=["Son 1 Yıl", "Son 2 Yıl", "Son 3 Yıl"],
            index=0,
            help="Gelir artışının hangi periyot için hesaplanacağı")
        
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write("**Gelir Artışı Kriterleri:**")
            st.write(f"• Gelir Artışı: {revenue_growth_min}% - {revenue_growth_max}% arasında")
            st.write(f"• Karşılaştırma Periyodu: {revenue_period}")
            st.write(f"• Piyasa Değeri: {market_cap_filter}")
            st.write(f"• Veri Periyodu: {selected_period_display}")
            st.info("💡 Yüksek gelir artışı büyüyen şirketleri gösterir")
    
    elif fundamental_scan_code == "profit_margin_scan":
        st.sidebar.subheader("Net Kar Marjı Ayarları")
        
        profit_margin_min = st.sidebar.number_input(
            "Minimum Net Kar Marjı (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
            help="Minimum net kar marjı yüzdesi")
        
        profit_margin_max = st.sidebar.number_input(
            "Maksimum Net Kar Marjı (%)",
            min_value=0.0,
            max_value=100.0,
            value=40.0,
            step=1.0,
            help="Maksimum net kar marjı yüzdesi")
        
        with st.sidebar.expander("📋 Tarama Kriterleri", expanded=False):
            st.write("**Net Kar Marjı Kriterleri:**")
            st.write(f"• Net Kar Marjı: {profit_margin_min}% - {profit_margin_max}% arasında")
            st.write(f"• Piyasa Değeri: {market_cap_filter}")
            st.write(f"• Veri Periyodu: {selected_period_display}")
            st.info("💡 Yüksek kar marjı verimli şirketleri gösterir")
    
    elif fundamental_scan_code == "combined_value_scan":
        st.sidebar.subheader("Kombine Değer Taraması Ayarları")
        
        st.sidebar.markdown("**P/E Oranı Kriterleri:**")
        combined_pe_max = st.sidebar.number_input(
            "Maksimum P/E Oranı",
            min_value=1.0,
            max_value=50.0,
            value=15.0,
            step=0.5,
            help="Değerli hisseler için maksimum P/E")
        
        st.sidebar.markdown("**P/B Oranı Kriterleri:**")
        combined_pb_max = st.sidebar.number_input(
            "Maksimum P/B Oranı",
            min_value=0.1,
            max_value=10.0,
            value=2.0,
            step=0.1,
            help="Değerli hisseler için maksimum P/B")
        
        st.sidebar.markdown("**ROE Kriterleri:**")
        combined_roe_min = st.sidebar.number_input(
            "Minimum ROE (%)",
            min_value=0.0,
            max_value=100.0,
            value=15.0,
            step=1.0,
            help="Kaliteli şirketler için minimum ROE")
        
        st.sidebar.markdown("**Borç/Özkaynak Kriterleri:**")
        combined_debt_max = st.sidebar.number_input(
            "Maksimum Borç/Özkaynak",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Güvenli şirketler için maksimum borç oranı")
        
        with st.sidebar.expander("📋 Kombine Tarama Kriterleri", expanded=True):
            st.write("**Tüm Kriterler Birlikte:**")
            st.write(f"• P/E ≤ {combined_pe_max}")
            st.write(f"• P/B ≤ {combined_pb_max}")
            st.write(f"• ROE ≥ {combined_roe_min}%")
            st.write(f"• B/Ö ≤ {combined_debt_max}")
            st.write(f"• Piyasa Değeri: {market_cap_filter}")
            st.success("💎 En kaliteli değer hisselerini bulur!")
    
    # Comprehensive scoring ayarları - buton dışında görünmeli
    if fundamental_scan_code == "comprehensive_scoring":
        st.sidebar.subheader("🏆 Kapsamlı Puanlama 30 Ayarları")
        
        # Ana filtre
        min_points = st.sidebar.slider(
            "Minimum Toplam Puan",
            min_value=0, max_value=30, value=15, step=1,
            help="Bu puanın altındaki hisseler listeye alınmaz")
        
        # Temel Analiz Kriterleri (20 Puan)
        with st.sidebar.expander("📊 Temel Analiz Kriterleri (20 Puan)", expanded=True):
            st.write("**1. F/K Oranı (2 Puan)**")
            pe_excellent = st.number_input("F/K İyi (<)", value=15.0, step=0.5, help="İyi (2P): F/K < bu değer")
            pe_good = st.number_input("F/K Orta (<)", value=25.0, step=0.5, help="Orta (1P): F/K < bu değer")
            
            st.write("**2. PD/DD Oranı (2 Puan)**")
            pb_excellent = st.number_input("PD/DD İyi (<)", value=1.0, step=0.1, help="İyi (2P): PD/DD < bu değer")
            pb_good = st.number_input("PD/DD Orta (<)", value=2.0, step=0.1, help="Orta (1P): PD/DD < bu değer")
            
            st.write("**3. ROE Oranı (2 Puan)**")
            roe_excellent = st.number_input("ROE İyi (>%)", value=15.0, step=1.0, help="İyi (2P): ROE > bu değer")
            roe_good = st.number_input("ROE Orta (>%)", value=10.0, step=1.0, help="Orta (1P): ROE > bu değer")
            
            st.write("**4. Net Kâr Marjı (2 Puan)**")
            margin_excellent = st.number_input("Kâr Marjı İyi (>%)", value=10.0, step=1.0, help="İyi (2P): Marj > bu değer")
            margin_good = st.number_input("Kâr Marjı Orta (>%)", value=5.0, step=1.0, help="Orta (1P): Marj > bu değer")
            
            st.write("**5. Borç/Özkaynak Oranı (2 Puan)**")
            debt_excellent = st.number_input("Borç/ÖK İyi (<)", value=1.0, step=0.1, help="İyi (2P): Borç/ÖK < bu değer")
            debt_good = st.number_input("Borç/ÖK Orta (<)", value=2.0, step=0.1, help="Orta (1P): Borç/ÖK < bu değer")
        
        # Teknik Analiz Kriterleri (10 Puan)
        with st.sidebar.expander("📈 Teknik Analiz Kriterleri (10 Puan)", expanded=True):
            st.write("**1. RSI (14) Analizi (2 Puan)**")
            rsi_good_min = st.number_input("RSI İyi Min", value=40.0, step=1.0, help="İyi aralık minimum")
            rsi_good_max = st.number_input("RSI İyi Max", value=60.0, step=1.0, help="İyi aralık maksimum")
            
            st.write("**2. SMA Analizi (4 Puan)**")
            sma_tolerance = st.number_input("SMA Tolerans (%)", value=2.0, step=0.5, help="SMA civarında tolerans")
            
            st.write("**3. Hacim Analizi (2 Puan)**")
            volume_multiplier = st.number_input("Hacim Çarpanı", value=1.2, step=0.1, help="20 gün ort. hacim çarpanı")
            
            st.write("**4. MACD Tolerans (2 Puan)**")
            macd_tolerance = st.number_input("MACD Sıfır Tolerans", value=0.01, step=0.001, help="MACD sıfır civarı toleransı")
        
        # Filtreleme Seçenekleri
        with st.sidebar.expander("🔧 Ek Filtreler", expanded=False):
            min_fundamental_points = st.slider("Min Temel Puan", 0, 20, 8, help="Minimum temel analiz puanı")
            min_technical_points = st.slider("Min Teknik Puan", 0, 10, 4, help="Minimum teknik analiz puanı")
            
            balance_requirement = st.checkbox("Denge Şartı", value=True, help="Her kategoriden minimum %40 puan şartı")
        
        # Kriterler özeti
        with st.sidebar.expander("📋 Puanlama Kriterleri Özeti", expanded=False):
            st.markdown("""
            **Temel Analiz (20 Puan):**
            - F/K Oranı: 2P
            - PD/DD Oranı: 2P  
            - ROE: 2P
            - Net Kâr Marjı: 2P
            - Borç/Özkaynak: 2P
            - Satış Büyümesi: 2P
            - Net Kâr Büyümesi: 2P
            - Cari Oran: 2P
            - Nakit Akışı: 2P
            - FD/FAVÖK: 2P
            
            **Teknik Analiz (10 Puan):**
            - SMA200 Pozisyonu: 2P
            - SMA50 Pozisyonu: 2P
            - RSI Analizi: 2P
            - MACD Sinyali: 2P
            - Hacim Analizi: 2P
            
            **Toplam: 30 Puan**
            """)
        
        # Parametreleri analyzer'a geçirmek için dictionary oluştur
        scoring_params = {
            'pe_excellent': pe_excellent,
            'pe_good': pe_good,
            'pb_excellent': pb_excellent,
            'pb_good': pb_good,
            'roe_excellent': roe_excellent,
            'roe_good': roe_good,
            'margin_excellent': margin_excellent,
            'margin_good': margin_good,
            'debt_excellent': debt_excellent,
            'debt_good': debt_good,
            'rsi_good_min': rsi_good_min,
            'rsi_good_max': rsi_good_max,
            'sma_tolerance': sma_tolerance,
            'volume_multiplier': volume_multiplier,
            'macd_tolerance': macd_tolerance,
            'min_fundamental_points': min_fundamental_points,
            'min_technical_points': min_technical_points,
            'balance_requirement': balance_requirement
        }
    
    st.sidebar.markdown("---")
    
    did_run = False
    # Analysis button
    if st.sidebar.button("🔍 Temel Analizi Başlat", type="primary"):
        did_run = True
        st.info(f"**Seçilen Tarama:** {selected_fundamental_scan}")
        
        # Initialize analyzer
        analyzer = BISTVolumeAnalyzer()
        
        # Comprehensive scoring path
        if fundamental_scan_code == "comprehensive_scoring":
            # Progress widgets
            progress_bar = st.progress(0)
            status_text = st.empty()

            with st.spinner("Kapsamlı puanlama taraması yapılıyor..."):
                try:
                    stocks = analyzer.get_bist_stocks()
                    total = len(stocks)
                    status_text.text(f"{total} hisse bulundu. Analiz başlıyor...")
                    progress_bar.progress(5)

                    def cb(i, t, sym):
                        p = 5 + int(90 * i / max(1, t))
                        progress_bar.progress(min(p, 95))
                        status_text.text(f"Analiz ediliyor: {sym} ({i}/{t})")

                    results = analyzer.analyze_stocks_comprehensive(
                        period=fundamental_period,
                        min_total_points=min_points,
                        progress_callback=cb,
                        limit=None,
                        sleep_sec=0.08,
                        scoring_params=scoring_params
                    )

                    progress_bar.progress(100)
                    status_text.text("Tamamlandı")

                    if not results:
                        st.warning("Kriterlere uyan hisse bulunamadı.")
                    else:
                        st.success(f"{len(results)} hisse bulundu.")

                        # Prepare display
                        rows = []
                        for r in results:
                            rows.append({
                                'Hisse': r['symbol'],
                                'Toplam': r['total_points'],
                                'Temel': r['fundamental_points'],
                                'Teknik': r['technical_points'],
                                'Öneri': r['recommendation'],
                                'Fiyat (₺)': f"{r.get('price', 0):.2f}",
                                'P/E': f"{r.get('pe_ratio', 0):.1f}" if r.get('pe_ratio') is not None else "-",
                                'P/B': f"{r.get('pb_ratio', 0):.1f}" if r.get('pb_ratio') is not None else "-",
                            })

                        df = pd.DataFrame(rows)
                        # Sort by Toplam desc then Temel desc
                        df = df.sort_values(['Toplam', 'Temel'], ascending=[False, False])
                        st.dataframe(df, use_container_width=True, hide_index=True)

                        # Download
                        csv = df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="📥 Skor Sonuçlarını İndir",
                            data=csv,
                            file_name=f"kapsamli_puanlama_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )

                        # Cache results for persistence
                        try:
                            st.session_state['fund_cache'] = {
                                'scan_type': 'comprehensive_scoring',
                                'df': df
                            }
                        except Exception:
                            pass

                        # Save to repository
                        st.markdown("---")
                        colA, colB = st.columns([1,1])
                        with colA:
                            if st.button("💾 Bu Sonucu Depoya Kaydet (Puanlama)", use_container_width=True):
                                path = save_results_df(df, category="fundamental", scan_code="comprehensive_scoring")
                                if path:
                                    st.success(f"Kaydedildi: {path}")
                                    prune_saved_files("fundamental", "comprehensive_scoring", keep=st.session_state.get('save_keep', 10))
                        with colB:
                            auto_c = st.checkbox("Yeni sonuçları otomatik kaydet (puanlama)", value=st.session_state.get('auto_save', True))
                            if auto_c:
                                p = save_results_df(df, category="fundamental", scan_code="comprehensive_scoring")
                                if p:
                                    prune_saved_files("fundamental", "comprehensive_scoring", keep=st.session_state.get('save_keep', 10))

                except Exception as e:
                    st.error(f"Tarama hatası: {e}")
                finally:
                    progress_bar.empty()
                    status_text.empty()
            return

        # Prepare scan parameters
        scan_params = {
            'period': fundamental_period,
            'min_market_cap': 100,  # Million TL
            'max_market_cap': 100000,  # Million TL
        }
        
        # Add specific parameters based on scan type
        if fundamental_scan_code == "pe_ratio_scan":
            scan_params['min_pe'] = pe_min
            scan_params['max_pe'] = pe_max
            scan_type = 'low_pe'
        elif fundamental_scan_code == "pb_ratio_scan":
            scan_params['min_pb'] = pb_min
            scan_params['max_pb'] = pb_max  
            scan_type = 'low_pb'
        elif fundamental_scan_code == "roe_scan":
            scan_params['min_roe'] = roe_min
            scan_params['max_roe'] = roe_max
            scan_type = 'high_roe'
        elif fundamental_scan_code == "debt_equity_scan":
            scan_params['min_debt_equity'] = debt_equity_min
            scan_params['max_debt_equity'] = debt_equity_max
            scan_type = 'low_debt'
        elif fundamental_scan_code == "dividend_yield_scan":
            scan_params['min_dividend'] = dividend_min
            scan_params['max_dividend'] = dividend_max
            scan_type = 'dividend'
        elif fundamental_scan_code == "revenue_growth_scan":
            scan_params['min_revenue_growth'] = revenue_growth_min
            scan_params['max_revenue_growth'] = revenue_growth_max
            scan_type = 'revenue_growth'
        elif fundamental_scan_code == "profit_margin_scan":
            scan_params['min_profit_margin'] = profit_margin_min
            scan_params['max_profit_margin'] = profit_margin_max
            scan_type = 'profit_margin'
        elif fundamental_scan_code == "combined_value_scan":
            scan_params['max_pe'] = combined_pe_max
            scan_params['max_pb'] = combined_pb_max
            scan_params['min_roe'] = combined_roe_min
            scan_params['max_debt_equity'] = combined_debt_max
            scan_type = 'combined_value'
        else:
            scan_type = 'growth'  # Default
        
        # Progress indicator
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner(f'{selected_fundamental_scan} yapılıyor...'):
            try:
                status_text.text("BIST hisse senetleri listesi alınıyor...")
                progress_bar.progress(10)
                
                # Get BIST stocks count for progress calculation
                bist_stocks = analyzer.get_bist_stocks()
                total_stocks = len(bist_stocks)
                scan_limit = total_stocks  # Scan all stocks, no limit
                
                status_text.text(f"{total_stocks} hisse senedi bulundu. Tüm hisseler taranacak...")
                progress_bar.progress(20)
                
                # Progress callback function
                def update_progress(current, total, symbol):
                    progress = 20 + (70 * current / total)
                    progress_bar.progress(int(progress))
                    status_text.text(f"Analiz ediliyor: {symbol} ({current}/{total})")
                
                # Run fundamental screening with progress tracking
                results = analyzer.screen_stocks_fundamental(scan_type, scan_params, progress_callback=update_progress)
                
                status_text.text("Sonuçlar hazırlanıyor...")
                progress_bar.progress(100)
                
                # Display results
                if results:
                    st.success(f"✅ {len(results)} hisse bulundu!")
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Toplam Hisse", len(analyzer.get_bist_stocks()))
                    
                    with col2:
                        st.metric("Kriterleri Karşılayan", len(results))
                    
                    with col3:
                        success_rate = (len(results) / len(analyzer.get_bist_stocks())) * 100
                        st.metric("Başarı Oranı", f"{success_rate:.1f}%")
                    
                    st.markdown("---")
                    
                    # Results table
                    st.subheader("📊 Tarama Sonuçları")
                    
                    # Prepare results for display
                    display_results = []
                    for stock in results:
                        display_results.append({
                            'Hisse': stock['symbol'],
                            'Güncel Fiyat': f"{stock['current_price']:.2f} ₺",
                            'P/E': f"{stock.get('pe_ratio', 0):.1f}",
                            'P/B': f"{stock.get('pb_ratio', 0):.1f}",
                            'ROE': f"{stock.get('roe', 0):.1f}%",
                            'B/Ö': f"{stock.get('debt_equity_ratio', 0):.1f}",
                            'Gelir↗': f"{stock.get('revenue_growth', 0):.1f}%",
                            'Kar🎯': f"{stock.get('profit_margin', 0):.1f}%",
                            'Temettü': f"{stock.get('dividend_yield', 0):.1f}%",
                            '1 Aylık': f"{stock.get('price_change_1m', 0):.1f}%",
                            '3 Aylık': f"{stock.get('price_change_3m', 0):.1f}%",
                            'Volatilite': f"{stock.get('volatility', 0):.1f}%"
                        })
                    
                    df_results = pd.DataFrame(display_results)
                    st.dataframe(df_results, use_container_width=True)

                    # Cache results for persistence
                    try:
                        st.session_state['fund_cache'] = {
                            'scan_type': scan_type,
                            'df': df_results
                        }
                    except Exception:
                        pass
                    
                    # Download option
                    csv = df_results.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Sonuçları CSV olarak İndir",
                        data=csv,
                        file_name=f"temel_analiz_{scan_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

                    # Save to repository
                    st.markdown("---")
                    colA, colB = st.columns([1,1])
                    with colA:
                        if st.button("💾 Bu Sonucu Depoya Kaydet (Temel)", use_container_width=True):
                            path = save_results_df(df_results, category="fundamental", scan_code=scan_type)
                            if path:
                                st.success(f"Kaydedildi: {path}")
                                prune_saved_files("fundamental", scan_type, keep=st.session_state.get('save_keep', 10))
                    with colB:
                        auto_f = st.checkbox("Yeni sonuçları otomatik kaydet (temel)", value=st.session_state.get('auto_save', True))
                        if auto_f:
                            p = save_results_df(df_results, category="fundamental", scan_code=scan_type)
                            if p:
                                prune_saved_files("fundamental", scan_type, keep=st.session_state.get('save_keep', 10))
                                st.info("Otomatik olarak kaydedildi.")
                    
                else:
                    st.warning("⚠️ Belirtilen kriterleri karşılayan hisse bulunamadı.")
                    
                    # Summary metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Toplam Hisse", len(analyzer.get_bist_stocks()))
                    
                    with col2:
                        st.metric("Kriterleri Karşılayan", 0)
                    
                    with col3:
                        st.metric("Başarı Oranı", "0%")
                
                progress_bar.empty()
                status_text.empty()
                
            except Exception as e:
                st.error(f"❌ Tarama sırasında hata oluştu: {str(e)}")
                progress_bar.empty()
                status_text.empty()

    # If not run this time, show cached fundamental results for selected scan
    if not did_run:
        cache = st.session_state.get('fund_cache')
        if cache and cache.get('scan_type') == (fundamental_scan_code if fundamental_scan_code != 'comprehensive_scoring' else 'comprehensive_scoring'):
            df_cached = cache.get('df')
            if df_cached is not None and not df_cached.empty:
                st.info("Önceki temel tarama sonuçları gösteriliyor (yeniden tarama yapılmadı).")
                st.dataframe(df_cached, use_container_width=True)
                # Download cached
                csv = df_cached.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 Sonuçları CSV olarak İndir (Önceki)",
                    data=csv,
                    file_name=f"temel_analiz_{cache.get('scan_type')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                # Optional: quick save to repo
                colA, colB = st.columns([1,1])
                with colA:
                    if st.button("💾 Bu Sonucu Depoya Kaydet (Önceki)", use_container_width=True, key="save_prev_fund"):
                        path = save_results_df(df_cached, category="fundamental", scan_code=(cache.get('scan_type') or 'fundamental'))
                        if path:
                            st.success(f"Kaydedildi: {path}")
    
    # Information section for fundamental analysis
    with st.expander("ℹ️ Temel Analiz Hakkında"):
        st.markdown("""
        ### Temel Analiz Özellikleri:
        - **P/E Oranı**: Fiyat/Kazanç oranı analizi - düşük P/E değerli hisseler
        - **P/B Oranı**: Fiyat/Defter değeri oranı analizi - düşük P/B değerli hisseler  
        - **ROE**: Özkaynak karlılığı analizi - yüksek ROE'li şirketler
        - **Borç/Özkaynak**: Finansal kaldıraç analizi - düşük borçlu şirketler
        - **Temettü Verimi**: Temettü getirisi analizi - yüksek temettü veren hisseler
        - **Gelir Artışı**: Büyüme trendi analizi - geliri artan şirketler
        - **Net Kar Marjı**: Karlılık analizi - yüksek kar marjlı şirketler
        - **Kombine Tarama**: Birden fazla kriterin birlikte değerlendirilmesi
        
    ### 🏆 Kapsamlı Puanlama (30P) — Özet
    - Temel (20P): F/K, PD/DD, FD/FAVÖK, Net Kâr Marjı, 3Y Satış/Net Kâr Büyümesi, ROE, Borç/Özkaynak, Cari Oran, Faaliyet Nakit Akımı.
    - Teknik (10P): Fiyat>SMA200, Fiyat>SMA50, RSI, MACD, Hacim>20G Ort.
    - Öneri: 0–7 Güçlü Sat, 8–11 Sat, 12–15 Tut, 16–19 Al, 20+ Güçlü Al.
        
        ### Veri Kaynakları:
        - Finansal tablolar ve rasyolar
        - Geçmiş performans verileri
        - Sektör karşılaştırmaları
        - Piyasa değeri hesaplamaları
        """)

def saved_results_section():
    st.header("📁 Kayıtlı Sonuçlar Deposu")
    st.markdown("Depolanan teknik/temel tarama sonuçlarını burada görüntüleyip indirebilirsiniz.")

    # Manual refresh to ensure users can see newly saved files immediately
    refresh_col, _ = st.columns([1, 3])
    with refresh_col:
        if st.button("🔄 Listeyi Yenile"):
            st.rerun()

    col1, col2 = st.columns([1,2])
    with col1:
        category = st.selectbox("Kategori", options=["technical", "fundamental"], index=0)
        scan_types = list_saved_scan_types(category)
        scan_code = st.selectbox("Tarama Türü", options=scan_types if scan_types else [""], index=0)
        files = list_saved_files(category, scan_code) if scan_code else []
        file_labels = [f.name for f in files]
        selected_file = st.selectbox("Kayıtlar (sondan başa)", options=file_labels if file_labels else [""], index=0)

    with col2:
        if files and selected_file:
            path = next((p for p in files if p.name == selected_file), None)
            if path:
                st.subheader(f"📄 {path.name}")
                df = load_saved_csv(path)
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    st.download_button("📥 CSV İndir", data=df.to_csv(index=False, encoding='utf-8-sig'), file_name=path.name, mime="text/csv")
                del_col1, del_col2 = st.columns([1,3])
                with del_col1:
                    if st.button("🗑️ Sil", type="secondary"):
                        try:
                            path.unlink(missing_ok=True)
                            st.success("Silindi. Yenilemek için menüden tekrar seçin.")
                        except Exception as e:
                            st.error(f"Silinemedi: {e}")
        else:
            st.info("Seçili türde kayıt bulunamadı veya dosya seçilmedi.")


if __name__ == "__main__":
    main()
