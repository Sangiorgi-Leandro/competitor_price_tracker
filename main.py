import asyncio
import json
import csv
from datetime import datetime
import os
import argparse

from scraper.amazon import scrape_amazon
from scraper.phoneclick import scrape_phoneclick
from scraper.teknozone import scrape_teknozone
from alert_system import PriceAlertSystem  # Assicurati che il file si chiami alert_system.py


async def main():
    """
    Script principale per monitorare i prezzi del Samsung Galaxy S23 256GB
    """
    parser = argparse.ArgumentParser(description='Competitor Price Tracker con sistema di alert')
    parser.add_argument('--no-alerts', action='store_true', help='Disabilita controllo alert')
    parser.add_argument('--schedule', type=int, help='Esegui ogni N minuti (modalità daemon)')
    args = parser.parse_args()

    print("🚀 Avvio Competitor Price Tracker per Samsung Galaxy S23 256GB")
    print("------------------------------------------------------------")

    alert_system = None if args.no_alerts else PriceAlertSystem()

    if args.schedule:
        print(f"⏰ Modalità scheduler attiva: controllo ogni {args.schedule} minuti")
        while True:
            await run_price_check(alert_system)
            print(f"😴 Prossimo controllo tra {args.schedule} minuti...")
            await asyncio.sleep(args.schedule * 60)
    else:
        await run_price_check(alert_system)


async def run_price_check(alert_system=None):
    """
    Esegue un singolo controllo prezzi
    """
    tasks = [
        scrape_amazon(),
        scrape_phoneclick(),
        scrape_teknozone()
    ]

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        site_names = ["Amazon.it", "Phoneclick.it", "Teknozone.it"]
        valid_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Errore durante lo scraping di {site_names[i]}: {result}")
            else:
                valid_results.append(result)
                print(f"✅ {result['site']}: {result['title'][:50]} - {result['price']}")

        if not valid_results:
            print("❌ Nessun dato raccolto con successo!")
            return

        # Sistema di allerta
        if alert_system:
            alert_system.process_alerts(valid_results)

        # Salvataggio dati
        save_latest_prices(valid_results)
        save_price_history(valid_results)

        print("------------------------------------------------------------")
        print("💾 Dati salvati in data/latest_prices.json e data/price_history.csv")
        print(f"📊 Raccolti {len(valid_results)} prezzi su 3 siti")
        print(f"🕐 {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}")

    except Exception as e:
        print(f"❌ Errore generale durante l'esecuzione: {e}")


def save_latest_prices(results):
    """Salva gli ultimi prezzi in formato JSON"""
    os.makedirs('data', exist_ok=True)
    data = {
        "timestamp": datetime.now().isoformat(),
        "product": "Samsung Galaxy S23 256GB",
        "prices": results
    }
    with open('data/latest_prices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_price_history(results):
    """Aggiunge una riga per ogni prezzo al file CSV storico"""
    os.makedirs('data', exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.exists('data/price_history.csv')

    with open('data/price_history.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'site', 'title', 'price', 'url'])
        if not file_exists:
            writer.writeheader()
        for result in results:
            writer.writerow({
                'timestamp': timestamp,
                'site': result['site'],
                'title': result['title'],
                'price': result['price'],
                'url': result['url']
            })


if __name__ == "__main__":
    asyncio.run(main())
