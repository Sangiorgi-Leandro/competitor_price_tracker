#!/usr/bin/env python3
"""
Competitor Price Tracker - Main Entry Point

Un tracker di prezzi asincrono per monitorare automaticamente 
i prezzi di prodotti su diversi e-commerce italiani.

Autore: Leandro Sangiorgi
Versione: 2.0.0
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import dei moduli personalizzati
from utils.config_manager import get_config_manager, ConfigManager
from scraper.base_scraper import ScrapingResult
from data.price_storage import PriceStorage
from utils.metrics import MetricsCollector


class PriceTracker:
    """Classe principale per il tracking dei prezzi."""
    
    def __init__(self, config_path: str = "config.json"):
        """Inizializza il Price Tracker."""
        self.config: ConfigManager = get_config_manager(config_path)
        self.storage: PriceStorage = PriceStorage(self.config)
        self.metrics: MetricsCollector = MetricsCollector()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        self._setup_logging()
        
        # Import dinamico degli scrapers
        self.scrapers = self._load_scrapers()
        
        self.logger.info(f"🚀 Price Tracker inizializzato per: {self.config.product.name}")
        self.logger.info(f"📊 Siti abilitati: {', '.join(self.config.get_enabled_sites())}")
    
    def _setup_logging(self) -> None:
        """Configura il sistema di logging."""
        log_level = getattr(logging, self.config.settings.log_level.upper())
        
        # Crea la directory dei log se non esiste
        log_dir = self.config.get_log_path()
        
        # Nome file log con data corrente
        log_filename = f"tracker_{datetime.now().strftime('%Y%m%d')}.log"
        log_file_path = log_dir / log_filename
        
        # Configura logging
        logging.basicConfig(
            level=log_level,
            format=self.config.settings.log_format,
            handlers=[
                logging.FileHandler(log_file_path, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Riduci verbosità delle librerie esterne
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    def _load_scrapers(self) -> Dict[str, object]:
        """Carica dinamicamente gli scrapers basati sulla configurazione."""
        scrapers = {}
        
        scraper_mapping = {
            'amazon': 'scraper.amazon.AmazonScraper',
            'phoneclick': 'scraper.phoneclick.PhoneclickScraper',
            'teknozone': 'scraper.teknozone.TeknozoneScraper'
        }
        
        for site_key in self.config.get_enabled_sites():
            if site_key in scraper_mapping:
                try:
                    # Import dinamico
                    module_path, class_name = scraper_mapping[site_key].rsplit('.', 1)
                    module = __import__(module_path, fromlist=[class_name])
                    scraper_class = getattr(module, class_name)
                    
                    # Inizializza lo scraper con la configurazione
                    site_config = self.config.get_site_config(site_key)
                    scrapers[site_key] = scraper_class(site_config, self.config.settings)
                    
                    self.logger.debug(f"✅ Scraper caricato: {site_key}")
                    
                except ImportError as e:
                    self.logger.error(f"❌ Impossibile caricare scraper {site_key}: {e}")
                except Exception as e:
                    self.logger.error(f"❌ Errore nell'inizializzazione scraper {site_key}: {e}")
        
        return scrapers
    
    async def scrape_all_sites(self) -> List[ScrapingResult]:
        """Esegue lo scraping di tutti i siti configurati in parallelo."""
        if not self.scrapers:
            self.logger.error("❌ Nessun scraper disponibile")
            return []
        
        self.logger.info(f"🔍 Avvio scraping su {len(self.scrapers)} siti...")
        start_time = time.time()
        
        # Crea le tasks per lo scraping asincrono
        tasks = []
        for site_key, scraper in self.scrapers.items():
            task = asyncio.create_task(
                self._scrape_single_site(site_key, scraper),
                name=f"scrape_{site_key}"
            )
            tasks.append(task)
        
        # Esegue tutte le tasks in parallelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa i risultati
        valid_results = []
        for i, result in enumerate(results):
            site_key = list(self.scrapers.keys())[i]
            
            if isinstance(result, Exception):
                self.logger.error(f"❌ {site_key}: {result}")
                self.metrics.record_failure()
            elif result and result.success:
                valid_results.append(result)
                self.metrics.record_success(result.response_time)
                self.logger.info(f"✅ {result.site}: {result.title} - {result.formatted_price}")
            else:
                self.logger.warning(f"⚠️ {site_key}: Scraping fallito")
                self.metrics.record_failure()
        
        execution_time = time.time() - start_time
        self.logger.info(f"⏱️ Scraping completato in {execution_time:.2f} secondi")
        self.logger.info(f"📊 Successi: {len(valid_results)}/{len(self.scrapers)}")
        
        return valid_results
    
    async def _scrape_single_site(self, site_key: str, scraper) -> Optional[ScrapingResult]:
        """Esegue lo scraping di un singolo sito con gestione errori."""
        try:
            self.logger.debug(f"🔍 Scraping {site_key}...")
            
            # Aggiungi un delay casuale per evitare rilevamento
            import random
            delay = random.uniform(
                self.config.settings.delay_min,
                self.config.settings.delay_max
            )
            await asyncio.sleep(delay)
            
            # Esegui lo scraping
            result = await scraper.scrape()
            
            # Valida il prezzo se disponibile
            if result and result.success and result.price_numeric:
                if not self.config.validate_price(result.price_numeric):
                    self.logger.warning(
                        f"⚠️ {site_key}: Prezzo fuori range "
                        f"(€{result.price_numeric}) - possibile errore"
                    )
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"❌ {site_key}: Timeout dopo {self.config.settings.timeout}s")
        except Exception as e:
            self.logger.error(f"❌ {site_key}: Errore imprevisto - {e}")
        
        return None
    
    async def run_tracking_cycle(self) -> Dict[str, any]:
        """Esegue un ciclo completo di tracking dei prezzi."""
        cycle_start = time.time()
        timestamp = datetime.now()
        
        self.logger.info("=" * 60)
        self.logger.info(f"🚀 Avvio Competitor Price Tracker per {self.config.product.name}")
        self.logger.info("=" * 60)
        
        try:
            # Esegui scraping
            results = await self.scrape_all_sites()
            
            if not results:
                self.logger.warning("⚠️ Nessun dato raccolto in questo ciclo")
                return {
                    'success': False,
                    'timestamp': timestamp.isoformat(),
                    'results': [],
                    'execution_time': time.time() - cycle_start
                }
            
            # Salva i dati
            self.logger.info("💾 Salvataggio dati...")
            await self.storage.save_results(results, timestamp)
            
            # Prepara il report
            execution_time = time.time() - cycle_start
            
            report_data = {
                'success': True,
                'timestamp': timestamp.isoformat(),
                'product': self.config.product.name,
                'results': [result.to_dict() for result in results],
                'execution_time': round(execution_time, 2),
                'success_rate': f"{len(results)}/{len(self.scrapers)}",
                'metrics': {
                    'total_requests': self.metrics.metrics.total_requests,
                    'successful_scrapes': self.metrics.metrics.successful_scrapes,
                    'failed_scrapes': self.metrics.metrics.failed_scrapes,
                    'avg_response_time': round(self.metrics.metrics.avg_response_time, 2)
                }
            }
            
            # Log del report finale
            self.logger.info("=" * 60)
            self.logger.info(f"📊 Raccolti {len(results)} prezzi su {len(self.scrapers)} siti")
            self.logger.info(f"⏱️ Tempo di esecuzione: {execution_time:.2f} secondi")
            self.logger.info(f"💾 Dati salvati in: {self.config.settings.data_directory}/")
            self.logger.info("=" * 60)
            
            return report_data
            
        except Exception as e:
            self.logger.error(f"❌ Errore durante il ciclo di tracking: {e}")
            return {
                'success': False,
                'timestamp': timestamp.isoformat(),
                'error': str(e),
                'execution_time': time.time() - cycle_start
            }
    
    def print_summary(self, report_data: Dict[str, any]) -> None:
        """Stampa un riassunto colorato dei risultati."""
        if not report_data['success']:
            print("❌ Tracking fallito")
            if 'error' in report_data:
                print(f"Errore: {report_data['error']}")
            return
        
        print(f"\n🚀 Competitor Price Tracker - {self.config.product.name}")
        print("-" * 60)
        
        # Mostra i prezzi
        for result_data in report_data['results']:
            site = result_data['site']
            title = result_data['title'][:50] + "..." if len(result_data['title']) > 50 else result_data['title']
            price = result_data['formatted_price']
            print(f"✅ {site}: {title} - {price}")
        
        print("-" * 60)
        print(f"💾 Dati salvati in {self.config.settings.data_directory}/")
        print(f"📊 Raccolti {report_data['success_rate']} prezzi")
        print(f"⏱️ Tempo di esecuzione: {report_data['execution_time']} secondi")


async def main():
    """Funzione principale del programma."""
    try:
        # Inizializza il tracker
        tracker = PriceTracker()
        
        # Esegui un ciclo di tracking
        report = await tracker.run_tracking_cycle()
        
        # Mostra il riassunto
        tracker.print_summary(report)
        
        # Exit code basato sul successo
        return 0 if report['success'] else 1
        
    except KeyboardInterrupt:
        print("\n🛑 Tracking interrotto dall'utente")
        return 130
    except FileNotFoundError as e:
        print(f"❌ File non trovato: {e}")
        print("💡 Suggerimento: Verifica che il file config.json esista")
        return 1
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")
        logging.exception("Errore dettagliato:")
        return 1


if __name__ == "__main__":
    # Esegui il programma
    exit_code = asyncio.run(main())
    sys.exit(exit_code)