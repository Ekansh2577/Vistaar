import urllib.request
import urllib.parse
import json
import re

def search(query):
    # Try DuckDuckGo Instant Answer API
    url = 'https://api.duckduckgo.com/?q=' + urllib.parse.quote(query) + '&format=json&no_html=1&skip_disambig=1'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    results = []
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('AbstractText') and data.get('AbstractURL'):
                results.append({
                    'title': data.get('Heading', query),
                    'url': data.get('AbstractURL'),
                    'snippet': data.get('AbstractText'),
                    'domain': urllib.parse.urlparse(data.get('AbstractURL')).netloc
                })
            for topic in data.get('RelatedTopics', []):
                if isinstance(topic, dict) and topic.get('FirstURL') and topic.get('Text'):
                    results.append({
                        'title': topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else query,
                        'url': topic.get('FirstURL'),
                        'snippet': topic.get('Text'),
                        'domain': urllib.parse.urlparse(topic.get('FirstURL')).netloc
                    })
    except Exception as e:
        print('DuckDuckGo API error:', e)

    # Also try Wikipedia API for general knowledge
    if len(results) < 3:
        try:
            wiki_url = 'https://en.wikipedia.org/w/api.php?action=opensearch&search=' + urllib.parse.quote(query) + '&limit=4&namespace=0&format=json'
            wiki_req = urllib.request.Request(wiki_url, headers={'User-Agent': 'VISTAAR/1.0 (academic; research)'})
            with urllib.request.urlopen(wiki_req, timeout=5) as wresp:
                wdata = json.loads(wresp.read().decode('utf-8'))
                # wdata format: [query, [titles], [descriptions], [urls]]
                if len(wdata) >= 4:
                    titles = wdata[1]
                    snippets = wdata[2]
                    urls = wdata[3]
                    for t, s, u in zip(titles, snippets, urls):
                        if u not in [r['url'] for r in results]:
                            results.append({
                                'title': t,
                                'url': u,
                                'snippet': s if s else f"Information on {t} from Wikipedia.",
                                'domain': 'en.wikipedia.org'
                            })
        except Exception as e:
            print('Wikipedia API error:', e)

    return results

if __name__ == '__main__':
    res = search('fastapi python framework')
    print('Found results:', len(res))
    for r in res:
        print('-', r['title'], '-->', r['url'])
