import lancedb
import pandas as pd
from datetime import datetime

def inspect_lancedb_contents():
    try:
        # Connect to LanceDB
        db = lancedb.connect("./lancedb")
        
        # Get the table
        table = db.open_table("search_results")
        
        # Get all rows from the table
        df = table.to_pandas()
        
        # Print total number of rows
        print(f"Total rows in LanceDB table: {len(df)}")
        
        # Print number of blog posts
        blog_posts = df[df['is_blog_post'] == True]
        print(f"Number of blog posts: {len(blog_posts)}")
        
        # Print details of each blog post
        for index, post in blog_posts.iterrows():
            print(f"\nBlog Post {index + 1}:")
            print(f"Title: {post['title']}")
            print(f"Slug: {post['slug']}")
            print(f"Publish Date: {post['publish_date']}")
            print(f"Is Blog Post: {post['is_blog_post']}")
            print(f"Description: {post['description'][:100]}...")  # First 100 characters of description
        
        # If there are no blog posts, print all row titles to see what's in the database
        if len(blog_posts) == 0:
            print("\nAll row titles in the database:")
            for index, row in df.iterrows():
                print(f"{index + 1}. {row['title']} (is_blog_post: {row['is_blog_post']})")
        
        # Print some statistics
        print(f"\nUnique sources: {df['source'].unique()}")
        print(f"Date range: from {df['publish_date'].min()} to {df['publish_date'].max()}")
        
    except Exception as e:
        print(f"Error inspecting LanceDB contents: {str(e)}")

if __name__ == "__main__":
    inspect_lancedb_contents()