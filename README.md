# Enhanced Web Search Engine with AI Integration

An intelligent search engine that combines results from multiple sources, enhances them with AI analysis, and provides a clean, modern interface for exploring search results.

## Features

- **Multi-Source Search**: Aggregates results from Google and DuckDuckGo for comprehensive coverage
- **AI-Powered Analysis**: Uses Groq's LLM API to analyze and summarize search results
- **Smart Caching**: Implements similarity-based caching using LanceDB to reduce redundant searches
- **Enhanced Ranking**: Uses a graph-based PageRank algorithm to improve result relevance
- **YouTube Integration**: Automatically fetches relevant YouTube content for searches
- **Blog Generation**: Automatically creates blog posts from search results and analysis
- **Responsive UI**: Modern, responsive interface built with Flask and Tailwind CSS

## Technical Stack

- **Backend**: Python, Flask
- **Database**: LanceDB
- **AI/ML**: 
  - Groq API for LLM analysis
  - TF-IDF vectorization for content similarity
  - NetworkX for graph-based ranking
- **Frontend**: HTML, Tailwind CSS, JavaScript
- **Search APIs**: Google Search, DuckDuckGo, YouTube

## Key Components

- **Search Aggregation**: Concurrent fetching from multiple sources using ThreadPoolExecutor
- **Content Analysis**: Web scraping with BeautifulSoup and content enrichment
- **Similarity Detection**: TF-IDF vectorization with cosine similarity
- **Graph-Based Ranking**: PageRank algorithm for result enhancement
- **Caching System**: LanceDB for efficient storage and retrieval

## Installation

1. Clone the repository
2. Install dependencies:
```bash
flask>=2.0.0
beautifulsoup4>=4.9.3
requests>=2.25.1
google>=3.0.0
duckduckgo-search>=2.8.0
youtube-search>=2.1.0
python-dotenv>=0.19.0
openai>=1.0.0
lancedb>=0.1.0
pandas>=1.3.0
scikit-learn>=0.24.2
pyarrow>=6.0.0
python-slugify>=5.0.2
networkx>=2.6.3
concurrent-futures>=3.1.0
```
3. Set up environment variables:
```bash
GROQ_API_KEY=your_api_key
```
4. Run the application:
```bash
python app.py
```

## Usage

The application provides several endpoints:

- `/`: Main search interface
- `/blog`: Auto-generated blog from search results
- `/blog/<slug>`: Individual blog posts with detailed analysis
- `/youtube_search`: YouTube results endpoint

## Architecture

The system follows a modular architecture:

1. **Search Layer**: Handles multi-source result aggregation
2. **Analysis Layer**: Processes and enhances results with AI
3. **Storage Layer**: Manages caching and persistence
4. **Presentation Layer**: Handles result rendering and UI

## Performance Features

- Concurrent API calls for faster searches
- Smart caching to reduce redundant requests
- Graph-based ranking for improved relevance
- Efficient content storage with LanceDB

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
