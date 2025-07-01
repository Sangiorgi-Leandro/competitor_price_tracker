# Competitor Price Tracker

Un tracker di prezzi asincrono per monitorare il prezzo del Samsung Galaxy S23 256GB su diversi e-commerce italiani.

## 🎯 Funzionalità

- **Scraping asincrono** su 3 siti e-commerce in parallelo
- **Salvataggio automatico** dei prezzi in JSON e CSV
- **Storico prezzi** con timestamp per analisi temporali
- **Gestione errori** robusta per connessioni instabili
- **User-Agent realistico** per evitare blocchi

## 🏪 Siti Monitorati

- **Amazon.it** - Samsung Galaxy S23 256GB
- **Phoneclick.it** - Samsung Galaxy S23 5G 256GB 8GB Ram
- **Teknozone.it** - Samsung Galaxy S23 5G 256GB 8GB Ram

## 📁 Struttura Progetto

```
competitor_price_tracker/
│
├── main.py                 # Script principale
├── scraper/
│   ├── amazon.py           # Scraper Amazon
│   ├── phoneclick.py       # Scraper Phoneclick
│   └── teknozone.py        # Scraper Teknozone
│
├── data/
│   ├── latest_prices.json  # Ultimi prezzi rilevati
│   └── price_history.csv   # Storico completo prezzi
│
├── requirements.txt        # Dipendenze Python
└── README.md              # Questa documentazione
```

## 🚀 Installazione e Uso

### 1. Clona/Scarica il progetto
```bash
cd competitor_price_tracker
```

### 2. Installa le dipendenze
```bash
pip install -r requirements.txt  
```

### 3. Esegui il tracker
```bash
python main.py
```

## 📊 Output

Il programma produrrá:

### Console Output
```
🚀 Avvio Competitor Price Tracker per Samsung Galaxy S23 256GB
------------------------------------------------------------
✅ Amazon.it: SAMSUNG Galaxy S23 256GB - €482,00
✅ Phoneclick.it: Samsung Galaxy S23 5G 256GB 8GB Ram Dual Sim Black Europa - €485,00
✅ Teknozone.it: Samsung Galaxy S23 5G 256GB 8GB Ram Dual Sim Black Europa - €486,00
------------------------------------------------------------
💾 Dati salvati in data/latest_prices.json e data/price_history.csv
📊 Raccolti 3 prezzi su 3 siti
```

### File Generati

**data/latest_prices.json**
```json
{
  "timestamp": "2025-01-15T14:30:45.123456",
  "product": "Samsung Galaxy S23 256GB",
  "prices": [
    {
      "site": "Amazon.it",
      "title": "SAMSUNG Galaxy S23 256GB",
      "price": "€482,00",
      "url": "https://www.amazon.it/dp/..."
    }
  ]
}
```

**data/price_history.csv**
```csv
timestamp,site,title,price,url
2025-01-15 14:30:45,Amazon.it,SAMSUNG Galaxy S23 256GB,€482.00,https://www.amazon.it/dp/...
```

## 🔧 Dipendenze

- **aiohttp** - Client HTTP asincrono per web scraping
- **beautifulsoup4** - Parser HTML per estrazione dati
- **lxml** - Parser XML/HTML veloce (backend per BeautifulSoup)

## ⚠️ Note Tecniche

- **Timeout**: 10 secondi per ogni richiesta HTTP
- **User-Agent**: Simula un browser Chrome reale per evitare blocchi
- **Gestione errori**: Continua l'esecuzione anche se un sito fallisce
- **Encoding**: UTF-8 per supportare caratteri italiani nei file

## 🐛 Troubleshooting

**Errore "Titolo non trovato"**
- Il sito potrebbe aver cambiato la struttura HTML
- Verifica che l'URL sia ancora valido

**Errore "Prezzo non trovato"**
- Il selettore CSS/HTML potrebbe essere cambiato
- Controlla il prezzo manualmente sul sito

**Errore di connessione**
- Verifica la connessione internet
- Alcuni siti potrebbero bloccare richieste automatiche

## 📝 Personalizzazione

Per monitorare altri prodotti:
1. Modifica gli URL nei file `scraper/*.py`
2. Aggiorna i selettori HTML per titolo e prezzo
3. Cambia il nome del prodotto in `main.py`

## 📄 Licenza

Progetto per uso educativo e personale. Rispetta i Terms of Service dei siti web.