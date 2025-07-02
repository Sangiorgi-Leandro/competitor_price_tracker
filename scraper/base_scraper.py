"""
Base Scraper - Classe astratta per tutti gli scrapers.

Fornisce funzionalità comuni come gestione HTTP, parsing,
validazione dati e gestione errori.
"""

import re
import time
import aiohttp
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from decimal import Decimal, InvalidOperation


@dataclass
class ScrapingResult:
    """Risultato dello scraping di un sito."""
    site: str
    title: str
    price_text: str
    formatted_price: str
    price_numeric: float
    currency: str
    url: str
    success: bool
    error_message: Optional[str] = None
    response_time: float = 0.0
    scraped_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte il risultato in dizionario."""
        return asdict(self)
    
    @classmethod
    def failed_result(cls, site: str, url: str, error: str, response_time: float = 0.0):
        """Crea un risultato di fallimento."""
        return cls(
            site=site,
            title="",
            price_text="",
            formatted_price="",
            price_numeric=0.0,
            currency="EUR",
            url=url,
            success=False,
            error_message=error,
            response_time=response_time
        )


class BaseScraper(ABC):
    """Classe base astratta per tutti gli scrapers."""
    
    def __init__(self, site_config, settings_config):
        """
        Inizializza lo scraper base.
        
        Args:
            site_config: Configurazione specifica del sito
            settings_config: Configurazioni generali
        """
        self.site_config = site_config
        self.settings = settings_config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Timeout per le richieste HTTP
        self.timeout = aiohttp.ClientTimeout(total=self.settings.timeout)
        
        # Pattern regex per pulizia prezzi
        self.price_patterns = [
            r'[€$£¥]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',  # Standard europeo
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # Formato italiano
            r'(\d+[.,]\d{2})',  # Semplice con decimali
            r'(\d+)'  # Solo numeri interi
        ]
    
    async def scrape(self) -> ScrapingResult:
        """
        Esegue lo scraping del sito.
        Template method che orchestia il processo di scraping.
        """
        start_time = time.time()
        
        try:
            self.logger.debug(f"Inizio scraping {self.site_config.name}")
            
            # Effettua la richiesta HTTP
            html_content = await self._fetch_page()
            
            # Parse della pagina
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Estrae i dati (metodo da implementare nelle sottoclassi)
            title = await self._extract_title(soup)
            price_text, price_numeric = await self._extract_price(soup)
            
            # Valida i dati estratti
            self._validate_extracted_data(title, price_text, price_numeric)
            
            # Crea il risultato
            response_time = time.time() - start_time
            
            return ScrapingResult(
                site=self.site_config.name,
                title=title.strip(),
                price_text=price_text,
                formatted_price=self._format_price(price_numeric),
                price_numeric=price_numeric,
                currency="EUR",
                url=self.site_config.url,
                success=True,
                response_time=response_time,
                scraped_at=self._get_timestamp()
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Errore scraping {self.site_config.name}: {str(e)}"
            self.logger.error(error_msg)
            
            return ScrapingResult.failed_result(
                site=self.site_config.name,
                url=self.site_config.url,
                error=error_msg,
                response_time=response_time
            )
    
    async def _fetch_page(self) -> str:
        """Effettua la richiesta HTTP e restituisce il contenuto HTML."""
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=self.site_config.headers
        ) as session:
            
            self.logger.debug(f"Richiesta HTTP a: {self.site_config.url}")
            
            async with session.get(self.site_config.url) as response:
                # Verifica status code
                if response.status != 200:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}"
                    )
                
                # Legge il contenuto
                content = await response.text(encoding='utf-8')
                
                self.logger.debug(f"Ricevuti {len(content)} caratteri da {self.site_config.name}")
                return content
    
    @abstractmethod
    async def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        Estrae il titolo del prodotto dalla pagina.
        Da implementare nelle sottoclassi.
        """
        pass
    
    @abstractmethod
    async def _extract_price(self, soup: BeautifulSoup) -> tuple[str, float]:
        """
        Estrae il prezzo dalla pagina.
        Da implementare nelle sottoclassi.
        
        Returns:
            tuple: (prezzo_testo, prezzo_numerico)
        """
        pass
    
    def _extract_text_by_selector(self, soup: BeautifulSoup, selector: str, 
                                  default: str = "") -> str:
        """
        Utility per estrarre testo tramite selettore CSS.
        
        Args:
            soup: Oggetto BeautifulSoup
            selector: Selettore CSS
            default: Valore di default se non trovato
            
        Returns:
            str: Testo estratto o valore di default
        """
        try:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
            else:
                self.logger.warning(f"Elemento non trovato con selettore: {selector}")
                return default
        except Exception as e:
            self.logger.error(f"Errore nell'estrazione con selettore {selector}: {e}")
            return default
    
    def _parse_price(self, price_text: str) -> float:
        """
        Converte il testo del prezzo in valore numerico.
        
        Args:
            price_text: Testo contenente il prezzo
            
        Returns:
            float: Prezzo numerico
            
        Raises:
            ValueError: Se il prezzo non può essere parsato
        """
        if not price_text:
            raise ValueError("Testo prezzo vuoto")
        
        # Pulisce il testo
        clean_text = price_text.strip()
        
        # Prova con i diversi pattern
        for pattern in self.price_patterns:
            match = re.search(pattern, clean_text)
            if match:
                price_str = match.group(1)
                
                # Gestisce i separatori decimali europei
                if ',' in price_str and '.' in price_str:
                    # Formato tipo 1.234,56
                    price_str = price_str.replace('.', '').replace(',', '.')
                elif ',' in price_str:
                    # Controlla se è separatore decimale o migliaia
                    parts = price_str.split(',')
                    if len(parts) == 2 and len(parts[1]) == 2:
                        # È un separatore decimale (es: 123,45)
                        price_str = price_str.replace(',', '.')
                    else:
                        # È separatore migliaia (es: 1,234)
                        price_str = price_str.replace(',', '')
                
                try:
                    price_float = float(price_str)
                    self.logger.debug(f"Prezzo parsato: '{price_text}' -> {price_float}")
                    return price_float
                except ValueError:
                    continue
        
        raise ValueError(f"Impossibile parsare il prezzo: '{price_text}'")
    
    def _validate_extracted_data(self, title: str, price_text: str, price_numeric: float):
        """
        Valida i dati estratti.
        
        Args:
            title: Titolo del prodotto
            price_text: Testo del prezzo
            price_numeric: Prezzo numerico
            
        Raises:
            ValueError: Se i dati non sono validi
        """
        if not title:
            raise ValueError("Titolo del prodotto non trovato")
        
        if not price_text:
            raise ValueError("Prezzo non trovato")
        
        if price_numeric <= 0:
            raise ValueError(f"Prezzo non valido: {price_numeric}")
        
        # Controlla se il prezzo è nel range ragionevole
        if hasattr(self.settings, 'min_price') and hasattr(self.settings, 'max_price'):
            if not (self.settings.min_price <= price_numeric <= self.settings.max_price):
                self.logger.warning(
                    f"Prezzo fuori range ({self.settings.min_price}-{self.settings.max_price}): "
                    f"{price_numeric}"
                )
    
    def _format_price(self, price: float) -> str:
        """
        Formatta il prezzo per la visualizzazione.
        
        Args:
            price: Prezzo numerico
            
        Returns:
            str: Prezzo formattato (es: "€123,45")
        """
        return f"€{price:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    def _get_timestamp(self) -> str:
        """Restituisce timestamp ISO formato corrente."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def test_selectors(self) -> Dict[str, Any]:
        """
        Testa i selettori configurati e restituisce info di debug.
        Utile per debugging quando i selettori cambiano.
        """
        try:
            html_content = await self._fetch_page()
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Testa selettore titolo
            title_selector = self.site_config.selectors.get('title', '')
            title_element = soup.select_one(title_selector)
            title_found = title_element is not None
            title_text = title_element.get_text(strip=True) if title_element else ""
            
            # Testa selettore prezzo
            price_selector = self.site_config.selectors.get('price', '')
            price_element = soup.select_one(price_selector)
            price_found = price_element is not None
            price_text = price_element.get_text(strip=True) if price_element else ""
            
            return {
                'site': self.site_config.name,
                'url': self.site_config.url,
                'title': {
                    'selector': title_selector,
                    'found': title_found,
                    'text': title_text[:100] + "..." if len(title_text) > 100 else title_text
                },
                'price': {
                    'selector': price_selector,
                    'found': price_found,
                    'text': price_text
                },
                'page_size': len(html_content),
                'timestamp': self._get_timestamp()
            }
            
        except Exception as e:
            return {
                'site': self.site_config.name,
                'error': str(e),
                'timestamp': self._get_timestamp()
            }


# Utility per test rapidi
async def test_scraper(scraper_instance: BaseScraper) -> None:
    """Funzione di utilità per testare un scraper."""
    print(f"🧪 Test scraper: {scraper_instance.site_config.name}")
    print("-" * 50)
    
    # Test selettori
    selector_test = await scraper_instance.test_selectors()
    
    if 'error' in selector_test:
        print(f"❌ Errore: {selector_test['error']}")
        return
    
    print(f"📄 Dimensione pagina: {selector_test['page_size']} caratteri")
    print(f"📝 Titolo ({selector_test['title']['selector']}):")
    print(f"   Trovato: {'✅' if selector_test['title']['found'] else '❌'}")
    if selector_test['title']['found']:
        print(f"   Testo: {selector_test['title']['text']}")
    
    print(f"💰 Prezzo ({selector_test['price']['selector']}):")
    print(f"   Trovato: {'✅' if selector_test['price']['found'] else '❌'}")
    if selector_test['price']['found']:
        print(f"   Testo: {selector_test['price']['text']}")
    
    # Test scraping completo
    print("\n🚀 Test scraping completo...")
    result = await scraper_instance.scrape()
    
    if result.success:
        print(f"✅ Successo!")
        print(f"   Titolo: {result.title}")
        print(f"   Prezzo: {result.formatted_price}")
        print(f"   Tempo: {result.response_time:.2f}s")
    else:
        print(f"❌ Fallito: {result.error_message}")