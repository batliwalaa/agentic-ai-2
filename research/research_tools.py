###==============================
### Import libraries
###==============================

import os
import xml.etree.ElementTree as ET

import requests
from tavily import TavilyClient
from dotenv import load_dotenv
import wikipedia

load_dotenv()

session = requests.Session()
session.headers.update({
    "User-Agent": "LF-ADP-Agent/1.0 (mailto:your.email@example.com)"
})

def arxiv_search(query: str, max_results: int = 5) -> list[dict]:
    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results
    }

    try:
      response = session.get(base_url, params=params, timeout=30)
      response.raise_for_status()
    except requests.exceptions.RequestException as e:
      return [{"error": str(e)}]
    
    try:
      root = ET.fromstring(response.content)
      ns = {'atom': 'http://www.w3.org/2005/Atom'}
    
      results = []
      for entry in root.findall('atom:entry', ns):
          title = entry.find('atom:title', ns).text
          authors = [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)]
          published = entry.find('atom:published', ns).text[:10]
          url_abstract = entry.find('atom:id', ns).text
          summary = entry.find('atom:summary', ns).text.strip()

          link_pdf = None
          for link in entry.findall('atom:link', ns):
              if link.attrib.get('title') == 'pdf':
                  link_pdf = link.attrib['href']
                  break
          results.append({
              "title": title,
              "authors": authors,
              "published": published,
              "url_abstract": url_abstract,
              "url_pdf": link_pdf,
              "summary": summary
          })

      return results
    except Exception as e:
      return [{"error": f"XML Parse Error: {str(e)}"}]
    
arxiv_tool_def = {
   "type": "function",
   "function": {
      "name": "arxiv_search",
      "description": "Search for research papers on arXiv.org given a search query. Returns a list of relevant papers with title, authors, published date, abstract URL, PDF URL, and summary.",
      "parameters": {
         "type": "object",
         "properties": {
            "query": {
               "type": "string",
               "description": "The search query string to find relevant research papers."
            },
            "max_results": {
               "type": "integer",
               "description": "The maximum number of results to return (default is 5).",
                "default": 5
            }
         },
         "required": ["query"]
      } 
   }
}


def tavily_search(query: str, max_results: int = 5, include_images:bool = False) -> list[dict]:
    """
    Perform a search using the Tavily API.

    Args:
        query (str): The search query.
        max_results (int): Number of results to return (default 5).
        include_images (bool): Whether to include image results.

    Returns:
        list[dict]: A list of dictionaries with keys like 'title', 'content', and 'url'.
    """
    params = {}
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables.")
    params['api_key'] = api_key

    api_base_url = os.getenv("DLAI_TAVILY_BASE_URL")
    if api_base_url:
        params['api_base_url'] = api_base_url

    client = TavilyClient(api_key=api_key, api_base_url=api_base_url)

    try:
        response = client.search(query=query, max_results=max_results, include_images=include_images)
        formatted_results = []
        for item in response.get("results", []):
            formatted_results.append({
                "title": item.get("title"),
                "content": item.get("content"),
                "url": item.get("url")
            })

        if include_images:
            for img in response.get("images", []):
                formatted_results.append({"image_url": img})
        return formatted_results
    
    except Exception as e:
        return [{"error": str(e)}]
    
tavily_tool_def = {
   "type": "function",
    "function": {
        "name": "tavily_search",
        "description": "Search for documents using the Tavily API given a search query. Returns a list of relevant documents with title, content snippet, source, and URL.",
        "parameters": {
          "type": "object",
          "properties": {
              "query": {
                "type": "string",
                "description": "The search query string to find relevant documents."
              },
              "max_results": {
                "type": "integer",
                "description": "The maximum number of results to return (default is 5).",
                "default": 5
              },
              "include_images": {
                  "type": "boolean",
                  "description": "Whether to include image results.",
                  "default": False
              }
          },
          "required": ["query"]
        } 
  }
}


def wikipedia_search(query: str, sentences: int = 5) -> list[dict]:
    """
    Searches Wikipedia for a summary of the given query.

    Args:
        query (str): Search query for Wikipedia.
        sentences (int): Number of sentences to include in the summary.

    Returns:
        list[dict]: A list with a single dictionary containing title, summary, and URL.
    """

    try:
        page_title = wikipedia.search(query)[0]
        page = wikipedia.page(page_title)
        summary = wikipedia.summary(page_title, sentences = sentences)

        return [{
            "title": page.title,
            "summary": summary,
            "url": page.url
        }]
    except Exception as e:
        return [{ "error": str(e) }]
   
wikipedia_tool_def = {
    "type": "function",
    "function": {
        "name": "wikipedia_search",
        "description": "Searches for a Wikipedia article summary by query string.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords for wikipedia article"
                },
                "sentences": {
                    "type": "integer",
                    "description": "Number of sentences in the summary.",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}


def parse_input(report):
    """
    Normalizes report input into a single string.

    Allowed forms:
    - String
    - List of strings
    - List of dicts that contain 'content'

    Anything else raises a ValueError.
    """

    # Case 1: plain text
    if isinstance(report, str):
        return report.strip()

    # Case 2: list of strings OR list of message dicts
    if isinstance(report, list):
        parts = []

        for item in report:
            # Case: dict with content
            if isinstance(item, dict):
                if "content" not in item:
                    raise ValueError("Dict items must contain a 'content' field.")
                parts.append(str(item["content"]))

            # Case: string entry
            elif isinstance(item, str):
                parts.append(item)

            # Not allowed
            else:
                raise ValueError(
                    f"Invalid item in list: {type(item).__name__}. "
                    "Only strings or dicts with 'content' are allowed."
                )

        return "\n".join(parts).strip()

    # Anything else is not allowed
    raise ValueError(
        f"Invalid report type: {type(report).__name__}. "
        "Expected string or list."
    )

tool_mapping = {
    "tavily_search": tavily_search,
    "arxiv_search": arxiv_search,
    "wikipedia_search": wikipedia_search
}
