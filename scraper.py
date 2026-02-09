import requests
from bs4 import BeautifulSoup

def minerar_precos_python(item):
    try:
        # Busca no DuckDuckGo (mais amigável que o Google para robôs)
        query = f"{item} preço brasil"
        url = f"https://html.duckduckgo.com/html/?q={query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        resultados = []
        # No DuckDuckGo HTML, os resultados ficam em classes 'result__body'
        for result in soup.find_all('div', class_='result__body')[:5]:
            title_tag = result.find('a', class_='result__a')
            snippet_tag = result.find('a', class_='result__snippet')
            
            if title_tag:
                nome = title_tag.text
                link = title_tag['href']
                
                # Tenta achar um preço (R$) no texto do snippet
                import re
                preco_match = re.search(r'R\$\s?(\d{1,3}(\.\d{3})*,\d{2})', snippet_tag.text if snippet_tag else "")
                preco = preco_match.group(0) if preco_match else "Ver no link"
                
                resultados.append({
                    "Produto": nome[:80],
                    "Preço": preco,
                    "Loja": "Busca Web",
                    "Link": link
                })
        
        return resultados
    except Exception as e:
        return [{"Erro": str(e)}]