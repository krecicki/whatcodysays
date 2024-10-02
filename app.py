import time
from flask import Flask, render_template, request, jsonify, abort, redirect, url_for
from googlesearch import search as google_search
from duckduckgo_search import DDGS
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from youtube_search import YoutubeSearch
from dotenv import load_dotenv
from openai import OpenAI
import os
import lancedb
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import pyarrow as pa
from slugify import slugify
from datetime import datetime
import random
from graph import enhance_search_results

app = Flask(__name__)

# Load environment variables
load_dotenv()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

# Set up LanceDB
db_path = os.path.join(os.getcwd(), "lancedb")
db = lancedb.connect(db_path)

if "search_results" not in db.table_names():
    schema = pa.schema([
        ('query', pa.string()),
        ('url', pa.string()),
        ('title', pa.string()),
        ('description', pa.string()),
        ('content_preview', pa.string()),
        ('body', pa.string()),
        ('source', pa.string()),
        ('gpt_relevance', pa.string()),
        ('slug', pa.string()),
        ('is_blog_post', pa.bool_()),
        ('publish_date', pa.string())
    ])
    table = db.create_table("search_results", schema=schema)
else:
    table = db.open_table("search_results")

# Load existing data from LanceDB into a pandas DataFrame
search_results_df = table.to_pandas()

print(f"Loaded {len(search_results_df)} rows from LanceDB")

def get_google_results(query, num_results=10):
    start_time = time.time()
    results = []
    try:
        for result in google_search(query, num_results=num_results):
            results.append({'url': result, 'source': 'Google'})
    except Exception as e:
        print(f"An error occurred during Google search: {str(e)}")
    print(f"Google search took {time.time() - start_time:.2f} seconds")
    return results

def get_duckduckgo_results(query, num_results=10):
    start_time = time.time()
    try:
        with DDGS() as ddgs:
            results = [{'url': r['href'], 'title': r['title'], 'body': r['body'], 'source': 'DuckDuckGo'} 
                       for r in ddgs.text(query, max_results=num_results)]
        print(f"DuckDuckGo search took {time.time() - start_time:.2f} seconds")
        return results
    except Exception as e:
        print(f"An error occurred during DuckDuckGo search: {str(e)}")
        print(f"DuckDuckGo search took {time.time() - start_time:.2f} seconds")
        return []

def get_page_info(result):
    start_time = time.time()
    url = result['url']
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('title').text if soup.find('title') else "No title found"
        description = soup.find('meta', attrs={'name': 'description'})
        description = description['content'] if description else "No description available"
        content_preview = ' '.join(soup.stripped_strings)[:1000]
        body = soup.body.get_text(strip=True) if soup.body else "No body content found"
        print(f"Fetching and parsing {url} took {time.time() - start_time:.2f} seconds")
        return {
            'url': url,
            'title': title,
            'description': description[:200] + '...' if len(description) > 200 else description,
            'content_preview': content_preview + '...',
            'body': body,
            'source': result['source']
        }
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        print(f"Attempted fetch of {url} took {time.time() - start_time:.2f} seconds")
        return None

def get_gpt_relevance(query, results):
    start_time = time.time()
    try:
        result_summaries = "\n".join([f"Title: {r['title']}\nDescription: {r['description']}\nURL: {r['url']}\nBody: {r['body'][:1000]}..." for r in results[:10]])
        prompt = f"""Given the search query '{query}', analyze these search results:
{result_summaries}
1. Identify the most relevant result and explain why it's the best match, give the source url.
2. If you can't provide a direct answer, explain what information is missing and suggest how the user might find it.
3. Suggest 2-3 follow-up queries that might help explore this topic further.
Format your response like this:
Most Relevant Result: [Title of most relevant result]
Direct Answer: [Concise answer to the likely question, or explanation of what's missing]
Next Steps: [Suggestion for what the user should do next with a url]
Follow-up Queries: [List of 2-3 suggested follow-up queries]"""
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes search results and provides quick, relevant answers."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        print(f"GPT analysis took {time.time() - start_time:.2f} seconds")
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in GPT analysis: {str(e)}")
        print(f"GPT analysis attempt took {time.time() - start_time:.2f} seconds")
        return f"Error in GPT analysis: {str(e)}"

def store_search_results(query, results, gpt_relevance):
    global search_results_df
    data = []
    current_time = datetime.now().isoformat()
    for result in results:
        data.append({
            "query": query,
            "url": result.get('url', ''),
            "title": result.get('title', ''),
            "description": result.get('description', ''),
            "content_preview": result.get('content_preview', ''),
            "body": result.get('body', ''),
            "source": result.get('source', ''),
            "gpt_relevance": gpt_relevance,
            "slug": slugify(result.get('title', '')),
            "is_blog_post": False,
            "publish_date": current_time
        })
    new_df = pd.DataFrame(data)
    
    try:
        # Store in LanceDB
        table.add(data)
        
        # Update the in-memory DataFrame
        search_results_df = pd.concat([search_results_df, new_df], ignore_index=True)
        
        print(f"Added {len(new_df)} new rows to LanceDB. Total rows: {len(search_results_df)}")
    except Exception as e:
        print(f"Error adding data to LanceDB: {str(e)}")
        print(f"Data sample: {data[0] if data else 'No data'}")

