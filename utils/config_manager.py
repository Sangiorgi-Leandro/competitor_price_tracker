"""
Gestore della configurazione per il Price Tracker.
Carica e valida i parametri di configurazione dal file JSON.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SiteConfig:
    """Configurazione per un singolo sito e-commerce."""
    name: str
    url: str
    selectors: Dict[str, str]
    headers: Dict[str, str]
    enabled: bool = True


@dataclass
class ProductConfig:
    """Configurazione del prodotto da monitorare."""
    name: str
    description: str


@dataclass
class SettingsConfig:
    """Configurazioni generali dell'applicazione."""
    timeout: int
    max_retries: int
    delay_min: float
    delay_max: float
    min_price: float
    max_price: float
    currency: str
    data_directory: str
    json_filename: str
    csv_filename: str
    log_directory: str
    log_level: str
    log_format: str


class ConfigManager:
    """Gestore centralizzato della configurazione."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self._config_data: Optional[Dict[str, Any]] = None
        self._sites: Dict[str, SiteConfig] = {}
        self._product: Optional[ProductConfig] = None
        self._settings: Optional[SettingsConfig] = None
        
        self.load_config()
    
    def load_config(self) -> None:
        """Carica la configurazione dal file JSON."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"File di configurazione non trovato: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
            
            self._validate_config()
            self._parse_config()
            
            logger.info(f"Configurazione caricata con successo da {self.config_path}")
            
        except FileNotFoundError as e:
            logger.error(f"Errore: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Errore nel parsing JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore imprevisto nel caricamento configurazione: {e}")
            raise
    
    def _validate_config(self) -> None:
        """Valida la struttura della configurazione."""
        required_sections = ['product', 'sites', 'settings']
        
        for section in required_sections:
            if section not in self._config_data:
                raise ValueError(f"Sezione mancante nella configurazione: {section}")
        
        # Valida che almeno un sito sia abilitato
        enabled_sites = [
            site for site, config in self._config_data['sites'].items()
            if config.get('enabled', True)
        ]
        
        if not enabled_sites:
            raise ValueError("Nessun sito abilitato nella configurazione")
        
        logger.debug(f"Configurazione validata. Siti abilitati: {enabled_sites}")
    
    def _parse_config(self) -> None:
        """Converte i dati JSON in oggetti strutturati."""
        # Parse product config
        product_data = self._config_data['product']
        self._product = ProductConfig(
            name=product_data['name'],
            description=product_data['description']
        )
        
        # Parse sites config
        sites_data = self._config_data['sites']
        for site_key, site_data in sites_data.items():
            if site_data.get('enabled', True):
                self._sites[site_key] = SiteConfig(
                    name=site_data['name'],
                    url=site_data['url'],
                    selectors=site_data['selectors'],
                    headers=site_data['headers'],
                    enabled=site_data.get('enabled', True)
                )
        
        # Parse settings config
        settings_data = self._config_data['settings']
        delay_config = settings_data['delay_between_requests']
        price_config = settings_data['price_validation']
        output_config = settings_data['output']
        logging_config = settings_data['logging']
        
        self._settings = SettingsConfig(
            timeout=settings_data['timeout'],
            max_retries=settings_data['max_retries'],
            delay_min=delay_config['min'],
            delay_max=delay_config['max'],
            min_price=price_config['min_price'],
            max_price=price_config['max_price'],
            currency=price_config['currency'],
            data_directory=output_config['data_directory'],
            json_filename=output_config['json_filename'],
            csv_filename=output_config['csv_filename'],
            log_directory=output_config['log_directory'],
            log_level=logging_config['level'],
            log_format=logging_config['format']
        )
    
    @property
    def sites(self) -> Dict[str, SiteConfig]:
        """Restituisce la configurazione dei siti abilitati."""
        return self._sites
    
    @property
    def product(self) -> ProductConfig:
        """Restituisce la configurazione del prodotto."""
        return self._product
    
    @property
    def settings(self) -> SettingsConfig:
        """Restituisce le impostazioni generali."""
        return self._settings
    
    def get_site_config(self, site_key: str) -> Optional[SiteConfig]:
        """Restituisce la configurazione di un sito specifico."""
        return self._sites.get(site_key)
    
    def is_site_enabled(self, site_key: str) -> bool:
        """Verifica se un sito è abilitato."""
        return site_key in self._sites
    
    def get_enabled_sites(self) -> list[str]:
        """Restituisce la lista dei siti abilitati."""
        return list(self._sites.keys())
    
    def validate_price(self, price: float) -> bool:
        """Valida se un prezzo è nel range accettabile."""
        return self._settings.min_price <= price <= self._settings.max_price
    
    def get_data_path(self, filename: str = None) -> Path:
        """Restituisce il path completo per i file di dati."""
        data_dir = Path(self._settings.data_directory)
        data_dir.mkdir(exist_ok=True)
        
        if filename:
            return data_dir / filename
        return data_dir
    
    def get_log_path(self, filename: str = None) -> Path:
        """Restituisce il path completo per i file di log."""
        log_dir = Path(self._settings.log_directory)
        log_dir.mkdir(exist_ok=True)
        
        if filename:
            return log_dir / filename
        return log_dir
    
    def reload_config(self) -> None:
        """Ricarica la configurazione dal file."""
        logger.info("Ricaricamento configurazione...")
        self.load_config()
    
    def __repr__(self) -> str:
        return (f"ConfigManager(sites={len(self._sites)}, "
                f"product='{self._product.name if self._product else None}')")


# Istanza globale del config manager
config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: str = "config.json") -> ConfigManager:
    """
    Factory function per ottenere l'istanza del ConfigManager.
    Utilizza il pattern Singleton per evitare ricaricamenti multipli.
    """
    global config_manager
    
    if config_manager is None:
        config_manager = ConfigManager(config_path)
    
    return config_manager


def reload_config(config_path: str = "config.json") -> ConfigManager:
    """Forza il ricaricamento della configurazione."""
    global config_manager
    config_manager = ConfigManager(config_path)
    return config_manager


# Esempi di uso:
if __name__ == "__main__":
    # Test del config manager
    try:
        config = get_config_manager()
        
        print(f"Prodotto: {config.product.name}")
        print(f"Siti abilitati: {config.get_enabled_sites()}")
        print(f"Timeout: {config.settings.timeout}s")
        print(f"Range prezzi: €{config.settings.min_price}-{config.settings.max_price}")
        
        # Test validazione prezzo
        test_prices = [150.0, 500.0, 3000.0]
        for price in test_prices:
            valid = config.validate_price(price)
            print(f"Prezzo €{price}: {'✅ Valido' if valid else '❌ Non valido'}")
            
    except Exception as e:
        print(f"Errore: {e}")