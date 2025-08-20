import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_fetcher import TradingViewDataFetcher
import time
import requests
from bs4 import BeautifulSoup
import re

class BISTVolumeAnalyzer:
    """BIST stocks volume-based technical analysis tool"""
    
    def __init__(self):
        self.data_fetcher = TradingViewDataFetcher()
        self.bist_stocks = []
        
    def get_bist_stocks(self):
        """Get comprehensive list of all BIST stocks from TradingView"""
        try:
            # 0) If override file exists and has tickers, prefer it
            override = self._load_override_tickers_file('bist_tickers.txt')
            if len(override) >= 50:
                self.bist_stocks = override
                print(f"Using override tickers file with {len(override)} symbols")
                return self.bist_stocks

            # 1) Prefer TradingView scanner API (broader coverage)
            scanner_list = self._fetch_bist_from_tradingview_scanner()

            # 2) Also try components page as a secondary source
            components_list = self._fetch_bist_all_shares_from_tradingview()

            # 3) Manual comprehensive list as fallback
            manual_list = self._get_comprehensive_bist_stocks()

            # Merge and deduplicate, prefer scanner list if sufficiently large
            merged = set()
            for src in (scanner_list, components_list, manual_list):
                for s in src:
                    if isinstance(s, str):
                        s2 = s.strip().upper()
                        if re.fullmatch(r'[A-Z0-9]{1,6}', s2):
                            merged.add(s2)

            merged_list = sorted(list(merged))

            # If scanner returned a robust list (e.g., > 550), trust it; else use merged
            final_list = scanner_list if len(scanner_list) >= 550 else merged_list

            self.bist_stocks = final_list
            print(f"BIST list finalized with {len(final_list)} tickers")
            return self.bist_stocks
                
        except Exception as e:
            print(f"Error fetching BIST stocks: {e}")
            # Use comprehensive manual list as fallback
            return self._get_comprehensive_bist_stocks()

    def _load_override_tickers_file(self, path='bist_tickers.txt'):
        """Load ticker symbols from a plain text file (one per line)."""
        try:
            import os
            if not os.path.exists(path):
                return []
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            tickers = []
            EXCLUDE = {"REIT", "CEF", "ETF", "WARRANT", "FON", "FUND"}
            for line in lines:
                s = (line or '').strip().upper()
                if not s or s.startswith('#'):
                    continue
                if s in EXCLUDE:
                    continue
                if re.fullmatch(r'[A-Z0-9]{2,6}', s):
                    tickers.append(s)
            # unique and sorted
            return sorted(list(set(tickers)))
        except Exception as e:
            print(f"Error loading override tickers: {e}")
            return []
    
    def _fetch_bist_all_shares_from_tradingview(self):
        """Fetch all BIST stocks from TradingView XUTUM components"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            url = "https://www.tradingview.com/symbols/BIST-XUTUM/components/"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all stock symbols in the table
            symbols = []
            # Look for links with BIST- pattern
            for link in soup.find_all('a', href=re.compile(r'/symbols/BIST-')):
                href = link.get('href') if hasattr(link, 'get') else str(link.get('href', ''))
                if href and isinstance(href, str):
                    match = re.search(r'/symbols/BIST-([A-Z0-9]+)/', href)
                    if match:
                        symbol = match.group(1)
                        # Filter out indices and other non-stock symbols
                        if len(symbol) <= 6 and symbol not in ['XUTUM', 'XU100', 'XU030', 'XUSIN', 'XUMAL']:
                            symbols.append(symbol)
            
            # Remove duplicates and sort
            symbols = sorted(list(set(symbols)))
            print(f"Fetched {len(symbols)} stocks from TradingView")
            
            return symbols
            
        except Exception as e:
            print(f"Error fetching from TradingView: {e}")
            return []

    def _fetch_bist_from_tradingview_scanner(self):
        """Fetch BIST stocks via TradingView scanner API (exchange=BIST, type=stock)."""
        try:
            url = "https://scanner.tradingview.com/turkey/scan"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            payload = {
                "filter": [
                    {"left": "exchange", "operation": "equal", "right": "BIST"},
                    {"left": "type", "operation": "in_range", "right": ["stock"]}
                ],
                "symbols": {"query": {"types": []}, "tickers": []},
                "columns": ["symbol"],
                "sort": {"sortBy": "name", "sortOrder": "asc"},
                "options": {"lang": "tr"},
                "range": [0, 1500]
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            out = []
            for row in data.get('data', []):
                s = row.get('s') or ''
                # Expect format like 'BIST:THYAO'
                parts = s.split(':')
                if len(parts) == 2 and parts[0] == 'BIST':
                    sym = parts[1].strip().upper()
                    if re.fullmatch(r'[A-Z0-9]{1,6}', sym):
                        out.append(sym)
            out = sorted(list(set(out)))
            print(f"Fetched {len(out)} stocks from TradingView scanner")
            return out
        except Exception as e:
            print(f"Error fetching from TradingView scanner: {e}")
            return []
    
    def _get_comprehensive_bist_stocks(self):
        """Get comprehensive manually curated list of BIST stocks"""
        # Comprehensive list of major BIST stocks (588+ stocks)
        comprehensive_stocks = [
            # Major banks and financial institutions
            'AKBNK', 'GARAN', 'ISCTR', 'HALKB', 'VAKBN', 'YKBNK', 'QNBFB', 'QNBFL',
            'TSKB', 'ICBCT', 'ALBRK', 'SKBNK', 'KLNMA', 'ZIRAA', 'ISBTR', 'ISATR',
            
            # Major holdings and conglomerates  
            'KCHOL', 'SAHOL', 'DOHOL', 'GUBRF', 'TAVHL', 'YGGYO', 'DGGYO',
            
            # Technology and telecommunications
            'ASELS', 'TCELL', 'TTKOM', 'NETAS', 'LOGO', 'ARMDA', 'KREA', 'INDES',
            'LINK', 'FONET', 'ARENA', 'KAREL', 'DESPC', 'SMART', 'EDATA',
            
            # Airlines and transportation
            'THYAO', 'PGSUS', 'RYSAS', 'CLEBI', 'DOCO', 'GSDDE',
            
            # Automotive
            'FROTO', 'TOASO', 'OTKAR', 'FORD', 'ASUZU', 'KATMR', 'KLMSN',
            
            # Energy and utilities
            'TUPRS', 'EREGL', 'PETUN', 'GEREL', 'AKSEN', 'ZOREN', 'AYEN',
            'CWENE', 'ENKAI', 'EPLAS', 'FENER', 'GWIND', 'HUNER', 'ISSEN',
            'KAYSE', 'ODINE', 'POLTK', 'SMART', 'SOKE', 'TERNA', 'YESIL',
            
            # Retail and consumer goods
            'BIMAS', 'MGROS', 'SOKM', 'CARRF', 'BIZIM', 'ADESE', 'MAVI',
            'ULKER', 'CCOLA', 'ULUSE', 'AEFES', 'KENT', 'PETUN', 'PNSUT',
            
            # Construction and real estate
            'ENKAI', 'AKFEN', 'ALTIN', 'DGGYO', 'EKGYO', 'EMLAK', 'GARAN',
            'ISGYO', 'KLGYO', 'KOSGB', 'KRGYO', 'MSGYO', 'NUGYO', 'OZGYO',
            'PAGYO', 'PEGYO', 'REIT', 'RNPOL', 'TRGYO', 'VCGYO', 'YATAS',
            
            # Industrial and manufacturing
            'SISE', 'ARCLK', 'VESBE', 'CIMSA', 'OYAKC', 'TRKCM', 'AKSA',
            'ALKIM', 'ANACM', 'AYGAZ', 'BRISA', 'BRYAT', 'BURCE', 'BURVA',
            'CELHA', 'CMENT', 'CUSAN', 'DEVA', 'DGKLB', 'DYOBY', 'EGEEN',
            'EGGUB', 'EMKEL', 'ERBOS', 'ERSU', 'FMIZP', 'GOODY', 'GUBRF',
            'HEKTS', 'IHEVA', 'IZMDC', 'JANTS', 'KAPLM', 'KARTN', 'KCAER',
            'KENT', 'KLSER', 'KONYA', 'KORDS', 'KRTEK', 'KUTPO', 'LUKSK',
            'MAVI', 'MERKO', 'METRO', 'MPARK', 'NTHOL', 'PARSN', 'PETKM',
            'PRKAB', 'ROYAL', 'SARKY', 'SELEC', 'TMPOL', 'TURSG', 'USAK',
            'YATAS', 'ZOREN',
            
            # Steel and metals
            'EREGL', 'KRDMD', 'CEMTS', 'DOKTA', 'ISDMR', 'OZBAL', 'SARKY',
            
            # Chemicals and petrochemicals  
            'SASA', 'AKSA', 'ALKIM', 'ANACM', 'BAGFS', 'BRSAN', 'DYOBY',
            'GUBRF', 'HEKTS', 'IHEVA', 'PETKM', 'RTALB', 'SODA', 'TUPRS',
            
            # Food and beverages
            'ULKER', 'CCOLA', 'AEFES', 'BANVT', 'ERSU', 'KENT', 'KNFRT',
            'KRSAN', 'MERKO', 'OYLUM', 'PENGD', 'PETUN', 'PINSU', 'PNSUT',
            'TATGD', 'TUKAS', 'ULUSE', 'VANGD',
            
            # Textiles and apparel
            'ARSAN', 'ATEKS', 'BLCYT', 'BRKO', 'DERIM', 'DIRIT', 'HATEK',
            'KRTEK', 'LUKSK', 'MAVI', 'MENDERES', 'ROYAL', 'SKTAS', 'SNPAM',
            'SODSN', 'YATAS', 'YUNSA',
            
            # Healthcare and pharmaceuticals
            'DEVA', 'SELGD', 'SNGYO', 'ECZYT', 'LKMNH', 'EGPRO',
            
            # Paper and packaging
            'KARTN', 'OLMIP', 'PRKAB', 'SILVR',
            
            # Tourism and leisure
            'MAALT', 'PKART', 'TEKTU', 'UTPYA', 'AYCES', 'AVTUR', 'METUR',
            'NTTUR', 'PKENT', 'TAKS', 'KSTUR', 'MARTI',
            
            # Media and entertainment
            'DMRGD', 'HURGZ', 'IHLAS', 'IHLGM', 'IHYAY', 'KERVT', 'KLRHO',
            'MEDTR', 'MRGYO', 'RAYSG', 'TMPOL', 'YGGYO',
            
            # Education
            'FENER', 'BAHKM', 'OBASE',
            
            # Other sectors
            'ADANA', 'ADEL', 'ADESE', 'ADBGR', 'AEFES', 'AFYON', 'AGESA',
            'AGHOL', 'AGROT', 'AKARP', 'AKCNS', 'AKGRT', 'AKIN', 'AKSA',
            'AKSEN', 'AKSGY', 'AKSUE', 'ALARK', 'ALBRK', 'ALCAR', 'ALCTL',
            'ALFAS', 'ALGYO', 'ALKA', 'ALKIM', 'ALTIN', 'ALTNY', 'ALVES',
            'ALYAG', 'ANELE', 'ANSGR', 'ARASE', 'ARCLK', 'ARDYZ', 'ARENA',
            'ARMDA', 'ARSAN', 'ARTMS', 'ARZUM', 'ASELS', 'ASGYO', 'ASTOR',
            'ASUZU', 'ATAGY', 'ATAKP', 'ATATP', 'ATEKS', 'ATLAS', 'ATSYH',
            'AVGYO', 'AVHOL', 'AVISA', 'AVPGY', 'AVTUR', 'AYCEM', 'AYCES',
            'AYEN', 'AYES', 'AYGAZ', 'AZTEK', 'BAGFS', 'BAHKM', 'BAKAB',
            'BALAT', 'BANVT', 'BARMA', 'BASCM', 'BASGZ', 'BAYRK', 'BEGYO',
            'BERA', 'BEYAZ', 'BFREN', 'BIGCH', 'BIMAS', 'BINBN', 'BIOEN',
            'BIZIM', 'BJKAS', 'BLCYT', 'BMSCH', 'BMSTL', 'BNTAS', 'BOBET',
            'BORLS', 'BORSK', 'BOSSA', 'BRISA', 'BRKO', 'BRKSN', 'BRMEN',
            'BRSAN', 'BRYAT', 'BSOKE', 'BTCIM', 'BUCIM', 'BURCE', 'BURVA',
            'BVSAN', 'BYDNR', 'CANTE', 'CARRF', 'CATES', 'CCOLA', 'CELHA',
            'CEMTS', 'CEOEM', 'CIMSA', 'CLEBI', 'CMBTN', 'CMENT', 'CONSE',
            'COSMO', 'CRDFA', 'CRFSA', 'CUSAN', 'CVKMD', 'CWENE', 'DAGI',
            'DAPGM', 'DARDL', 'DENGE', 'DERHL', 'DERIM', 'DESPC', 'DEVA',
            'DGATE', 'DGGYO', 'DGKLB', 'DIRIT', 'DMRGD', 'DMSAS', 'DNISI',
            'DOAS', 'DOBUR', 'DOCO', 'DOGUB', 'DOHOL', 'DOKTA', 'DURDO',
            'DYOBY', 'DZGYO', 'EDATA', 'EDIP', 'EGEEN', 'EGGUB', 'EGPRO',
            'EGSER', 'EKGYO', 'EKIZ', 'EKSUN', 'ELITE', 'EMKEL', 'EMNIS',
            'ENERY', 'ENJSA', 'ENKAI', 'ENSRI', 'EPLAS', 'ERBOS', 'ERCB',
            'EREGL', 'ERSU', 'ESCAR', 'ESCOM', 'ETILR', 'ETYAT', 'EUKYO',
            'EUREN', 'EUSDR', 'EUYAV', 'EYODER', 'FENER', 'FLAP', 'FMIZP',
            'FONET', 'FORMT', 'FORTE', 'FROTO', 'FRIGO', 'GARAN', 'GARFA',
            'GDKMD', 'GEDIK', 'GEDZA', 'GENIL', 'GEREL', 'GESAN', 'GIPTA',
            'GLBMD', 'GLYHO', 'GMTAS', 'GOKNR', 'GOLTS', 'GOODY', 'GOZDE',
            'GRNYO', 'GRSEL', 'GSDDE', 'GSDHO', 'GSRAY', 'GUBRF', 'GWIND',
            'GZNMI', 'HALKB', 'HATEK', 'HATSN', 'HDFGS', 'HEDEF', 'HEKTS',
            'HKTM', 'HLGYO', 'HOROZ', 'HRGYO', 'HTTBT', 'HUBVC', 'HURGZ',
            'HUNER', 'IDAS', 'IDGYO', 'IHEVA', 'IHGZT', 'IHLAS', 'IHLGM',
            'IHYAY', 'IMASM', 'INDES', 'INFO', 'INTEM', 'INVEO', 'INVES',
            'ISGSY', 'ISGYO', 'ISKPL', 'ISSEN', 'IZENR', 'IZMDC', 'JANTS',
            'KAPLM', 'KAREL', 'KARSN', 'KARTN', 'KATMR', 'KAYSE', 'KCAER',
            'KCHOL', 'KENT', 'KERVT', 'KGYO', 'KIMMR', 'KLGYO', 'KLKIM',
            'KLNMA', 'KLRHO', 'KLSER', 'KLSYN', 'KMPUR', 'KNFRT', 'KONYA',
            'KOPOL', 'KORDS', 'KOSGB', 'KOZAA', 'KOZAL', 'KRDMA', 'KRDMB',
            'KRDMD', 'KREA', 'KRPLS', 'KRSAN', 'KRTEK', 'KRVGD', 'KSTUR',
            'KUTPO', 'LIDER', 'LINK', 'LKMNH', 'LOGO', 'LUKSK', 'MAALT',
            'MACKO', 'MAGEN', 'MAKIM', 'MAKTK', 'MANAS', 'MARDIN', 'MARTI',
            'MAVI', 'MEDTR', 'MEGAP', 'MEKAG', 'MEPET', 'MERCN', 'MERKO',
            'METRO', 'METUR', 'MGROS', 'MHRGY', 'MILPA', 'MMCAS', 'MOBTL',
            'MPARK', 'MRGYO', 'MRSHL', 'MSGYO', 'MTRKS', 'MTRYO', 'MULTD',
            'NATEN', 'NBFGN', 'NETAS', 'NTHOL', 'NTTUR', 'NUGYO', 'OBASE',
            'ODAS', 'ODINE', 'OLMIP', 'ONCSM', 'ORCAY', 'ORGE', 'ORMA',
            'OSMEN', 'OSTIM', 'OTKAR', 'OTTO', 'OYLUM', 'OZBAL', 'OZGYO',
            'OZKGY', 'OZRDN', 'OZSUB', 'PAGYO', 'PAMEL', 'PAPIL', 'PARSN',
            'PASEU', 'PATEK', 'PCILT', 'PEGYO', 'PENGD', 'PENTA', 'PETKM',
            'PETUN', 'PGSUS', 'PINSU', 'PKART', 'PKENT', 'PLAST', 'PLTUR',
            'PNSUT', 'POLHO', 'POLTK', 'PRDGS', 'PRKAB', 'PRKME', 'PRZMA',
            'PSDTC', 'QNBFB', 'QNBFL', 'QUAGR', 'RAYSG', 'REEDR', 'REIT',
            'REYSN', 'RNPOL', 'RODRG', 'ROYAL', 'RTALB', 'RUBNS', 'RYSAS',
            'SAFKR', 'SAHOL', 'SAMAT', 'SANEL', 'SANFM', 'SANKO', 'SARKY',
            'SASA', 'SAYAS', 'SDTTR', 'SEGYO', 'SEKFK', 'SELEC', 'SELGD',
            'SELVA', 'SEYKM', 'SILVR', 'SISE', 'SKBNK', 'SKTAS', 'SKYMD',
            'SMART', 'SMRTG', 'SNKRN', 'SNPAM', 'SODA', 'SODSN', 'SOKE',
            'SOKM', 'SONME', 'SRVGY', 'SUWEN', 'TATGD', 'TAVHL', 'TBORG',
            'TCELL', 'TCKRC', 'TDGYO', 'TEKTU', 'TERA', 'TERNA', 'TETMT',
            'TEZOL', 'THYAO', 'TIRE', 'TKFEN', 'TKNSA', 'TLMAN', 'TMPOL',
            'TMSN', 'TOASO', 'TRCAS', 'TRGYO', 'TRILC', 'TSGYO', 'TSKB',
            'TTKOM', 'TTRAK', 'TUCLK', 'TUKAS', 'TUPRS', 'TUREX', 'TURGG',
            'TURSG', 'UFUK', 'ULAS', 'ULKER', 'ULUSE', 'ULUUN', 'UNLU',
            'USAK', 'UTPYA', 'VAKBN', 'VAKFN', 'VANGD', 'VBTYZ', 'VCGYO',
            'VEBET', 'VEHBI', 'VESBE', 'VESTL', 'VKGYO', 'VKMDM', 'VRGYO',
            'WAVED', 'YAPRK', 'YATAS', 'YAYLA', 'YBTAS', 'YESIL', 'YGGYO',
            'YGYO', 'YKBNK', 'YUNSA', 'YYLGD', 'ZEDUR', 'ZOREN', 'ZRGYO'
        ]
        
        # Remove duplicates and sort
        comprehensive_stocks = sorted(list(set(comprehensive_stocks)))
        
        # Remove problematic stocks that are delisted or have data issues
        excluded_stocks = ['ZIRAAT', 'KOZA', 'SODA']
        comprehensive_stocks = [stock for stock in comprehensive_stocks if stock not in excluded_stocks]
        
        self.bist_stocks = comprehensive_stocks
        print(f"Using comprehensive list with {len(comprehensive_stocks)} BIST stocks")
        
        return self.bist_stocks
    
    def analyze_stock_volume(self, symbol, period='5d', interval='1d', sma_period=10, ema_short=50, ema_long=200, volume_period=20,
                           macd_fast=12, macd_slow=26, macd_signal=9, sideways_days=5, sideways_threshold=2.0,
                           vwap_period=20, support_tolerance=1.0, bottom_lookback=10,
                           volume_avg_period=20, volume_multiplier_triple=2.0, rsi_period=14, rsi_min=60, rsi_max=70, 
                           obv_period=20, obv_threshold=95, triangle_period=20, convergence_threshold=3.0,
                           volume_decline_period=10, volume_decline_threshold=20, breakout_volume_increase=40, breakout_direction="Yukarı",
                           divergence_period=20, min_divergence_strength=0.6, resistance_period=10, 
                           resistance_breakout_percent=1.5, volume_breakout_multiplier=1.5, rsi_oversold_threshold=30,
                           bb_period=20, bb_std_dev=2.0, squeeze_period=6, squeeze_percentile=10,
                           upper_band_breakout_percent=1.0, volume_squeeze_multiplier=1.5, consecutive_days=2,
                           fib_lookback_period=50, fib_retracement_min=38.2, fib_retracement_max=50.0,
                           fib_support_tolerance=2.0, harmonic_pattern_type="Otomatik", harmonic_tolerance=5.0,
                           fib_volume_multiplier=1.3, trend_strength_days=10, periods_to_check=3):
        """
        Analyze volume for a single stock
        
        Args:
            symbol (str): Stock symbol
            period (str): Time period for analysis
            interval (str): Data interval
            sma_period (int): SMA calculation period
            ema_short (int): Short EMA period
            ema_long (int): Long EMA period
            volume_period (int): Volume comparison period
            macd_fast (int): MACD fast EMA period
            macd_slow (int): MACD slow EMA period
            macd_signal (int): MACD signal period
            sideways_days (int): Days to check for sideways movement
            sideways_threshold (float): Threshold for sideways movement detection
            vwap_period (int): VWAP calculation period
            support_tolerance (float): VWAP support tolerance percentage
            bottom_lookback (int): Lookback period for bottom detection
            volume_avg_period (int): Volume average period for triple confirmation
            volume_multiplier_triple (float): Volume multiplier for triple confirmation
            rsi_period (int): RSI calculation period
            rsi_min (int): RSI minimum threshold
            rsi_max (int): RSI maximum threshold
            obv_period (int): OBV comparison period
            obv_threshold (int): OBV threshold percentage
            triangle_period (int): Triangle formation detection period
            convergence_threshold (float): Triangle convergence threshold percentage
            volume_decline_period (int): Volume decline analysis period
            volume_decline_threshold (int): Volume decline threshold percentage
            breakout_volume_increase (int): Required volume increase on breakout
            breakout_direction (str): Direction of breakout to scan for
            divergence_period (int): Period for divergence analysis
            min_divergence_strength (float): Minimum divergence strength (0.3-1.0)
            resistance_period (int): Period for resistance level detection
            resistance_breakout_percent (float): Percentage breakout required for resistance
            volume_breakout_multiplier (float): Volume multiplier for breakout confirmation
            rsi_oversold_threshold (int): RSI oversold threshold for divergence
            bb_period (int): Bollinger Band calculation period
            bb_std_dev (float): Bollinger Band standard deviation multiplier
            squeeze_period (int): Squeeze analysis period in months
            squeeze_percentile (int): Squeeze percentile threshold (5-25)
            upper_band_breakout_percent (float): Upper band breakout percentage
            volume_squeeze_multiplier (float): Volume multiplier for squeeze breakout
            consecutive_days (int): Consecutive days requirement for upper band closure
            fib_lookback_period (int): Fibonacci analysis lookback period
            fib_retracement_min (float): Minimum Fibonacci retracement level (%)
            fib_retracement_max (float): Maximum Fibonacci retracement level (%)
            fib_support_tolerance (float): Support tolerance for Fibonacci levels (%)
            harmonic_pattern_type (str): Type of harmonic pattern to detect
            harmonic_tolerance (float): Harmonic pattern tolerance (%)
            fib_volume_multiplier (float): Volume multiplier for support test
            trend_strength_days (int): Days for trend strength analysis
            periods_to_check (int): Number of periods to check for volume progression (1-4)
            
        Returns:
            dict: Analysis results
        """
        try:
            # Fetch stock data
            data = self.data_fetcher.get_stock_data(symbol, period, interval)
            
            if data is None or len(data) < sma_period:
                return None
            
            # Calculate volume SMA
            data['volume_sma'] = data['volume'].rolling(window=sma_period).mean()
            
            # Calculate EMAs for price
            data['ema_short'] = data['close'].ewm(span=ema_short).mean()
            data['ema_long'] = data['close'].ewm(span=ema_long).mean()
            
            # Calculate volume moving average for comparison
            data['volume_ma'] = data['volume'].rolling(window=volume_period).mean()
            
            # Calculate MACD
            data['macd_ema_fast'] = data['close'].ewm(span=macd_fast).mean()
            data['macd_ema_slow'] = data['close'].ewm(span=macd_slow).mean()
            data['macd_line'] = data['macd_ema_fast'] - data['macd_ema_slow']
            data['macd_signal'] = data['macd_line'].ewm(span=macd_signal).mean()
            data['macd_histogram'] = data['macd_line'] - data['macd_signal']
            
            # Calculate VWAP
            data['vwap'] = self._calculate_vwap(data, vwap_period)
            
            # Calculate RSI
            data['rsi'] = self._calculate_rsi(data['close'], rsi_period)
            
            # Calculate OBV
            data['obv'] = self._calculate_obv(data)
            
            # Get latest values
            latest_data = data.iloc[-1]
            current_volume = latest_data['volume']
            volume_sma = latest_data['volume_sma']
            current_price = latest_data['close']
            ema_short_current = latest_data['ema_short']
            ema_long_current = latest_data['ema_long']
            volume_ma_current = latest_data['volume_ma']
            macd_line_current = latest_data['macd_line']
            macd_histogram_current = latest_data['macd_histogram']
            vwap_current = latest_data['vwap']
            rsi_current = latest_data['rsi']
            obv_current = latest_data['obv']
            
            # Check volume progression criteria - dynamic based on periods_to_check
            volume_progression_check = False
            volume_trend = "Yetersiz Veri"
            
            # Calculate required minimum data points for the check
            required_periods = periods_to_check + 1  # Need one more data point for comparison
            
            if len(data) >= required_periods:
                # Get last N+1 volumes for progression check
                last_volumes = data['volume'].tail(required_periods).values
                
                # Check if each period has higher volume than previous
                volume_progression_check = True
                for i in range(1, len(last_volumes)):
                    if last_volumes[i] <= last_volumes[i-1]:
                        volume_progression_check = False
                        break
                
                if volume_progression_check:
                    volume_trend = f"{periods_to_check} Periyot Artış ✓"
                else:
                    volume_trend = "Artış Yok ✗"
            elif len(data) >= 3:
                # Fallback to simple trend for less data
                recent_volumes = data['volume'].tail(3).values
                volume_trend = self._calculate_trend(recent_volumes)
            
            # Check EMA Golden Cross
            golden_cross = False
            golden_cross_recent = False
            
            if len(data) >= max(ema_short, ema_long) + 5:
                # Check if EMA short is above EMA long (current golden cross state)
                golden_cross = ema_short_current > ema_long_current
                
                # Check if golden cross happened recently (within last 5 periods)
                for i in range(1, min(6, len(data))):
                    prev_short = data['ema_short'].iloc[-(i+1)]
                    prev_long = data['ema_long'].iloc[-(i+1)]
                    curr_short = data['ema_short'].iloc[-i]
                    curr_long = data['ema_long'].iloc[-i]
                    
                    if prev_short <= prev_long and curr_short > curr_long:
                        golden_cross_recent = True
                        break
            
            # Check MACD Zero Line Breakout
            macd_zero_breakout = False
            macd_zero_breakout_recent = False
            macd_histogram_positive = macd_histogram_current > 0
            
            if len(data) >= max(macd_fast, macd_slow) + macd_signal + 5:
                # Current MACD above zero
                macd_zero_breakout = macd_line_current > 0
                
                # Check if MACD crossed zero recently (within last 5 periods)
                for i in range(1, min(6, len(data))):
                    prev_macd = data['macd_line'].iloc[-(i+1)]
                    curr_macd = data['macd_line'].iloc[-i]
                    
                    if prev_macd <= 0 and curr_macd > 0:
                        macd_zero_breakout_recent = True
                        break
            
            # Check sideways movement before breakout
            sideways_movement = False
            if len(data) >= sideways_days + 5:
                # Get price data for sideways analysis
                sideways_period = data['close'].tail(sideways_days + 1)
                if len(sideways_period) > 1:
                    price_max = sideways_period.max()
                    price_min = sideways_period.min()
                    price_range_pct = ((price_max - price_min) / price_min) * 100
                    sideways_movement = price_range_pct <= sideways_threshold
            
            # Check VWAP Support Test
            vwap_support_test = False
            vwap_breakout_recent = False
            rising_bottoms = False
            
            if len(data) >= vwap_period + bottom_lookback:
                # Check if price went below VWAP and came back above
                recent_data = data.tail(10)  # Last 10 periods
                vwap_below_count = 0
                vwap_above_recent = False
                
                for i in range(len(recent_data)):
                    row = recent_data.iloc[i]
                    vwap_val = row['vwap']
                    low_price = row['low']
                    close_price = row['close']
                    
                    # Check if price went below VWAP (with tolerance)
                    if low_price < vwap_val * (1 - support_tolerance/100):
                        vwap_below_count += 1
                    
                    # Check if recent close is above VWAP
                    if i >= len(recent_data) - 3:  # Last 3 periods
                        if close_price > vwap_val:
                            vwap_above_recent = True
                
                vwap_support_test = vwap_below_count > 0 and vwap_above_recent
                vwap_breakout_recent = current_price > vwap_current
                
                # Check for rising bottoms
                rising_bottoms = self._check_rising_bottoms(data, bottom_lookback)
            
            # Check Triple Volume Confirmation
            triple_volume_confirmed = False
            rsi_in_range = False
            obv_at_peak = False
            
            if len(data) >= max(volume_avg_period, rsi_period, obv_period):
                # 1. Volume confirmation
                volume_ma_triple = data['volume'].tail(volume_avg_period).mean()
                triple_volume_confirmed = current_volume >= (volume_ma_triple * volume_multiplier_triple)
                
                # 2. RSI in optimal range
                rsi_in_range = rsi_min <= rsi_current <= rsi_max
                
                # 3. OBV at peak levels
                obv_period_data = data['obv'].tail(obv_period)
                obv_percentile = (obv_current - obv_period_data.min()) / (obv_period_data.max() - obv_period_data.min()) * 100
                obv_at_peak = obv_percentile >= obv_threshold
            
            # Check Triangle Breakout Pattern
            triangle_detected = False
            volume_declined = False
            breakout_confirmed = False
            breakout_direction_correct = False
            
            if len(data) >= triangle_period:
                # 1. Detect triangle formation (converging price action)
                triangle_detected = self._detect_triangle_formation(data, triangle_period, convergence_threshold)
                
                # 2. Check volume decline during formation
                volume_declined = self._check_volume_decline(data, volume_decline_period, volume_decline_threshold)
                
                # 3. Check breakout with volume increase
                breakout_confirmed, breakout_direction_detected = self._check_breakout_with_volume(
                    data, current_volume, breakout_volume_increase
                )
                
                # 4. Check if breakout direction matches requirement
                if breakout_direction == "Her İkisi":
                    breakout_direction_correct = breakout_confirmed
                elif breakout_direction == "Yukarı":
                    breakout_direction_correct = breakout_confirmed and breakout_direction_detected == "up"
                elif breakout_direction == "Aşağı":
                    breakout_direction_correct = breakout_confirmed and breakout_direction_detected == "down"
            
            # Check RSI Divergence + Trend Breakout Pattern
            rsi_divergence_detected = False
            rsi_oversold = False
            resistance_broken = False
            volume_confirmed_breakout = False
            
            if len(data) >= divergence_period:
                # 1. Check for positive RSI divergence (price lower lows, RSI higher lows)
                rsi_divergence_detected = self._detect_rsi_divergence(data, divergence_period, min_divergence_strength, rsi_period)
                
                # 2. Check if RSI was in oversold territory
                rsi_oversold = data['rsi'].iloc[-divergence_period:].min() <= rsi_oversold_threshold
                
                # 3. Check for resistance breakout
                resistance_broken = self._check_resistance_breakout(data, resistance_period, resistance_breakout_percent)
                
                # 4. Check volume confirmation for breakout
                volume_confirmed_breakout = self._check_volume_confirmation_breakout(
                    data, current_volume, volume_breakout_multiplier
                )
            
            # Check Bollinger Band Squeeze + Breakout Pattern
            bb_squeeze_detected = False
            upper_band_broken = False
            volume_confirmed_squeeze = False
            consecutive_upper_closes = False
            
            if len(data) >= bb_period:
                # 1. Calculate Bollinger Bands and detect squeeze
                bb_squeeze_detected = self._detect_bollinger_squeeze(data, bb_period, bb_std_dev, squeeze_period, squeeze_percentile)
                
                # 2. Check upper band breakout
                upper_band_broken = self._check_upper_band_breakout(data, bb_period, bb_std_dev, upper_band_breakout_percent)
                
                # 3. Check volume confirmation for squeeze breakout
                volume_confirmed_squeeze = self._check_volume_confirmation_breakout(
                    data, current_volume, volume_squeeze_multiplier
                )
                
                # 4. Check consecutive days of upper band proximity
                consecutive_upper_closes = self._check_consecutive_upper_closes(
                    data, bb_period, bb_std_dev, consecutive_days
                )
            
            # Check Fibonacci Retest + Harmonic Pattern
            fib_retracement_detected = False
            harmonic_pattern_detected = False
            fib_support_confirmed = False
            volume_confirmed_fib = False
            
            if len(data) >= fib_lookback_period:
                # 1. Detect Fibonacci retracement levels
                fib_retracement_detected = self._detect_fibonacci_retracement(
                    data, fib_lookback_period, fib_retracement_min, fib_retracement_max, fib_support_tolerance
                )
                
                # 2. Detect harmonic patterns
                harmonic_pattern_detected = self._detect_harmonic_pattern(
                    data, harmonic_pattern_type, harmonic_tolerance, fib_lookback_period
                )
                
                # 3. Check Fibonacci support confirmation
                fib_support_confirmed = self._check_fibonacci_support(
                    data, fib_lookback_period, fib_retracement_min, fib_retracement_max, fib_support_tolerance
                )
                
                # 4. Check volume confirmation for support test
                volume_confirmed_fib = self._check_volume_confirmation_breakout(
                    data, current_volume, fib_volume_multiplier
                )
            
            # Validate data
            if pd.isna(current_volume) or pd.isna(volume_sma) or volume_sma == 0:
                return None
            
            return {
                'symbol': symbol,
                'current_volume': current_volume,
                'volume_sma': volume_sma,
                'volume_ma': volume_ma_current,
                'current_price': current_price,
                'volume_trend': volume_trend,
                'volume_ratio': current_volume / volume_sma,
                'volume_progression_check': volume_progression_check,
                'ema_short': ema_short_current,
                'ema_long': ema_long_current,
                'golden_cross': golden_cross,
                'golden_cross_recent': golden_cross_recent,
                'macd_line': macd_line_current,
                'macd_histogram': macd_histogram_current,
                'macd_zero_breakout': macd_zero_breakout,
                'macd_zero_breakout_recent': macd_zero_breakout_recent,
                'macd_histogram_positive': macd_histogram_positive,
                'sideways_movement': sideways_movement,
                'vwap': vwap_current,
                'vwap_support_test': vwap_support_test,
                'vwap_breakout_recent': vwap_breakout_recent,
                'rising_bottoms': rising_bottoms,
                'rsi': rsi_current,
                'obv': obv_current,
                'triple_volume_confirmed': triple_volume_confirmed,
                'rsi_in_range': rsi_in_range,
                'obv_at_peak': obv_at_peak,
                'triangle_detected': triangle_detected,
                'volume_declined': volume_declined,
                'breakout_confirmed': breakout_confirmed,
                'breakout_direction_correct': breakout_direction_correct,
                'rsi_divergence_detected': rsi_divergence_detected,
                'rsi_oversold': rsi_oversold,
                'resistance_broken': resistance_broken,
                'volume_confirmed_breakout': volume_confirmed_breakout,
                'bb_squeeze_detected': bb_squeeze_detected,
                'upper_band_broken': upper_band_broken,
                'volume_confirmed_squeeze': volume_confirmed_squeeze,
                'consecutive_upper_closes': consecutive_upper_closes,
                'fib_retracement_detected': fib_retracement_detected,
                'harmonic_pattern_detected': harmonic_pattern_detected,
                'fib_support_confirmed': fib_support_confirmed,
                'volume_confirmed_fib': volume_confirmed_fib,
                'data_points': len(data),
                'last_update': datetime.now()
            }
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {str(e)}")
            return None
    
    def _calculate_vwap(self, data, period):
        """Calculate Volume Weighted Average Price"""
        try:
            # Calculate typical price (High + Low + Close) / 3
            typical_price = (data['high'] + data['low'] + data['close']) / 3
            
            # Calculate VWAP using rolling window
            vwap_values = []
            for i in range(len(data)):
                start_idx = max(0, i - period + 1)
                period_data = data.iloc[start_idx:i+1]
                
                if len(period_data) > 0:
                    tp = (period_data['high'] + period_data['low'] + period_data['close']) / 3
                    vol = period_data['volume']
                    
                    # VWAP = Sum(Typical Price * Volume) / Sum(Volume)
                    if vol.sum() > 0:
                        vwap = (tp * vol).sum() / vol.sum()
                    else:
                        vwap = tp.iloc[-1]  # Fallback to typical price
                else:
                    vwap = typical_price.iloc[i]
                
                vwap_values.append(vwap)
            
            return pd.Series(vwap_values, index=data.index)
            
        except Exception as e:
            print(f"Error calculating VWAP: {str(e)}")
            return pd.Series([0] * len(data), index=data.index)
    
    def _check_rising_bottoms(self, data, lookback_period):
        """Check if recent bottoms are rising"""
        try:
            if len(data) < lookback_period + 5:
                return False
            
            recent_data = data.tail(lookback_period + 5)
            lows = recent_data['low'].values
            
            # Find local minima (bottoms)
            bottoms = []
            for i in range(1, len(lows) - 1):
                if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                    bottoms.append((i, lows[i]))
            
            # Need at least 2 bottoms to compare
            if len(bottoms) < 2:
                return False
            
            # Check if last bottom is higher than previous bottom
            recent_bottoms = sorted(bottoms, key=lambda x: x[0])[-2:]  # Last 2 bottoms
            return recent_bottoms[1][1] > recent_bottoms[0][1]
            
        except Exception as e:
            print(f"Error checking rising bottoms: {str(e)}")
            return False
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.fillna(50)
            
        except Exception as e:
            print(f"Error calculating RSI: {str(e)}")
            return pd.Series([50] * len(prices), index=prices.index)
    
    def _calculate_obv(self, data):
        """Calculate On Balance Volume"""
        try:
            obv = []
            obv_value = 0
            
            for i in range(len(data)):
                if i == 0:
                    obv_value = data['volume'].iloc[i]
                else:
                    prev_close = data['close'].iloc[i-1]
                    curr_close = data['close'].iloc[i]
                    curr_volume = data['volume'].iloc[i]
                    
                    if curr_close > prev_close:
                        obv_value += curr_volume
                    elif curr_close < prev_close:
                        obv_value -= curr_volume
                    # If close == prev_close, OBV stays the same
                
                obv.append(obv_value)
            
            return pd.Series(obv, index=data.index)
            
        except Exception as e:
            print(f"Error calculating OBV: {str(e)}")
            return pd.Series([0] * len(data), index=data.index)
    
    def _detect_triangle_formation(self, data, period, convergence_threshold):
        """Detect triangle formation (converging price action)"""
        try:
            # Get recent data for triangle detection
            recent_data = data.tail(period)
            
            if len(recent_data) < 10:
                return False
            
            # Calculate highs and lows
            highs = recent_data['high']
            lows = recent_data['low']
            
            # Find trend lines for highs and lows
            high_trend_slope = self._calculate_trend_slope(highs)
            low_trend_slope = self._calculate_trend_slope(lows)
            
            # Triangle: high trend line should be declining, low trend line should be inclining
            # Or both converging towards each other
            price_range_start = highs.iloc[0] - lows.iloc[0]
            price_range_end = highs.iloc[-1] - lows.iloc[-1]
            
            if price_range_start > 0:
                convergence_percent = ((price_range_start - price_range_end) / price_range_start) * 100
                return convergence_percent >= convergence_threshold
            
            return False
            
        except Exception as e:
            print(f"Error detecting triangle formation: {str(e)}")
            return False
    
    def _calculate_trend_slope(self, series):
        """Calculate trend line slope using linear regression"""
        try:
            import numpy as np
            
            x = np.arange(len(series))
            y = series.values
            
            # Simple linear regression
            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x * x)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            return slope
            
        except Exception as e:
            print(f"Error calculating trend slope: {str(e)}")
            return 0
    
    def _check_volume_decline(self, data, period, threshold):
        """Check if volume has declined during the formation period"""
        try:
            if len(data) < period:
                return False
            
            # Compare early vs late volume in the formation period
            recent_data = data.tail(period)
            early_volume = recent_data['volume'].head(period // 2).mean()
            late_volume = recent_data['volume'].tail(period // 2).mean()
            
            if early_volume > 0:
                decline_percent = ((early_volume - late_volume) / early_volume) * 100
                return decline_percent >= threshold
            
            return False
            
        except Exception as e:
            print(f"Error checking volume decline: {str(e)}")
            return False
    
    def _check_breakout_with_volume(self, data, current_volume, volume_increase_threshold):
        """Check if there's a breakout with volume increase"""
        try:
            if len(data) < 5:
                return False, None
            
            # Get recent data for breakout detection
            recent_data = data.tail(5)
            current_price = recent_data['close'].iloc[-1]
            previous_prices = recent_data['close'].iloc[:-1]
            
            # Calculate recent volume average (exclude current day)
            recent_volume_avg = recent_data['volume'].iloc[:-1].mean()
            
            # Check volume increase
            if recent_volume_avg > 0:
                volume_increase_percent = ((current_volume - recent_volume_avg) / recent_volume_avg) * 100
                volume_breakout = volume_increase_percent >= volume_increase_threshold
            else:
                volume_breakout = False
            
            # Determine breakout direction
            recent_high = recent_data['high'].iloc[:-1].max()
            recent_low = recent_data['low'].iloc[:-1].min()
            
            breakout_direction = None
            price_breakout = False
            
            if current_price > recent_high:
                breakout_direction = "up"
                price_breakout = True
            elif current_price < recent_low:
                breakout_direction = "down"
                price_breakout = True
            
            return (volume_breakout and price_breakout), breakout_direction
            
        except Exception as e:
            print(f"Error checking breakout with volume: {str(e)}")
            return False, None
    
    def _detect_rsi_divergence(self, data, period, min_strength, rsi_period):
        """Detect positive RSI divergence (price lower lows, RSI higher lows)"""
        try:
            if len(data) < period:
                return False
            
            # Get recent data for divergence analysis
            recent_data = data.tail(period)
            prices = recent_data['low']  # Use lows for divergence detection
            rsi_values = recent_data['rsi']
            
            # Find local minima in both price and RSI
            price_lows = self._find_local_minima(prices, window=3)
            rsi_lows = self._find_local_minima(rsi_values, window=3)
            
            if len(price_lows) < 2 or len(rsi_lows) < 2:
                return False
            
            # Check for divergence: price making lower lows, RSI making higher lows
            last_price_low = price_lows[-1]
            prev_price_low = price_lows[-2]
            last_rsi_low = rsi_lows[-1]
            prev_rsi_low = rsi_lows[-2]
            
            # Price divergence: current low should be lower than previous low
            price_divergence = prices.iloc[last_price_low] < prices.iloc[prev_price_low]
            
            # RSI divergence: current RSI low should be higher than previous RSI low
            rsi_divergence = rsi_values.iloc[last_rsi_low] > rsi_values.iloc[prev_rsi_low]
            
            # Calculate divergence strength
            if price_divergence and rsi_divergence:
                price_change = abs(prices.iloc[last_price_low] - prices.iloc[prev_price_low]) / prices.iloc[prev_price_low]
                rsi_change = abs(rsi_values.iloc[last_rsi_low] - rsi_values.iloc[prev_rsi_low]) / 100.0
                
                # Divergence strength is the ratio of changes
                divergence_strength = (rsi_change / max(price_change, 0.001)) if price_change > 0 else 0
                
                return divergence_strength >= min_strength
            
            return False
            
        except Exception as e:
            print(f"Error detecting RSI divergence: {str(e)}")
            return False
    
    def _find_local_minima(self, series, window=3):
        """Find local minima in a time series"""
        try:
            minima = []
            for i in range(window, len(series) - window):
                is_minimum = True
                for j in range(i - window, i + window + 1):
                    if j != i and series.iloc[j] <= series.iloc[i]:
                        is_minimum = False
                        break
                if is_minimum:
                    minima.append(i)
            return minima
            
        except Exception as e:
            print(f"Error finding local minima: {str(e)}")
            return []
    
    def _check_resistance_breakout(self, data, period, breakout_percent):
        """Check if price has broken through resistance level"""
        try:
            if len(data) < period + 1:
                return False
            
            # Get resistance level (highest high in the period, excluding current day)
            resistance_data = data.iloc[-(period+1):-1]  # Exclude current day
            resistance_level = resistance_data['high'].max()
            
            # Current price
            current_price = data['close'].iloc[-1]
            
            # Check if current price broke resistance by the required percentage
            breakout_threshold = resistance_level * (1 + breakout_percent / 100)
            
            return current_price >= breakout_threshold
            
        except Exception as e:
            print(f"Error checking resistance breakout: {str(e)}")
            return False
    
    def _check_volume_confirmation_breakout(self, data, current_volume, multiplier):
        """Check if volume confirms the breakout"""
        try:
            if len(data) < 5:
                return False
            
            # Average volume of previous days (exclude current)
            avg_volume = data['volume'].iloc[-6:-1].mean()  # Last 5 days excluding current
            
            # Check if current volume is above threshold
            return current_volume >= (avg_volume * multiplier)
            
        except Exception as e:
            print(f"Error checking volume confirmation for breakout: {str(e)}")
            return False
    
    def _detect_bollinger_squeeze(self, data, period, std_dev, squeeze_months, percentile):
        """Detect Bollinger Band squeeze (band width at lowest levels)"""
        try:
            if len(data) < period * 22 * squeeze_months:  # Approximate trading days in months
                return False
            
            # Calculate Bollinger Bands
            close_prices = data['close']
            sma = close_prices.rolling(window=period).mean()
            std = close_prices.rolling(window=period).std()
            
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            # Calculate band width (normalized by price)
            band_width = (upper_band - lower_band) / sma * 100
            
            # Get squeeze period data (months to days conversion)
            squeeze_days = squeeze_months * 22  # Approximate trading days per month
            historical_width = band_width.iloc[-squeeze_days:] if len(band_width) >= squeeze_days else band_width
            
            # Check if current band width is in the lowest percentile
            current_width = band_width.iloc[-1]
            percentile_threshold = historical_width.quantile(percentile / 100.0)
            
            return current_width <= percentile_threshold
            
        except Exception as e:
            print(f"Error detecting Bollinger squeeze: {str(e)}")
            return False
    
    def _check_upper_band_breakout(self, data, period, std_dev, breakout_percent):
        """Check if price has broken above upper Bollinger Band"""
        try:
            if len(data) < period:
                return False
            
            # Calculate current Bollinger Bands
            close_prices = data['close']
            sma = close_prices.rolling(window=period).mean().iloc[-1]
            std = close_prices.rolling(window=period).std().iloc[-1]
            
            upper_band = sma + (std * std_dev)
            current_price = data['close'].iloc[-1]
            
            # Check if price broke upper band by required percentage
            breakout_threshold = upper_band * (1 + breakout_percent / 100)
            
            return current_price >= breakout_threshold
            
        except Exception as e:
            print(f"Error checking upper band breakout: {str(e)}")
            return False
    
    def _check_consecutive_upper_closes(self, data, period, std_dev, days):
        """Check for consecutive days of closes near upper band"""
        try:
            if len(data) < max(period, days):
                return False
            
            # Calculate Bollinger Bands for last 'days' periods
            close_prices = data['close']
            sma = close_prices.rolling(window=period).mean()
            std = close_prices.rolling(window=period).std()
            upper_band = sma + (std * std_dev)
            
            # Check last 'days' closes
            recent_closes = close_prices.iloc[-days:]
            recent_upper_bands = upper_band.iloc[-days:]
            
            # Count consecutive closes within 2% of upper band
            upper_band_proximity = 0.98  # Within 2% of upper band
            consecutive_count = 0
            
            for i in range(len(recent_closes)):
                if recent_closes.iloc[i] >= (recent_upper_bands.iloc[i] * upper_band_proximity):
                    consecutive_count += 1
                else:
                    consecutive_count = 0
            
            return consecutive_count >= days
            
        except Exception as e:
            print(f"Error checking consecutive upper closes: {str(e)}")
            return False
    
    def _detect_fibonacci_retracement(self, data, lookback_period, min_retracement, max_retracement, tolerance):
        """Detect Fibonacci retracement levels and support"""
        try:
            if len(data) < lookback_period:
                return False
            
            # Get recent data for analysis
            recent_data = data.tail(lookback_period)
            highs = recent_data['high']
            lows = recent_data['low']
            closes = recent_data['close']
            
            # Find significant swing high and low
            swing_high = highs.max()
            swing_low = lows.min()
            swing_high_idx = highs.idxmax()
            swing_low_idx = lows.idxmin()
            
            # Ensure we have a proper swing (high comes before low for retracement)
            if swing_high_idx >= swing_low_idx:
                return False
            
            # Calculate Fibonacci retracement levels
            price_range = swing_high - swing_low
            fib_382 = swing_high - (price_range * 0.382)
            fib_500 = swing_high - (price_range * 0.500)
            fib_618 = swing_high - (price_range * 0.618)
            
            # Current price
            current_price = closes.iloc[-1]
            
            # Check if current price is within the specified retracement range
            target_min_level = swing_high - (price_range * min_retracement / 100)
            target_max_level = swing_high - (price_range * max_retracement / 100)
            
            # Check if price is near any Fibonacci level within tolerance
            tolerance_range = price_range * tolerance / 100
            
            near_382 = abs(current_price - fib_382) <= tolerance_range
            near_500 = abs(current_price - fib_500) <= tolerance_range
            near_618 = abs(current_price - fib_618) <= tolerance_range
            
            # Price should be within the target retracement range and near a Fib level
            in_range = target_max_level <= current_price <= target_min_level
            near_fib_level = near_382 or near_500 or near_618
            
            return in_range and near_fib_level
            
        except Exception as e:
            print(f"Error detecting Fibonacci retracement: {str(e)}")
            return False
    
    def _detect_harmonic_pattern(self, data, pattern_type, tolerance, lookback_period):
        """Detect harmonic patterns (simplified implementation)"""
        try:
            if len(data) < lookback_period or lookback_period < 20:
                return False
            
            # Get recent data for pattern analysis
            recent_data = data.tail(lookback_period)
            closes = recent_data['close']
            highs = recent_data['high']
            lows = recent_data['low']
            
            # Find significant swing points
            swing_points = self._find_swing_points(closes, window=5)
            
            if len(swing_points) < 5:  # Need at least 5 points for harmonic patterns
                return False
            
            # Get last 5 swing points (X, A, B, C, D pattern)
            points = swing_points[-5:]
            
            if pattern_type == "Otomatik":
                # Check for any harmonic pattern
                return (self._check_gartley_pattern(points, tolerance) or
                        self._check_bat_pattern(points, tolerance) or
                        self._check_butterfly_pattern(points, tolerance) or
                        self._check_crab_pattern(points, tolerance))
            elif pattern_type == "Gartley":
                return self._check_gartley_pattern(points, tolerance)
            elif pattern_type == "Bat":
                return self._check_bat_pattern(points, tolerance)
            elif pattern_type == "Butterfly":
                return self._check_butterfly_pattern(points, tolerance)
            elif pattern_type == "Crab":
                return self._check_crab_pattern(points, tolerance)
            
            return False
            
        except Exception as e:
            print(f"Error detecting harmonic pattern: {str(e)}")
            return False
    
    def _find_swing_points(self, prices, window=5):
        """Find swing highs and lows in price data"""
        try:
            swing_points = []
            
            for i in range(window, len(prices) - window):
                # Check for swing high
                is_high = all(prices.iloc[i] >= prices.iloc[j] for j in range(i-window, i+window+1) if j != i)
                # Check for swing low  
                is_low = all(prices.iloc[i] <= prices.iloc[j] for j in range(i-window, i+window+1) if j != i)
                
                if is_high or is_low:
                    swing_points.append({
                        'index': i,
                        'price': prices.iloc[i],
                        'type': 'high' if is_high else 'low'
                    })
            
            return swing_points
            
        except Exception as e:
            print(f"Error finding swing points: {str(e)}")
            return []
    
    def _check_gartley_pattern(self, points, tolerance):
        """Check for Gartley pattern (0.618 AB=CD, 0.786 XA retracement)"""
        try:
            if len(points) < 5:
                return False
            
            # Extract points (X, A, B, C, D)
            X, A, B, C, D = [p['price'] for p in points]
            
            # Gartley ratios
            AB_XA = abs(B - A) / abs(A - X) if abs(A - X) > 0 else 0
            BC_AB = abs(C - B) / abs(B - A) if abs(B - A) > 0 else 0
            CD_BC = abs(D - C) / abs(C - B) if abs(C - B) > 0 else 0
            AD_XA = abs(D - A) / abs(A - X) if abs(A - X) > 0 else 0
            
            # Target ratios for Gartley
            target_AB_XA = 0.618
            target_BC_AB = 0.382  # or 0.886
            target_CD_BC = 1.272  # or 1.618
            target_AD_XA = 0.786
            
            # Check ratios within tolerance
            tolerance_ratio = tolerance / 100
            
            ab_check = abs(AB_XA - target_AB_XA) <= tolerance_ratio
            bc_check = abs(BC_AB - 0.382) <= tolerance_ratio or abs(BC_AB - 0.886) <= tolerance_ratio
            cd_check = abs(CD_BC - 1.272) <= tolerance_ratio or abs(CD_BC - 1.618) <= tolerance_ratio
            ad_check = abs(AD_XA - target_AD_XA) <= tolerance_ratio
            
            return ab_check and bc_check and cd_check and ad_check
            
        except Exception as e:
            print(f"Error checking Gartley pattern: {str(e)}")
            return False
    
    def _check_bat_pattern(self, points, tolerance):
        """Check for Bat pattern (0.382/0.500 AB=CD, 0.886 XA retracement)"""
        try:
            if len(points) < 5:
                return False
            
            X, A, B, C, D = [p['price'] for p in points]
            
            AB_XA = abs(B - A) / abs(A - X) if abs(A - X) > 0 else 0
            AD_XA = abs(D - A) / abs(A - X) if abs(A - X) > 0 else 0
            
            target_AB_XA = 0.382  # or 0.500
            target_AD_XA = 0.886
            
            tolerance_ratio = tolerance / 100
            
            ab_check = abs(AB_XA - 0.382) <= tolerance_ratio or abs(AB_XA - 0.500) <= tolerance_ratio
            ad_check = abs(AD_XA - target_AD_XA) <= tolerance_ratio
            
            return ab_check and ad_check
            
        except Exception as e:
            print(f"Error checking Bat pattern: {str(e)}")
            return False
    
    def _check_butterfly_pattern(self, points, tolerance):
        """Check for Butterfly pattern (0.786 AB=CD, 1.272 XA extension)"""
        try:
            if len(points) < 5:
                return False
            
            X, A, B, C, D = [p['price'] for p in points]
            
            AB_XA = abs(B - A) / abs(A - X) if abs(A - X) > 0 else 0
            AD_XA = abs(D - A) / abs(A - X) if abs(A - X) > 0 else 0
            
            target_AB_XA = 0.786
            target_AD_XA = 1.272  # or 1.618
            
            tolerance_ratio = tolerance / 100
            
            ab_check = abs(AB_XA - target_AB_XA) <= tolerance_ratio
            ad_check = abs(AD_XA - 1.272) <= tolerance_ratio or abs(AD_XA - 1.618) <= tolerance_ratio
            
            return ab_check and ad_check
            
        except Exception as e:
            print(f"Error checking Butterfly pattern: {str(e)}")
            return False
    
    def _check_crab_pattern(self, points, tolerance):
        """Check for Crab pattern (0.382/0.618 AB=CD, 1.618 XA extension)"""
        try:
            if len(points) < 5:
                return False
            
            X, A, B, C, D = [p['price'] for p in points]
            
            AB_XA = abs(B - A) / abs(A - X) if abs(A - X) > 0 else 0
            AD_XA = abs(D - A) / abs(A - X) if abs(A - X) > 0 else 0
            
            target_AB_XA = 0.382  # or 0.618
            target_AD_XA = 1.618
            
            tolerance_ratio = tolerance / 100
            
            ab_check = abs(AB_XA - 0.382) <= tolerance_ratio or abs(AB_XA - 0.618) <= tolerance_ratio
            ad_check = abs(AD_XA - target_AD_XA) <= tolerance_ratio
            
            return ab_check and ad_check
            
        except Exception as e:
            print(f"Error checking Crab pattern: {str(e)}")
            return False
    
    def _check_fibonacci_support(self, data, lookback_period, min_retracement, max_retracement, tolerance):
        """Check if price is finding support at Fibonacci levels"""
        try:
            if len(data) < lookback_period + 5:
                return False
            
            # Use recent data to check for support confirmation
            recent_data = data.tail(10)  # Last 10 days
            lows = recent_data['low']
            closes = recent_data['close']
            
            # Check for higher lows (support forming)
            recent_lows = lows.tail(5).values
            
            # Simple check: are recent lows trending higher?
            higher_lows = all(recent_lows[i] >= recent_lows[i-1] for i in range(1, len(recent_lows)))
            
            # Check if current price is above recent low
            current_price = closes.iloc[-1]
            recent_low = lows.min()
            price_recovery = current_price > recent_low * 1.01  # 1% above recent low
            
            return higher_lows and price_recovery
            
        except Exception as e:
            print(f"Error checking Fibonacci support: {str(e)}")
            return False
    
    def _calculate_trend(self, values):
        """Calculate trend direction from array of values"""
        if len(values) < 2:
            return "Belirsiz"
        
        # Calculate simple trend
        increases = 0
        decreases = 0
        
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                increases += 1
            elif values[i] < values[i-1]:
                decreases += 1
        
        if increases > decreases:
            return "Yükseliş"
        elif decreases > increases:
            return "Düşüş"
        else:
            return "Yatay"
    
    def batch_analyze(self, symbols, period='5d', interval='1d', sma_period=10, min_volume_ratio=1.5):
        """
        Analyze multiple stocks in batch
        
        Args:
            symbols (list): List of stock symbols
            period (str): Time period
            interval (str): Data interval
            sma_period (int): SMA period
            min_volume_ratio (float): Minimum volume ratio threshold
            
        Returns:
            list: Analysis results for stocks meeting criteria
        """
        results = []
        
        for symbol in symbols:
            try:
                analysis = self.analyze_stock_volume(symbol, period, interval, sma_period)
                
                if analysis and analysis['volume_ratio'] >= min_volume_ratio:
                    results.append(analysis)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in batch analysis for {symbol}: {str(e)}")
                continue
        
        # Sort by volume ratio descending
        results.sort(key=lambda x: x['volume_ratio'], reverse=True)
        
        return results
    
    def get_summary_stats(self, analyses):
        """Get summary statistics from analyses"""
        if not analyses:
            return {}
        
        volume_ratios = [a['volume_ratio'] for a in analyses]
        
        return {
            'total_stocks': len(analyses),
            'avg_volume_ratio': np.mean(volume_ratios),
            'max_volume_ratio': max(volume_ratios),
            'min_volume_ratio': min(volume_ratios),
            'median_volume_ratio': np.median(volume_ratios)
        }
    
    def get_fundamental_data(self, symbol, period='1y'):
        """Get fundamental data for a stock using yfinance"""
        try:
            # Get historical data
            data = self.data_fetcher.get_stock_data(symbol, period)
            if data is None or data.empty:
                print(f"No historical data available for {symbol}")
                return None

            # Calculate basic metrics
            current_price = data['close'].iloc[-1]
            market_data = {
                'symbol': symbol,
                'current_price': current_price,
                'volume': data['volume'].iloc[-1],
                'avg_volume': data['volume'].mean(),
                'price_change_1m': ((current_price - data['close'].iloc[-22]) / data['close'].iloc[-22] * 100) if len(data) > 22 else 0,
                'price_change_3m': ((current_price - data['close'].iloc[-66]) / data['close'].iloc[-66] * 100) if len(data) > 66 else 0,
                'price_change_6m': ((current_price - data['close'].iloc[-132]) / data['close'].iloc[-132] * 100) if len(data) > 132 else 0,
                'volatility': data['close'].pct_change().std() * 100,
            }
            
            # Calculate technical indicators
            market_data['rsi'] = self._calculate_rsi(data['close'])

            # Try to get real fundamental data from Yahoo Finance
            try:
                import yfinance as yf
                yf_symbol = f"{symbol}.IS" if not symbol.endswith('.IS') else symbol
                ticker = yf.Ticker(yf_symbol)
                
                info = ticker.info
                
                # P/E Ratio - Strict Check
                pe_ratio = info.get('trailingPE') or info.get('forwardPE')
                if pe_ratio and 0 < pe_ratio < 1000:
                    market_data['pe_ratio'] = pe_ratio
                    print(f"✅ {symbol}: Gerçek P/E bulundu: {pe_ratio:.1f}")
                else:
                    print(f"❌ {symbol}: Gerçek P/E verisi bulunamadı, hisse atlanıyor.")
                    return None

                # P/B Ratio - Strict Check
                pb_ratio = info.get('priceToBook')
                if pb_ratio and 0 < pb_ratio < 100:
                    market_data['pb_ratio'] = pb_ratio
                    print(f"✅ {symbol}: Gerçek P/B bulundu: {pb_ratio:.2f}")
                else:
                    print(f"❌ {symbol}: Gerçek P/B verisi bulunamadı, hisse atlanıyor.")
                    return None

                # Market Cap
                market_cap = info.get('marketCap')
                if market_cap and market_cap > 0:
                    market_data['market_cap_est'] = market_cap
                else:
                    market_data['market_cap_est'] = current_price * 1000000  # Estimated

                # Other financial ratios - if not found, use a default value or skip
                market_data['roe'] = info.get('returnOnEquity') or 0
                market_data['debt_equity_ratio'] = info.get('debtToEquity') or 0
                market_data['revenue_growth'] = info.get('revenueGrowth') or 0
                market_data['profit_margin'] = info.get('profitMargins') or 0
                market_data['dividend_yield'] = (info.get('dividendYield') or 0) * 100

            except Exception as e:
                print(f"❌ {symbol}: Yahoo Finance hatası: {e}. Hisse atlanıyor.")
                return None
            
            return market_data
            
        except Exception as e:
            print(f"Error getting fundamental data for {symbol}: {e}")
            return None
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not rsi.empty else 50
        except:
            return 50

    def _ema(self, series, span):
        try:
            return series.ewm(span=span, adjust=False).mean()
        except Exception:
            return None

    def _macd(self, close_series):
        """Compute MACD line and signal (12,26,9)"""
        try:
            ema12 = self._ema(close_series, 12)
            ema26 = self._ema(close_series, 26)
            if ema12 is None or ema26 is None:
                return None, None, None
            macd_line = ema12 - ema26
            signal = self._ema(macd_line, 9)
            hist = macd_line - signal
            return macd_line, signal, hist
        except Exception:
            return None, None, None

    def _sma(self, series, window):
        try:
            return series.rolling(window=window).mean()
        except Exception:
            return None

    def _get_financial_frames(self, symbol):
        """Fetch annual income, balance, cashflow, dividends using yfinance."""
        try:
            import yfinance as yf
            yf_symbol = f"{symbol}.IS" if not symbol.endswith('.IS') else symbol
            t = yf.Ticker(yf_symbol)
            # In yfinance>=0.2, properties return DataFrames with columns as periods
            income = getattr(t, 'income_stmt', None)
            balance = getattr(t, 'balance_sheet', None)
            cashflow = getattr(t, 'cashflow', None)
            dividends = getattr(t, 'dividends', None)
            return income, balance, cashflow, dividends
        except Exception as e:
            print(f"{symbol}: Finansal tablolar alınamadı: {e}")
            return None, None, None, None

    def _last_n_annual(self, df, keys, n=4):
        """Get last n annual values for the first matching key in keys list."""
        try:
            if df is None or df.empty:
                return None
            idx_candidates = keys
            row = None
            for k in idx_candidates:
                if k in df.index:
                    row = df.loc[k]
                    break
            if row is None:
                # Try case-insensitive
                lower_map = {i.lower(): i for i in df.index}
                for k in keys:
                    if k.lower() in lower_map:
                        row = df.loc[lower_map[k.lower()]]
                        break
            if row is None:
                return None
            # Ensure numeric and ordered by date ascending
            vals = row.dropna()
            if hasattr(vals, 'sort_index'):
                try:
                    vals = vals.sort_index()
                except Exception:
                    pass
            # Return last n values as list
            return list(vals.astype(float).values)[-n:]
        except Exception:
            return None

    def _avg_yoy_growth(self, series_vals):
        """Compute average YoY growth from consecutive annual values."""
        try:
            if not series_vals or len(series_vals) < 3:
                return None
            growths = []
            for i in range(1, len(series_vals)):
                prev, cur = series_vals[i-1], series_vals[i]
                if prev and abs(prev) > 1e-6:
                    growths.append((cur - prev) / abs(prev))
            if not growths:
                return None
            return float(np.mean(growths) * 100.0)
        except Exception:
            return None

    def analyze_single_stock(self, symbol, period='1y', scoring_params=None):
        """Analyze a single BIST stock with fundamental (max 20) and technical (max 10) criteria.
        Returns dict with detailed scoring and recommendation.
        
        Args:
            symbol: Stock symbol to analyze
            period: Data period
            scoring_params: Dict with custom thresholds from UI
        """
        # Default scoring parameters if not provided
        if scoring_params is None:
            scoring_params = {}
        
        # Set default thresholds
        pe_excellent = scoring_params.get('pe_excellent', 8.0)
        pe_good = scoring_params.get('pe_good', 15.0)
        pb_excellent = scoring_params.get('pb_excellent', 1.0)
        pb_good = scoring_params.get('pb_good', 2.0)
        roe_excellent = scoring_params.get('roe_excellent', 15.0)
        roe_good = scoring_params.get('roe_good', 10.0)
        margin_excellent = scoring_params.get('margin_excellent', 10.0)
        margin_good = scoring_params.get('margin_good', 5.0)
        debt_excellent = scoring_params.get('debt_excellent', 1.0)
        debt_good = scoring_params.get('debt_good', 2.0)
        rsi_good_min = scoring_params.get('rsi_good_min', 40.0)
        rsi_good_max = scoring_params.get('rsi_good_max', 60.0)
        sma_tolerance = scoring_params.get('sma_tolerance', 2.0)
        volume_multiplier = scoring_params.get('volume_multiplier', 1.2)
        macd_tolerance = scoring_params.get('macd_tolerance', 0.01)
        
        # Fetch base market and fundamental snapshot (uses strict real data for P/E & P/B)
        fundamentals = self.get_fundamental_data(symbol, period)
        if not fundamentals:
            return None

        # Fetch price history for technicals
        data = self.data_fetcher.get_stock_data(symbol, period)
        if data is None or data.empty or len(data) < 50:
            print(f"{symbol}: Yetersiz fiyat verisi")
            return None

        close = data['close']
        volume = data['volume']
        current_price = close.iloc[-1]

        # Technical indicators
        sma50 = self._sma(close, 50)
        sma200 = self._sma(close, 200) if len(close) >= 200 else None
        rsi = self._calculate_rsi(close)
        macd_line, macd_signal, macd_hist = self._macd(close)
        vol20 = volume.rolling(20).mean()

        # Fundamental additional metrics
        income, balance, cashflow, dividends = self._get_financial_frames(symbol)
        # Revenue and Net Income growth (3Y avg)
        rev_vals = self._last_n_annual(income, [
            'Total Revenue', 'TotalRevenue', 'Revenue'
        ], n=4)
        ni_vals = self._last_n_annual(income, [
            'Net Income', 'NetIncome', 'Net Income Applicable To Common Shares'
        ], n=4)
        rev_growth_3y = self._avg_yoy_growth(rev_vals)
        ni_growth_3y = self._avg_yoy_growth(ni_vals)

        # EV/EBITDA (FD/FAVÖK)
        ev_ebitda = None
        try:
            import yfinance as yf
            yf_symbol = f"{symbol}.IS" if not symbol.endswith('.IS') else symbol
            info = yf.Ticker(yf_symbol).info
            ev_ebitda = info.get('enterpriseToEbitda')
            if not ev_ebitda:
                ev = info.get('enterpriseValue')
                ebitda = info.get('ebitda')
                if ev and ebitda and ebitda != 0:
                    ev_ebitda = ev / ebitda
        except Exception:
            pass

        # Current ratio
        current_ratio = None
        try:
            ca_vals = self._last_n_annual(balance, ['Total Current Assets', 'CurrentAssets'])
            cl_vals = self._last_n_annual(balance, ['Total Current Liabilities', 'CurrentLiabilities'])
            if ca_vals and cl_vals and ca_vals[-1] and cl_vals[-1] and cl_vals[-1] != 0:
                current_ratio = ca_vals[-1] / cl_vals[-1]
        except Exception:
            pass

        # Operating cash flow
        ocf_vals = self._last_n_annual(cashflow, [
            'Operating Cash Flow', 'Total Cash From Operating Activities', 'OperatingCashFlow'
        ])
        ocf_last = ocf_vals[-1] if ocf_vals else None

        # Dividend regularity (last 3 years payments)
        div_points_support = 0
        div_yield = fundamentals.get('dividend_yield') or 0
        try:
            if dividends is not None and not dividends.empty:
                last3y = dividends[dividends.index >= (dividends.index.max() - pd.DateOffset(years=3))]
                paid_years = last3y.index.year.unique()
                if len(paid_years) >= 2:
                    div_points_support = 1
                if len(paid_years) >= 3:
                    div_points_support = 2
        except Exception:
            pass

        # --- Scoring ---
        fundamental_points = 0
        fundamental_breakdown = []

        # Selected 10 criteria (max 20 pts)
        # 1) P/E lower is better
        pe = fundamentals.get('pe_ratio')
        pe_pts = 2 if pe is not None and pe <= pe_excellent else (1 if pe is not None and pe <= pe_good else 0)
        fundamental_points += pe_pts
        fundamental_breakdown.append({'Kriter': 'F/K Oranı', 'Değer': pe, 'Puan': pe_pts})

        # 2) P/B lower is better (<1 ideal)
        pb = fundamentals.get('pb_ratio')
        pb_pts = 2 if pb is not None and pb < pb_excellent else (1 if pb is not None and pb <= pb_good else 0)
        fundamental_points += pb_pts
        fundamental_breakdown.append({'Kriter': 'PD/DD Oranı', 'Değer': pb, 'Puan': pb_pts})

        # 3) EV/EBITDA
        ev_ebitda_pts = 2 if ev_ebitda is not None and ev_ebitda < 6 else (1 if ev_ebitda is not None and ev_ebitda <= 8 else 0)
        fundamental_points += ev_ebitda_pts
        fundamental_breakdown.append({'Kriter': 'FD/FAVÖK', 'Değer': ev_ebitda, 'Puan': ev_ebitda_pts})

        # 4) Net Profit Margin
        npm = fundamentals.get('profit_margin')
        npm_pct = npm * 100 if npm is not None and npm < 1 else npm  # yfinance often returns fraction
        if npm_pct is None:
            npm_pct = 0
        npm_pts = 2 if npm_pct >= margin_excellent else (1 if npm_pct >= margin_good else 0)
        fundamental_points += npm_pts
        fundamental_breakdown.append({'Kriter': 'Net Kâr Marjı (%)', 'Değer': npm_pct, 'Puan': npm_pts})

        # 5) Sales Growth 3Y avg
        sg = rev_growth_3y if rev_growth_3y is not None else 0
        sg_pts = 2 if sg >= 10 else (1 if sg >= 5 else 0)
        fundamental_points += sg_pts
        fundamental_breakdown.append({'Kriter': 'Satış Büyümesi 3Y (%)', 'Değer': sg, 'Puan': sg_pts})

        # 6) Net Profit Growth 3Y
        ng = ni_growth_3y if ni_growth_3y is not None else 0
        ng_pts = 2 if ng >= 10 else (1 if ng > 0 else 0)
        fundamental_points += ng_pts
        fundamental_breakdown.append({'Kriter': 'Net Kâr Büyümesi 3Y (%)', 'Değer': ng, 'Puan': ng_pts})

        # 7) ROE
        roe = fundamentals.get('roe')
        roe_pct = roe * 100 if roe is not None and roe < 1 else roe
        if roe_pct is None:
            roe_pct = 0
        roe_pts = 2 if roe_pct >= roe_excellent else (1 if roe_pct >= roe_good else 0)
        fundamental_points += roe_pts
        fundamental_breakdown.append({'Kriter': 'ROE (%)', 'Değer': roe_pct, 'Puan': roe_pts})

        # 8) Debt/Equity
        de = fundamentals.get('debt_equity_ratio')
        de_pts = 2 if de is not None and de < debt_excellent else (1 if de is not None and de <= debt_good else 0)
        fundamental_points += de_pts
        fundamental_breakdown.append({'Kriter': 'Borç/Özkaynak', 'Değer': de, 'Puan': de_pts})

        # 9) Current Ratio
        cr = current_ratio if current_ratio is not None else 0
        cr_pts = 2 if cr >= 1.5 else (1 if cr >= 1.0 else 0)
        fundamental_points += cr_pts
        fundamental_breakdown.append({'Kriter': 'Cari Oran', 'Değer': cr, 'Puan': cr_pts})

        # 10) Operating Cash Flow
        ocf_pts = 2 if ocf_last is not None and ocf_last > 0 and (ni_vals and ni_vals[-1] and ni_vals[-1] > 0) else (1 if ocf_last is not None and ocf_last > 0 else 0)
        fundamental_points += ocf_pts
        fundamental_breakdown.append({'Kriter': 'Faaliyet Nakit Akımı', 'Değer': ocf_last, 'Puan': ocf_pts})

        # Fundamental cap at 20
        if fundamental_points > 20:
            fundamental_points = 20

        # Technical scoring (max 10)
        technical_points = 0
        technical_breakdown = []

        # Price above SMA200
        if sma200 is not None and not np.isnan(sma200.iloc[-1]):
            p200_pts = 2 if current_price > sma200.iloc[-1] else 0
            technical_points += p200_pts
            technical_breakdown.append({'Kriter': 'Fiyat > SMA200', 'Değer': f"{current_price:.2f} > {sma200.iloc[-1]:.2f}", 'Puan': p200_pts})
        else:
            technical_breakdown.append({'Kriter': 'Fiyat > SMA200', 'Değer': 'Veri yok', 'Puan': 0})

        # Price above SMA50
        if sma50 is not None and not np.isnan(sma50.iloc[-1]):
            p50_pts = 2 if current_price > sma50.iloc[-1] else 0
            technical_points += p50_pts
            technical_breakdown.append({'Kriter': 'Fiyat > SMA50', 'Değer': f"{current_price:.2f} > {sma50.iloc[-1]:.2f}", 'Puan': p50_pts})
        else:
            technical_breakdown.append({'Kriter': 'Fiyat > SMA50', 'Değer': 'Veri yok', 'Puan': 0})

        # RSI scoring
        rsi_pts = 2 if rsi >= rsi_good_max else (1 if rsi_good_min <= rsi <= rsi_good_max else 0)
        technical_points += rsi_pts
        technical_breakdown.append({'Kriter': 'RSI(14)', 'Değer': f"{rsi:.1f}", 'Puan': rsi_pts})

        # MACD
        if macd_line is not None and macd_signal is not None:
            macd_pts = 2 if macd_line.iloc[-1] > macd_signal.iloc[-1] else 0
            technical_points += macd_pts
            technical_breakdown.append({'Kriter': 'MACD', 'Değer': 'Pozitif' if macd_pts==2 else 'Negatif', 'Puan': macd_pts})
        else:
            technical_breakdown.append({'Kriter': 'MACD', 'Değer': 'Veri yok', 'Puan': 0})

        # Volume vs 20-day average
        if vol20 is not None and not np.isnan(vol20.iloc[-1]):
            vol_pts = 2 if volume.iloc[-1] > (vol20.iloc[-1] * volume_multiplier) else 0
            technical_points += vol_pts
            technical_breakdown.append({'Kriter': 'Hacim > 20G Ort.', 'Değer': f"{volume.iloc[-1]:.0f} vs {vol20.iloc[-1]*volume_multiplier:.0f}", 'Puan': vol_pts})
        else:
            technical_breakdown.append({'Kriter': 'Hacim > 20G Ort.', 'Değer': 'Veri yok', 'Puan': 0})

        total_points = fundamental_points + technical_points  # max 30

        # Recommendation mapping
        if total_points >= 20:
            reco = 'Güçlü Al'
        elif total_points >= 16:
            reco = 'Al'
        elif total_points >= 12:
            reco = 'Tut'
        elif total_points >= 8:
            reco = 'Sat'
        else:
            reco = 'Güçlü Sat'

        return {
            'symbol': symbol,
            'fundamental_points': fundamental_points,
            'technical_points': technical_points,
            'total_points': total_points,
            'recommendation': reco,
            'fundamental_breakdown': fundamental_breakdown,
            'technical_breakdown': technical_breakdown,
            'price': current_price,
            # Useful fields for batch display
            'pe_ratio': pe,
            'pb_ratio': pb
        }

    def analyze_stocks_comprehensive(self, period='1y', min_total_points=0, progress_callback=None, limit=None, sleep_sec=0.1, scoring_params=None):
        """Batch analyze all BIST stocks using the same 30-point scoring.

        Args:
            period (str): Data period to use for analysis.
            min_total_points (int): Minimum total points filter (0-30).
            progress_callback (callable): Optional progress reporter fn(i, total, symbol).
            limit (int|None): Optional max number of stocks to analyze (for quick tests).
            sleep_sec (float): Throttle between requests.
            scoring_params (dict): Custom scoring parameters from UI controls.

        Returns:
            list[dict]: List of per-stock score summaries.
        """
        stocks = self.get_bist_stocks()
        if not stocks:
            return []

        total = len(stocks) if limit is None else min(limit, len(stocks))
        results = []

        for idx, symbol in enumerate(stocks[:total], start=1):
            try:
                if progress_callback:
                    progress_callback(idx, total, symbol)

                res = self.analyze_single_stock(symbol, period, scoring_params=scoring_params)
                if res and res.get('total_points', 0) >= min_total_points:
                    results.append(res)
            except Exception as e:
                print(f"Comprehensive scan error on {symbol}: {e}")
            finally:
                try:
                    time.sleep(sleep_sec)
                except Exception:
                    pass

        # Sort by total points desc, then fundamental points desc
        results.sort(key=lambda x: (x.get('total_points', 0), x.get('fundamental_points', 0)), reverse=True)
        return results
    
    def screen_stocks_fundamental(self, scan_type, params, progress_callback=None, restrict_symbols=None):
        """Screen stocks based on fundamental criteria with progress tracking"""
        try:
            stocks = restrict_symbols if restrict_symbols else self.get_bist_stocks()
            if not stocks:
                return []
            
            results = []
            total_stocks = len(stocks)
            scan_limit = total_stocks  # Scan all stocks, no limit
            
            for i, symbol in enumerate(stocks[:scan_limit]):
                try:
                    # Progress callback for UI updates
                    if progress_callback:
                        progress_callback(i + 1, scan_limit, symbol)
                    
                    fundamental_data = self.get_fundamental_data(symbol, params.get('period', '1y'))
                    if fundamental_data is None:
                        continue
                    
                    # Apply filters based on scan type
                    if self._passes_fundamental_criteria(fundamental_data, scan_type, params):
                        results.append(fundamental_data)
                        print(f"🎯 BULUNAN: {symbol} - Kriterleri karşılıyor!")
                    else:
                        # Debug: Show which criterion failed
                        print(f"❌ {symbol}: Kriterleri karşılamıyor")
                        
                except Exception as e:
                    print(f"⚠️ {symbol}: Hata - {e}")
                    continue
            
            # Sort results based on scan type
            results = self._sort_fundamental_results(results, scan_type)
            
            return results[:50]  # Return top 50 results instead of 20
            
        except Exception as e:
            print(f"Temel tarama hatası: {e}")
            return []
    
    def _passes_fundamental_criteria(self, data, scan_type, params):
        """Check if stock passes fundamental screening criteria"""
        try:
            market_cap = data.get('market_cap_est', 0)
            min_market_cap = params.get('min_market_cap', 100) * 1000000  # Convert to TL
            max_market_cap = params.get('max_market_cap', 100000) * 1000000
            
            # Market cap filter
            if market_cap < min_market_cap or market_cap > max_market_cap:
                return False
            
            # Apply specific criteria based on scan type
            if scan_type == 'low_pe':
                pe_ratio = data.get('pe_ratio', 100)
                min_pe = params.get('min_pe', 0)
                max_pe = params.get('max_pe', 15)
                result = min_pe <= pe_ratio <= max_pe
                # Debug info
                if result:
                    print(f"✓ {data.get('symbol', 'UNKNOWN')}: P/E={pe_ratio:.1f} (aralık: {min_pe}-{max_pe})")
                return result
            
            elif scan_type == 'high_roe':
                roe = data.get('roe', 0)
                min_roe = params.get('min_roe', 15)
                max_roe = params.get('max_roe', 100)
                return min_roe <= roe <= max_roe
            
            elif scan_type == 'low_pb':
                pb_ratio = data.get('pb_ratio', 100)
                min_pb = params.get('min_pb', 0)
                max_pb = params.get('max_pb', 2)
                return min_pb <= pb_ratio <= max_pb
            
            elif scan_type == 'dividend':
                dividend_yield = data.get('dividend_yield', 0)
                min_dividend = params.get('min_dividend', 3)
                max_dividend = params.get('max_dividend', 20)
                return min_dividend <= dividend_yield <= max_dividend
            
            elif scan_type == 'low_debt':
                debt_equity = data.get('debt_equity_ratio', 10)
                min_debt_equity = params.get('min_debt_equity', 0)
                max_debt_equity = params.get('max_debt_equity', 1)
                result = min_debt_equity <= debt_equity <= max_debt_equity
                # Debug info
                if result:
                    print(f"✓ {data.get('symbol', 'UNKNOWN')}: B/Ö={debt_equity:.1f} (aralık: {min_debt_equity}-{max_debt_equity})")
                return result
            
            elif scan_type == 'revenue_growth':
                revenue_growth = data.get('revenue_growth', -100)
                min_revenue_growth = params.get('min_revenue_growth', 10)
                max_revenue_growth = params.get('max_revenue_growth', 50)
                result = min_revenue_growth <= revenue_growth <= max_revenue_growth
                # Debug info
                if result:
                    print(f"✓ {data.get('symbol', 'UNKNOWN')}: Gelir Artışı={revenue_growth:.1f}% (aralık: {min_revenue_growth}%-{max_revenue_growth}%)")
                return result
            
            elif scan_type == 'profit_margin':
                profit_margin = data.get('profit_margin', 0)
                min_profit_margin = params.get('min_profit_margin', 10)
                max_profit_margin = params.get('max_profit_margin', 40)
                result = min_profit_margin <= profit_margin <= max_profit_margin
                # Debug info
                if result:
                    print(f"✓ {data.get('symbol', 'UNKNOWN')}: Kar Marjı={profit_margin:.1f}% (aralık: {min_profit_margin}%-{max_profit_margin}%)")
                return result
            
            elif scan_type == 'combined_value':
                # Check all criteria for combined value screening
                pe_ratio = data.get('pe_ratio', 100)
                pb_ratio = data.get('pb_ratio', 100)
                roe = data.get('roe', 0)
                debt_equity = data.get('debt_equity_ratio', 10)
                
                max_pe = params.get('max_pe', 15)
                max_pb = params.get('max_pb', 2)
                min_roe = params.get('min_roe', 15)
                max_debt_equity = params.get('max_debt_equity', 1)
                
                pe_ok = pe_ratio <= max_pe
                pb_ok = pb_ratio <= max_pb
                roe_ok = roe >= min_roe
                debt_ok = debt_equity <= max_debt_equity
                
                result = pe_ok and pb_ok and roe_ok and debt_ok
                # Debug info
                if result:
                    print(f"✓ {data.get('symbol', 'UNKNOWN')}: KOMBINE DEĞER - P/E={pe_ratio:.1f}, P/B={pb_ratio:.1f}, ROE={roe:.1f}%, B/Ö={debt_equity:.1f}")
                return result
            
            elif scan_type == 'high_volume':
                avg_volume = data.get('avg_volume', 0)
                return avg_volume >= params.get('min_volume', 1000000)
            
            elif scan_type == 'momentum':
                price_change = data.get('price_change_1m', 0)
                return price_change >= params.get('min_momentum', 10)
            
            elif scan_type == 'value':
                pe_ok = data.get('pe_ratio', 100) <= params.get('max_pe', 15)
                pb_ok = data.get('pb_ratio', 100) <= params.get('max_pb', 2)
                return pe_ok and pb_ok
            
            elif scan_type == 'growth':
                price_3m = data.get('price_change_3m', 0)
                price_6m = data.get('price_change_6m', 0)
                return price_3m >= 15 and price_6m >= 25
            
            return True
            
        except Exception as e:
            return False
    
    def _sort_fundamental_results(self, results, scan_type):
        """Sort results based on scan type criteria"""
        try:
            if scan_type == 'low_pe':
                return sorted(results, key=lambda x: x.get('pe_ratio', 100))
            elif scan_type == 'high_roe':
                return sorted(results, key=lambda x: x.get('roe', 0), reverse=True)
            elif scan_type == 'low_pb':
                return sorted(results, key=lambda x: x.get('pb_ratio', 100))
            elif scan_type == 'dividend':
                return sorted(results, key=lambda x: x.get('dividend_yield', 0), reverse=True)
            elif scan_type == 'low_debt':
                return sorted(results, key=lambda x: x.get('debt_equity_ratio', 10))
            elif scan_type == 'revenue_growth':
                return sorted(results, key=lambda x: x.get('revenue_growth', -100), reverse=True)
            elif scan_type == 'profit_margin':
                return sorted(results, key=lambda x: x.get('profit_margin', 0), reverse=True)
            elif scan_type == 'combined_value':
                # Sort by best overall value score (low P/E + low P/B + high ROE + low debt)
                return sorted(results, key=lambda x: (x.get('pe_ratio', 100) + x.get('pb_ratio', 100)) - x.get('roe', 0) + x.get('debt_equity_ratio', 10))
            elif scan_type == 'high_volume':
                return sorted(results, key=lambda x: x.get('avg_volume', 0), reverse=True)
            elif scan_type == 'momentum':
                return sorted(results, key=lambda x: x.get('price_change_1m', 0), reverse=True)
            elif scan_type == 'value':
                return sorted(results, key=lambda x: x.get('pe_ratio', 100) + x.get('pb_ratio', 100))
            elif scan_type == 'growth':
                return sorted(results, key=lambda x: x.get('price_change_3m', 0) + x.get('price_change_6m', 0), reverse=True)
            else:
                return results
        except:
            return results