def similarity_search(query, top_k=10, similarity_threshold=0.9):
    global search_results_df
    
    if search_results_df.empty:
        return [], None
    
    # Normalize queries
    query = query.lower().strip()
    search_results_df['normalized_query'] = search_results_df['query'].str.lower().str.strip()
    
    # Check for exact matches first
    exact_matches = search_results_df[search_results_df['normalized_query'] == query]
    if not exact_matches.empty:
        results = exact_matches.head(top_k)
        gpt_relevance = results.iloc[0]['gpt_relevance']
        return results.drop(['normalized_query', 'gpt_relevance'], axis=1).to_dict('records'), gpt_relevance
    
    # If no exact match, use TF-IDF and cosine similarity for near-identical matches
    vectorizer = TfidfVectorizer()
    stored_vectors = vectorizer.fit_transform(search_results_df['normalized_query'])
    query_vector = vectorizer.transform([query])
    
    similarities = cosine_similarity(query_vector, stored_vectors)[0]
    
    search_results_df['similarity'] = similarities
    
    # Filter results based on the similarity threshold
    similar_results = search_results_df[search_results_df['similarity'] >= similarity_threshold]
    
    if not similar_results.empty:
        # Sort by similarity and get top_k results
        similar_results = similar_results.sort_values('similarity', ascending=False).head(top_k)
        
        gpt_relevance = similar_results.iloc[0]['gpt_relevance']
        
        # Prepare results
        results_list = similar_results.drop(['similarity', 'gpt_relevance', 'normalized_query'], axis=1).to_dict('records')
        
        # Clean up temporary columns
        search_results_df = search_results_df.drop(['similarity', 'normalized_query'], axis=1)
        
        return results_list, gpt_relevance
    
    # If no similar results found, return empty list and None
    search_results_df = search_results_df.drop(['normalized_query'], axis=1)
    return [], None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_time = time.time()
        query = request.form.get('query')
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        try:
            # First, check for similar existing results
            similar_results, cached_gpt_relevance = similarity_search(query)
            if similar_results:
                print(f"Found similar results for query: {query}")
                return jsonify({'results': similar_results, 'gpt_relevance': cached_gpt_relevance, 'from_cache': True})
            
            # If no similar results, perform a new search
            with ThreadPoolExecutor(max_workers=20) as executor:
                future_google = executor.submit(get_google_results, query, 10)
                future_ddg = executor.submit(get_duckduckgo_results, query, 10)
                
                google_results = future_google.result()
                ddg_results = future_ddg.result()

                all_results = google_results + ddg_results

                future_to_result = {executor.submit(get_page_info, result): result for result in all_results}
                results = []
                for future in as_completed(future_to_result):
                    result = future.result()
                    if result:
                        results.append(result)

                # Add DuckDuckGo results that weren't fetched
                for ddg_result in ddg_results:
                    if not any(r['url'] == ddg_result['url'] for r in results):
                        results.append({
                            'url': ddg_result['url'],
                            'title': ddg_result['title'],
                            'description': ddg_result['body'],
                            'content_preview': ddg_result['body'][:500] + '...',
                            'source': 'DuckDuckGo'
                        })

                # Get GPT relevance explanation
                gpt_relevance = executor.submit(get_gpt_relevance, query, results).result()

                # Store the new results
                store_search_results(query, results, gpt_relevance)

                # Enhance and rank the results
                enhanced_results = enhance_search_results(results)

                print(f"Total request processing time: {time.time() - start_time:.2f} seconds")
                return jsonify({'results': enhanced_results, 'gpt_relevance': gpt_relevance, 'from_cache': False, 'ranking_method': 'graph-based PageRank'})
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            print(f"Total request processing time (with error): {time.time() - start_time:.2f} seconds")
            return jsonify({'error': str(e)}), 500
    
    return render_template('index.html')

@app.route('/blog')
def blog():
    global search_results_df
    
    # Convert publish_date to datetime objects
    search_results_df['publish_date'] = pd.to_datetime(search_results_df['publish_date'])
    
    # Sort by publish_date in descending order and get unique entries
    posts = search_results_df.sort_values('publish_date', ascending=False).drop_duplicates(subset=['query']).to_dict('records')
    
    # Ensure all required fields are present and format dates
    for post in posts:
        post['query'] = post.get('query', 'Untitled Search')
        post['gpt_relevance'] = post.get('gpt_relevance', 'No AI-generated insights available.')
        post['slug'] = post.get('slug', 'default-slug')
        post['publish_date'] = post['publish_date'].strftime('%Y-%m-%d')
    
    return render_template('blog.html', posts=posts)

@app.route('/blog/<slug>')
def blog_post(slug):
    global search_results_df
    
    post = search_results_df[search_results_df['slug'] == slug].iloc[0].to_dict()
    query = post['query']
    all_results = search_results_df[search_results_df['query'] == query].to_dict('records')
    
    # Get YouTube results
    yt_results = YoutubeSearch(query, max_results=4).to_dict()
    
    # Get the GPT relevance
    gpt_relevance = post['gpt_relevance']
    print(gpt_relevance)
    
    return render_template('article.html', post=post, results=all_results, youtube_results=yt_results, gpt_relevance=gpt_relevance, result_count=len(all_results))

@app.route('/youtube_search', methods=['POST'])
def youtube_search():
    start_time = time.time()
    query = request.form['query']
    
    # Get YouTube results
    yt_results = YoutubeSearch(query, max_results=10).to_dict()
    
    print(f"YouTube search route took {time.time() - start_time:.2f} seconds")
    return jsonify({'youtube_results': yt_results})

if __name__ == '__main__':
    app.run(debug=True)