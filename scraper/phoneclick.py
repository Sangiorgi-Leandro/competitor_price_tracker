import aiohttp
from bs4 import BeautifulSoup
import re


async def scrape_phoneclick():
    """
    Scraping asincrono per Phoneclick.it
    """
    url = "https://www.phoneclick.it/samsung/galaxy-s23/samsung-galaxy-s23-5g-256gb-8gb-ram-dual-sim-black-europa?utm_campaign=feed-trovaprezzi&utm_medium=cpc&utm_source=trovaprezzi.it"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"Status code: {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Estrai il titolo
                title_element = soup.find('h1', class_='caratteretitolo')
                if not title_element:
                    raise Exception("Titolo non trovato")
                
                title = title_element.get_text().strip()
                
                # Estrai il prezzo
                # Il prezzo è dentro un tag <ins> che contiene il prezzo finale
                # Cerchiamo il pattern €XXX,XX che non sia il prezzo consigliato
                price_element = soup.find('ins')
                if not price_element:
                    raise Exception("Prezzo non trovato")
                
                # Ottieni tutto il testo e cerca tutti i prezzi
                full_text = price_element.get_text()
                
                # Trova tutti i prezzi nel formato €XXX,XX
                price_matches = re.findall(r'€\s*(\d+[.,]\d+)', full_text)
                
                if not price_matches:
                    raise Exception("Formato prezzo non riconosciuto")
                
                # Prendi l'ultimo prezzo trovato (di solito è il prezzo finale)
                final_price = price_matches[-1]
                price = f"€{final_price}"
                
                # Normalizza il prezzo
                price = normalize_price(price)
                
                return {
                    "site": "Phoneclick.it",
                    "title": title,
                    "price": price,
                    "url": url
                }
                
    except Exception as e:
        raise Exception(f"Errore scraping Phoneclick: {e}")


def normalize_price(price_text):
    """
    Normalizza il formato del prezzo
    """
    # Rimuovi spazi e caratteri non necessari
    price_text = price_text.strip().replace('&nbsp;', '')
    
    # Estrai numeri e virgole/punti
    price_match = re.search(r'€?\s*(\d+[.,]\d+)', price_text)
    if price_match:
        price_num = price_match.group(1)
        return f"€{price_num}"
    
    return price_text