import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from typing import List, Dict, Optional


class PriceAlertSystem:
    """
    Sistema di alert per monitoraggio cali di prezzo
    """
    
    def __init__(self, config_file: str = "config/alert_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.last_prices = self.load_last_prices()
    
    def load_config(self) -> Dict:
        """Carica la configurazione degli alert"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Configurazione di default
            default_config = {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "sender_email": "",
                    "sender_password": "",
                    "recipient_email": ""
                },
                "thresholds": {
                    "percentage_drop": 5.0,  # Alert se prezzo scende del 5%
                    "absolute_drop": 20.0    # Alert se prezzo scende di €20
                },
                "target_prices": {
                    "Amazon.it": 450.0,
                    "Phoneclick.it": 460.0,
                    "Teknozone.it": 470.0
                }
            }
            
            # Crea cartella config se non esiste
            os.makedirs('config', exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            print(f"⚙️ Creato file di configurazione: {self.config_file}")
            return default_config
    
    def load_last_prices(self) -> Dict:
        """Carica gli ultimi prezzi salvati"""
        try:
            with open('data/latest_prices.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Converte la lista in dizionario per accesso più facile
                return {item['site']: self.parse_price(item['price']) for item in data.get('prices', [])}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def parse_price(self, price_str: str) -> float:
        """Converte una stringa prezzo in float"""
        import re
        # Estrai solo numeri e virgola/punto
        numbers = re.findall(r'\d+[.,]?\d*', price_str.replace('.', '').replace(',', '.'))
        if numbers:
            return float(numbers[0])
        return 0.0
    
    def check_price_alerts(self, current_prices: List[Dict]) -> List[Dict]:
        """
        Controlla se ci sono alert da inviare
        Ritorna lista di alert da processare
        """
        alerts = []
        
        for price_data in current_prices:
            site = price_data['site']
            current_price = self.parse_price(price_data['price'])
            last_price = self.last_prices.get(site, 0)
            target_price = self.config['target_prices'].get(site, 0)
            
            # Skip se non abbiamo dati precedenti o il prezzo è 0
            if last_price == 0 or current_price == 0:
                continue
            
            alert_reasons = []
            
            # 1. Controllo calo percentuale
            if last_price > current_price:
                percentage_drop = ((last_price - current_price) / last_price) * 100
                if percentage_drop >= self.config['thresholds']['percentage_drop']:
                    alert_reasons.append(f"Calo del {percentage_drop:.1f}%")
            
            # 2. Controllo calo assoluto
            if last_price > current_price:
                absolute_drop = last_price - current_price
                if absolute_drop >= self.config['thresholds']['absolute_drop']:
                    alert_reasons.append(f"Calo di €{absolute_drop:.2f}")
            
            # 3. Controllo prezzo target raggiunto
            if target_price > 0 and current_price <= target_price:
                alert_reasons.append(f"Prezzo target €{target_price:.2f} raggiunto!")
            
            # Se ci sono motivi per l'alert, crealo
            if alert_reasons:
                alerts.append({
                    'site': site,
                    'title': price_data['title'],
                    'current_price': current_price,
                    'last_price': last_price,
                    'price_formatted': price_data['price'],
                    'url': price_data['url'],
                    'reasons': alert_reasons,
                    'timestamp': datetime.now().isoformat()
                })
        
        return alerts
    
    def send_email_alert(self, alerts: List[Dict]) -> bool:
        """Invia alert via email"""
        if not self.config['email']['enabled'] or not alerts:
            return False
        
        try:
            # Configura email
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['sender_email']
            msg['To'] = self.config['email']['recipient_email']
            msg['Subject'] = f"🚨 Price Alert - Samsung Galaxy S23 256GB ({len(alerts)} alert)"
            
            # Crea corpo email HTML
            html_body = self.create_email_html(alerts)
            msg.attach(MIMEText(html_body, 'html'))
            
            # Invia email
            server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['sender_email'], self.config['email']['sender_password'])
            text = msg.as_string()
            server.sendmail(self.config['email']['sender_email'], self.config['email']['recipient_email'], text)
            server.quit()
            
            print(f"📧 Email alert inviata con successo ({len(alerts)} alert)")
            return True
            
        except Exception as e:
            print(f"❌ Errore invio email: {e}")
            return False
    
    def create_email_html(self, alerts: List[Dict]) -> str:
        """Crea HTML per email di alert"""
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .alert { border: 2px solid #ff4444; border-radius: 5px; padding: 15px; margin: 10px 0; background-color: #fff5f5; }
                .price-drop { color: #ff4444; font-weight: bold; }
                .price-current { color: #00aa00; font-size: 1.2em; font-weight: bold; }
                .site-name { color: #0066cc; font-weight: bold; }
                a { color: #0066cc; }
            </style>
        </head>
        <body>
            <h2>🚨 Price Alert - Samsung Galaxy S23 256GB</h2>
            <p><strong>Data:</strong> {timestamp}</p>
        """.format(timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        
        for alert in alerts:
            reasons_text = " • ".join(alert['reasons'])
            html += f"""
            <div class="alert">
                <h3 class="site-name">{alert['site']}</h3>
                <p><strong>Prodotto:</strong> {alert['title']}</p>
                <p><strong>Prezzo attuale:</strong> <span class="price-current">{alert['price_formatted']}</span></p>
                <p><strong>Prezzo precedente:</strong> €{alert['last_price']:.2f}</p>
                <p class="price-drop"><strong>Alert:</strong> {reasons_text}</p>
                <p><a href="{alert['url']}" target="_blank">🛒 Vai al prodotto</a></p>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        return html
    
    def save_alert_log(self, alerts: List[Dict]):
        """Salva log degli alert inviati"""
        if not alerts:
            return
        
        os.makedirs('data', exist_ok=True)
        log_file = 'data/alert_log.json'
        
        # Carica log esistente
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            log_data = []
        
        # Aggiungi nuovi alert
        log_data.extend(alerts)
        
        # Salva log aggiornato
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📝 Alert salvati nel log ({len(alerts)} nuovi)")
    
    def process_alerts(self, current_prices: List[Dict]) -> List[Dict]:
        """
        Processa tutti gli alert per i prezzi correnti
        """
        alerts = self.check_price_alerts(current_prices)
        
        if alerts:
            print(f"\n🚨 ALERT RILEVATI: {len(alerts)} cali di prezzo!")
            print("-" * 50)
            
            for alert in alerts:
                reasons = " • ".join(alert['reasons'])
                print(f"🔔 {alert['site']}")
                print(f"   Prezzo: €{alert['last_price']:.2f} → {alert['price_formatted']}")
                print(f"   Motivo: {reasons}")
                print(f"   URL: {alert['url'][:50]}...")
                print()
            
            # Salva nel log
            self.save_alert_log(alerts)
            
            # Invia email se configurata
            if self.config['email']['enabled']:
                self.send_email_alert(alerts)
            else:
                print("📧 Email disabilitata. Configura email in config/alert_config.json per ricevere notifiche.")
        
        else:
            print("✅ Nessun alert rilevato. Prezzi stabili o in aumento.")
        
        return alerts