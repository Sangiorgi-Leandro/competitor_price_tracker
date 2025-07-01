import aiohttp
from bs4 import BeautifulSoup
import re


async def scrape_amazon():
    """
    Scraping asincrono per Amazon.it
    """
    url = "https://www.amazon.it/dp/B0C78GHQRJ/ref=asc_df_B0C78GHQRJ1750694400000/?tag=trovaprezzi-mp-ce-21&creative=23478&creativeASIN=B0C78GHQRJ&linkCode=df0&ascsubtag=7B2273223A226230633738676871726A222C2263223A372C2274223A22323530363239222C227472223A22227D"
    
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
                title_element = soup.find('span', {'id': 'productTitle'})
                if not title_element:
                    raise Exception("Titolo non trovato")
                
                title = title_element.get_text().strip()
                
                # Estrai il prezzo - prova prima con a-offscreen che è più affidabile
                price_element = soup.find('span', class_='a-offscreen')
                if price_element:
                    price_text = price_element.get_text().strip()
                else:
                    # Fallback: prova con a-price-whole e a-price-fraction
                    price_whole = soup.find('span', class_='a-price-whole')
                    if not price_whole:
                        raise Exception("Prezzo non trovato")
                    
                    decimal_element = soup.find('span', class_='a-price-fraction')
                    decimal = decimal_element.get_text().strip() if decimal_element else '00'
                    price_text = f"{price_whole.get_text().strip()},{decimal}€"
                
                # Normalizza il prezzo
                price = normalize_price(price_text)
                
                return {
                    "site": "Amazon.it",
                    "title": title,
                    "price": price,
                    "url": url
                }
                
    except Exception as e:
        raise Exception(f"Errore scraping Amazon: {e}")


def normalize_price(price_text):
    """
    Normalizza il formato del prezzo Amazon
    """
    # Rimuovi spazi e caratteri non necessari
    price_text = price_text.strip()
    
    # Se già contiene €, estrai solo i numeri e ricostruisci
    if '€' in price_text:
        # Estrai solo i numeri e la virgola/punto
        numbers = re.findall(r'\d+', price_text)
        if len(numbers) >= 2:
            # Prendi i primi due numeri (euro e centesimi)
            return f"€{numbers[0]},{numbers[1]}"
        elif len(numbers) == 1:
            return f"€{numbers[0]},00"
    
    # Se non c'è €, cerca il pattern numerico
    price_match = re.search(r'(\d+)[.,](\d+)', price_text)
    if price_match:
        euro = price_match.group(1)
        cents = price_match.group(2)
        return f"€{euro},{cents}"
    
    # Fallback: solo numeri interi
    price_match = re.search(r'(\d+)', price_text)
    if price_match:
        return f"€{price_match.group(1)},00"
    
    return price_text