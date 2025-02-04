# Move imports and API key to top
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import pandas as pd
import sqlite3
import markdown2

# Define format_text_response at module level
def format_text_response(text):
    return markdown2.markdown(text, extras=['tables', 'fenced-code-blocks'])

API_KEY = "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"

# Configure session globally
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

class DatasetContext:
    _instance = None
    _dataset_preview = None
    _schema = None

    @classmethod
    def set_context(cls, db_path="database.db"):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table info and sample data
            cursor.execute("PRAGMA table_info(dataset)")
            schema_info = cursor.fetchall()
            
            # Get actual table data for better context
            df = pd.read_sql("SELECT * FROM dataset LIMIT 5", conn)
            
            # Create detailed preview with actual data types and examples
            preview_str = """
TABLE STRUCTURE AND DATA:
------------------------
Table Name: 'dataset' (This is the only table in the database)

Column Information:
"""
            for col in schema_info:
                col_name = col[1]
                col_type = col[2]
                preview_str += f"- {col_name} ({col_type})\n"
            
            preview_str += "\nFirst 5 rows of data:\n"
            preview_str += df.to_string(index=False)
            
            cls._schema = [col[1] for col in schema_info]
            cls._dataset_preview = preview_str
            
            print("\nDataset loaded successfully:")
            print(f"Columns: {', '.join(cls._schema)}")
            print("Sample data loaded")
            
            conn.close()
            
        except Exception as e:
            cls._dataset_preview = None
            cls._schema = None
            print(f"Error setting context: {str(e)}")
            raise Exception(f"Failed to set dataset context: {str(e)}")

def query_gemini(prompt, include_data_context=True):
    try:
        messages = []
        
        if include_data_context and DatasetContext._dataset_preview:
            context_message = {
                "role": "system",
                "content": f"""You are a SQL query assistant. You have access to a SINGLE table named 'dataset' with the following structure:

{DatasetContext._dataset_preview}

CRITICAL RULES:
1. ONLY use the table name 'dataset'
2. ONLY use columns that are shown above
3. ALL queries must use: SELECT ... FROM dataset
4. DO NOT reference any other tables (like 'drivers' or 'races')
5. Base all analysis on the actual columns shown above

Example of a valid query:
SELECT {DatasetContext._schema[0]}, {DatasetContext._schema[1]} FROM dataset LIMIT 5;"""
            }
            messages.append(context_message)
            
        # Add user question with context reminder
        messages.append({
            "role": "user",
            "content": f"Based on the F1 dataset provided, {prompt}"
        })

        response = session.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "CSV Analyzer"
            },
            json={
                "model": "google/gemini-2.0-flash-thinking-exp:free",
                "messages": messages,
                "timeout": 30,
                "max_tokens": 2048,  # Increase max tokens
                "temperature": 0.1,   # Lower temperature for more consistent responses
                "stream": False       # Ensure we get complete responses
            },
            verify=True
        )
        
        if response.status_code == 200:
            response_data = response.json()
            print("API Response:", response_data)
            
            # Check for error in response
            if 'error' in response_data:
                error_message = response_data['error'].get('message', 'Unknown error occurred')
                if '429' in str(error_message):
                    return {
                        "type": "error",
                        "content": "The API is currently busy. Please wait a moment and try again."
                    }
                return {"type": "error", "content": error_message}
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0]['message']['content']
                finish_reason = response_data['choices'][0].get('finish_reason')
                
                # Handle truncated responses
                if finish_reason in ['length', 'MAX_TOKENS']:
                    content += "\n\n*Note: Response was truncated due to length. Please try a more specific question.*"
                
                # Handle SQL queries with potential explanations
                if "```sql" in content.lower():
                    parts = content.split("```sql")
                    explanation = format_text_response(parts[0])
                    query = parts[1].split("```")[0].strip()
                    return {
                        "type": "sql",
                        "query": query,
                        "explanation": explanation
                    }
                elif content.strip().upper().startswith(('SELECT', 'WITH')):
                    return {
                        "type": "sql",
                        "query": content.strip(),
                        "explanation": ""
                    }
                else:
                    # Format markdown content
                    formatted_content = format_text_response(content)
                    return {
                        "type": "text",
                        "content": formatted_content
                    }
            else:
                return {
                    "type": "error",
                    "content": "No response received from the API. Please try again."
                }
        elif response.status_code == 429:
            return {
                "type": "error",
                "content": "Too many requests. Please wait a moment and try again."
            }
        else:
            return {
                "type": "error",
                "content": f"API Error ({response.status_code}). Please try again later."
            }
            
    except Exception as e:
        print(f"Error details: {str(e)}")
        return {
            "type": "error",
            "content": "An error occurred while processing your request. Please try again."
        }

def reset_dataset_context():
    DatasetContext._dataset_preview = None
    DatasetContext._schema = None