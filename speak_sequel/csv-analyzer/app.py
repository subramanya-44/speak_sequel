from flask import Flask, request, render_template, flash, session, redirect, url_for
import os
import sqlite3
from database import store_csv_in_db, check_table_exists
from gemini_handler import query_gemini, DatasetContext, reset_dataset_context
from query_executor import execute_sql_query, get_table_schema
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = "datasets"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if 'delete_dataset' in request.form:
            # Add dataset deletion
            os.remove("database.db")
            reset_dataset_context()
            session.clear()
            flash('Dataset deleted successfully')
            return redirect(url_for('home'))
        
        if 'csv_file' not in request.files:
            flash('Please select a file')
            return redirect(url_for('home'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected')
            return redirect(url_for('home'))
        
        try:
            csv_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(csv_path)
            store_csv_in_db(csv_path)
            DatasetContext.set_context()  # Set the dataset context after upload
            session['current_file'] = file.filename
            flash('File successfully uploaded and processed')
        except Exception as e:
            flash(f'Error processing file: {str(e)}')
    
    return render_template("index.html", 
                         table_exists=check_table_exists(),
                         conversation=session.get('conversation', []),
                         current_file=session.get('current_file'))

# Add new route for clearing conversation
@app.route("/clear", methods=["POST"])
def clear_conversation():
    session['conversation'] = []
    return redirect(url_for('home'))

# Update the query route
@app.route("/query", methods=["POST"])
def query():
    try:
        user_question = request.form["question"]
        conversation = session.get('conversation', [])
        conversation.append({"user": user_question})

        if not check_table_exists():
            flash("Please upload a dataset first")
            return redirect(url_for('home'))

        response = query_gemini(user_question)
        
        if response["type"] == "error":
            conversation.append({
                "assistant": f'<div class="alert alert-warning">{response["content"]}</div>'
            })
        elif response["type"] == "sql":
            try:
                # Extract SQL query from response
                sql_query = response["query"].strip()
                explanation = response["explanation"]
                
                # Execute query and get results
                result = execute_sql_query(sql_query)
                
                # Convert results to HTML table
                html_result = result.to_html(
                    classes='table table-striped table-bordered',
                    index=False,
                    float_format=lambda x: '{:.2f}'.format(x) if isinstance(x, float) else x
                )
                
                # Combine explanation and results
                full_response = f"{explanation}<div class='sql-result'>{html_result}</div>"
                conversation.append({
                    "assistant": full_response,
                    "type": "table"
                })
            except Exception as e:
                logger.error(f"SQL Error: {str(e)}")
                conversation.append({
                    "assistant": f'<div class="alert alert-danger">Error executing query: {str(e)}</div>'
                })
        else:
            # Handle text responses
            conversation.append({
                "assistant": response["content"],
                "type": "text"
            })
        
        session['conversation'] = conversation
        return render_template("index.html", 
                             table_exists=True,
                             conversation=conversation,
                             current_file=session.get('current_file'))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        flash("An unexpected error occurred. Please try again later.")
        return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)