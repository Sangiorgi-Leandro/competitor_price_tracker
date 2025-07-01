import aiohttp
from bs4 import BeautifulSoup
import re


async def scrape_teknozone():
    """
    Scraping asincrono per Teknozone.it
    """
    url = "https://www.teknozone.it/smartphone-samsung/galaxy-s23/samsung-galaxy-s23-5g-256gb-8gb-ram-dual-sim-black-europa?utm_campaign=feed-trovaprezzi&utm_medium=cpc&utm_source=trovaprezzi.it"
    
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
                title_element = soup.find('h1', class_='product-title')
                if not title_element:
                    raise Exception("Titolo non trovato")
                
                title = title_element.get_text().strip()
                
                # Estrai il prezzo
                # Il prezzo è dentro <p class="product-cost"><strong>€486,00</strong></p>
                price_element = soup.find('p', class_='product-cost')
                if price_element:
                    # Cerca il tag strong dentro product-cost
                    strong_element = price_element.find('strong')
                    if strong_element:
                        price_text = strong_element.get_text().strip()
                    else:
                        price_text = price_element.get_text().strip()
                else:
                    # Fallback: cerca direttamente un tag strong con €
                    strong_elements = soup.find_all('strong')
                    price_text = None
                    for strong in strong_elements:
                        text = strong.get_text().strip()
                        if '€' in text and re.search(r'\d+[.,]\d+', text):
                            price_text = text
                            break
                    
                    if not price_text:
                        raise Exception("Prezzo non trovato")
                
                # Verifica che contenga il simbolo €
                if '€' not in price_text:
                    raise Exception("Formato prezzo non valido")
                
                # Normalizza il prezzo
                price = normalize_price(price_text)
                
                return {
                    "site": "Teknozone.it",
                    "title": title,
                    "price": price,
                    "url": url
                }
                
    except Exception as e:
        raise Exception(f"Errore scraping Teknozone: {e}")


def normalize_price(price_text):
    """
    Normalizza il formato del prezzo
    """
    # Rimuovi spazi e caratteri non necessari
    price_text = price_text.strip()
    
    # Estrai numeri e virgole/punti con il simbolo €
    price_match = re.search(r'€\s*(\d+[.,]\d+)', price_text)
    if price_match:
        return f"€{price_match.group(1)}"
    
    # Se il formato è diverso, restituisci il testo originale
    return price_text