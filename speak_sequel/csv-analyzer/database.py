import pandas as pd
import sqlite3

def store_csv_in_db(csv_path, db_name="database.db", table_name="dataset"):
    try:
        # Try reading with different chunk sizes for large files
        try:
            # First attempt: read in chunks
            chunk_size = 10000
            chunks = pd.read_csv(csv_path, encoding='utf-8', chunksize=chunk_size)
            df = pd.concat(chunks, ignore_index=True)
        except Exception:
            # Second attempt: try different encodings
            encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"Error with encoding {encoding}: {str(e)}")
                    continue
            else:
                raise Exception("Unable to read the CSV file. Please check the file format and encoding.")

        # Clean and validate data
        df.columns = df.columns.str.strip().str.replace(' ', '_')
        
        # Handle data types and clean data
        for col in df.columns:
            try:
                # Convert object columns with mixed types to strings
                if df[col].dtype == 'object':
                    df[col] = df[col].fillna('').astype(str)
                # Handle numeric columns
                elif df[col].dtype in ['int64', 'float64']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception as e:
                print(f"Warning: Could not process column {col}: {str(e)}")
                df[col] = df[col].astype(str)

        # Store in database with proper connection handling
        conn = None
        try:
            conn = sqlite3.connect(db_name)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        finally:
            if conn:
                conn.close()

    except Exception as e:
        raise Exception(f"Error processing CSV file: {str(e)}")

def check_table_exists(db_name="database.db", table_name="dataset"):
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        return False