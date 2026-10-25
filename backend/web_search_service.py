import os
import urllib.parse
import urllib.request
import json
from typing import List, Dict, Any
from ddgs import DDGS
from google import genai
from google.genai import types

def get_gemini_client():
    from qa_service import client
    return client

def search_ddg_html(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Query DuckDuckGo using HTML backend for maximum reliability without timeouts."""
    results = []
    try:
        ddgs_client = DDGS(timeout=8)
        raw_results = list(ddgs_client.text(query, backend="html", max_results=max_results))
        for r in raw_results:
            url = r.get("href", "")
            domain = ""
            if url:
                try:
                    domain = urllib.parse.urlparse(url).netloc
                except Exception:
                    domain = ""
            results.append({
                "title": r.get("title", "Web Source"),
                "url": url,
                "snippet": r.get("body", ""),
                "domain": domain
            })
    except Exception as e:
        print(f"DDGS html search error: {e}")
    return results

def search_fallback_apis(query: str) -> List[Dict[str, str]]:
    """Instant Answer and OpenSearch fallback for real web citations."""
    results = []
    # 1. DuckDuckGo Instant Answer API
    try:
        url = 'https://api.duckduckgo.com/?q=' + urllib.parse.quote(query) + '&format=json&no_html=1&skip_disambig=1'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=4) as resp:
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
        print(f"DDG API error: {e}")

    # 2. Wikipedia OpenSearch API fallback
    if len(results) < 2:
        try:
            wiki_url = 'https://en.wikipedia.org/w/api.php?action=opensearch&search=' + urllib.parse.quote(query) + '&limit=3&namespace=0&format=json'
            wiki_req = urllib.request.Request(wiki_url, headers={'User-Agent': 'VISTAAR-Intelligence/1.0'})
            with urllib.request.urlopen(wiki_req, timeout=4) as wresp:
                wdata = json.loads(wresp.read().decode('utf-8'))
                if len(wdata) >= 4:
                    titles = wdata[1]
                    snippets = wdata[2]
                    urls = wdata[3]
                    for t, s, u in zip(titles, snippets, urls):
                        if u not in [r['url'] for r in results]:
                            results.append({
                                'title': t,
                                'url': u,
                                'snippet': s if s else f"Summary and details on {t}.",
                                'domain': 'en.wikipedia.org'
                            })
        except Exception as e:
            print(f"Wikipedia API error: {e}")

    return results

def search_web_sources(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    results = search_ddg_html(query, max_results=max_results)
    if not results:
        results = search_fallback_apis(query)
    return results[:max_results]

def search_web_and_synthesize(query: str) -> Dict[str, Any]:
    sources = search_web_sources(query, max_results=4)
    if not sources:
        return {
            "query": query,
            "synthesized_answer": "No external web results could be found for this query.",
            "sources": [],
            "status": "empty"
        }

    context_lines = []
    for i, s in enumerate(sources, 1):
        context_lines.append(f"[{i}] {s['title']} ({s['domain']}):\n{s['snippet']}\nURL: {s['url']}")
    web_context = "\n\n".join(context_lines)

    system_instruction = (
        "You are an external web search synthesizer for VISTAAR. "
        "Summarize the answer to the user's question based strictly on the provided external web search results. "
        "Be concise, informative, and objective. "
        "Keep in mind this is EXTERNAL information and not from the user's private documents."
    )

    prompt = f"Web Search Results:\n{web_context}\n\nQuestion: {query}\n\nSynthesized Web Answer:"

    client = get_gemini_client()
    synthesized_answer = None
    for model_name in ["gemini-3-flash-preview", "gemini-3.5-flash"]:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                )
            )
            if resp.text:
                synthesized_answer = resp.text.strip()
                break
        except Exception as e:
            print(f"Gemini web synthesis error ({model_name}): {e}")

    if not synthesized_answer:
        snippets_summary = " ".join([s["snippet"] for s in sources[:2]])
        synthesized_answer = f"According to web search results: {snippets_summary}"

    return {
        "query": query,
        "synthesized_answer": synthesized_answer,
        "sources": sources,
        "status": "success"
    }
