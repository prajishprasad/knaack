import time
import pdfplumber
from naac_website_scraper import GRADE_SHEET_FOLDER, PEER_TEAM_REPORT_FOLDER
import os
import sqlite3
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore

def create_db(conn):
    """Create a database to store the NAAC accreditation data using sqlite3"""
    cursor = conn.cursor()
    # Create main naac table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS institution_details (
            hei_assessment_id INTEGER PRIMARY KEY,
            hei_name TEXT,
            aishe_id TEXT,
            other_address TEXT,
            state_name TEXT,
            iiqa_submitted_date TEXT,
            date_of_decleration TEXT,
            grade TEXT
        )
    ''')
    
    # Commit and close
    conn.commit()

def insert_institution_details(entry,conn):
    """Insert a single NAAC accreditation record into the database."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO institution_details (
            hei_assessment_id,
            hei_name,
            aishe_id,
            other_address,
            state_name,
            iiqa_submitted_date,
            date_of_decleration,
            grade
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        entry.get('hei_assessment_id'),
        entry.get('hei_name'),
        entry.get('aishe_id'),
        entry.get('other_address'),
        entry.get('state_name'),
        entry.get('iiqa_submitted_date'),
        entry.get('date_of_decleration'),
        entry.get('grade')
    ))
    conn.commit()

# Example usage: insert all entries from your JSON file
def insert_all_from_json(naac_data_file,conn):
    
    with open(naac_data_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    for entry in data['data']:
        print("Adding entry:", entry['hei_name'], "to the database...")
        insert_institution_details(entry,conn)

def create_criteria_table(conn):
    """Create a table for criteria and key indicators."""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS criteria_key_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            criterion TEXT,
            criterion_no FLOATING,
            key_indicator TEXT
        )
    ''')
    conn.commit()

def insert_criteria_key_indicators(conn):
    """Insert the NAAC criteria and key indicators into the table."""
    cursor = conn.cursor()

    # List of tuples: (criterion, key_indicator)
    data = [
        ("Criterion 1: Curricular Aspects", 1, "Criterion 1: Curricular Aspects"),
        ("Criterion 1: Curricular Aspects", 1.1, "1.1 Curricular Planning and Implementation"),
        ("Criterion 1: Curricular Aspects", 1.2, "1.2 Academic Flexibility"),
        ("Criterion 1: Curricular Aspects", 1.3, "1.3 Curriculum Enrichment"),
        ("Criterion 1: Curricular Aspects", 1.4, "1.4 Feedback System"),
        ("Criterion 2: Teaching-Learning and Evaluation", 2, "Criterion 2: Teaching-Learning and Evaluation"),
        ("Criterion 2: Teaching-Learning and Evaluation", 2.1, "2.1 Student Enrolment and Profile"),
        ("Criterion 2: Teaching-Learning and Evaluation", 2.2, "2.2 Catering to Student Diversity"),
        ("Criterion 2: Teaching-Learning and Evaluation", 2.3, "2.3 Teaching-Learning Process"),
        ("Criterion 2: Teaching-Learning and Evaluation", 2.4, "2.4 Teacher Profile and Quality"),
        ("Criterion 2: Teaching-Learning and Evaluation", 2.5, "2.5 Evaluation Process and Reforms"),
        ("Criterion 2: Teaching-Learning and Evaluation", 2.6, "2.6 Student Performance and Learning Outcomes"),
        ("Criterion 2: Teaching-Learning and Evaluation", 2.7, "2.7 Student Satisfaction Survey"),
        ("Criterion 3: Research, Innovations and Extension", 3, "Criterion 3: Research, Innovations and Extension"),
        ("Criterion 3: Research, Innovations and Extension", 3.1, "3.1 Promotion of Research and Facilities"),
        ("Criterion 3: Research, Innovations and Extension", 3.2, "3.2 Resource Mobilization for Research"),
        ("Criterion 3: Research, Innovations and Extension", 3.3, "3.3 Innovation Ecosystem"),
        ("Criterion 3: Research, Innovations and Extension", 3.4, "3.4 Research Publications and Awards"),
        ("Criterion 3: Research, Innovations and Extension", 3.5, "3.5 Consultancy"),
        ("Criterion 3: Research, Innovations and Extension", 3.6, "3.6 Extension Activities"),
        ("Criterion 3: Research, Innovations and Extension", 3.7, "3.7 Collaboration"),
        ("Criterion 4: Infrastructure and Learning Resources", 4, "Criterion 4: Infrastructure and Learning Resources"),
        ("Criterion 4: Infrastructure and Learning Resources", 4.1, "4.1 Physical Facilities"),
        ("Criterion 4: Infrastructure and Learning Resources", 4.2, "4.2 Library as a Learning Resource"),
        ("Criterion 4: Infrastructure and Learning Resources", 4.3, "4.3 IT Infrastructure"),
        ("Criterion 4: Infrastructure and Learning Resources", 4.4, "4.4 Maintenance of Campus Infrastructure"),
        ("Criterion 5: Student Support and Progression", 5, "Criterion 5: Student Support and Progression"),
        ("Criterion 5: Student Support and Progression", 5.1, "5.1 Student Support"),
        ("Criterion 5: Student Support and Progression", 5.2, "5.2 Student Progression"),
        ("Criterion 5: Student Support and Progression", 5.3, "5.3 Student Participation and Activities"),
        ("Criterion 5: Student Support and Progression", 5.4, "5.4 Alumni Engagement"),
        ("Criterion 6: Governance, Leadership and Management", 6, "Criterion 6: Governance, Leadership and Management"),
        ("Criterion 6: Governance, Leadership and Management", 6.1, "6.1 Institutional Vision and Leadership"),
        ("Criterion 6: Governance, Leadership and Management", 6.2, "6.2 Strategy Development and Deployment"),
        ("Criterion 6: Governance, Leadership and Management", 6.3, "6.3 Faculty Empowerment Strategies"),
        ("Criterion 6: Governance, Leadership and Management", 6.4, "6.4 Financial Management and Resource Mobilization"),
        ("Criterion 6: Governance, Leadership and Management", 6.5, "6.5 Internal Quality Assurance System"),
        ("Criterion 7: Institutional Values and Best Practices", 7, "7 Institutional Values and Best Practices"),
        ("Criterion 7: Institutional Values and Best Practices", 7.1, "7.1 Institutional Values and Social Responsibilities"),
        ("Criterion 7: Institutional Values and Best Practices", 7.2, "7.2 Best Practices"),
        ("Criterion 7: Institutional Values and Best Practices", 7.3, "7.3 Institutional Distinctiveness"),
    ]

    cursor.executemany(
        "INSERT INTO criteria_key_indicators (criterion, criterion_no, key_indicator) VALUES (?, ?, ?)", data
    )
    conn.commit()


def create_criteria_wise_grade_table(conn):
    """Create a table for criteria-wise grades."""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS criteria_wise_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aishe_id TEXT,
            criterion_no FLOATING,
            weightage FLOATING,
            criterion_wise_weighted_grade_point FLOATING,
            criterion_wise_gpa FLOATING,
            FOREIGN KEY (aishe_id) REFERENCES institution_details(aishe_id),
            FOREIGN KEY (criterion_no) REFERENCES criteria_key_indicators(criterion_no)
        )
    ''')
    conn.commit()

def insert_criteria_wise_grades(data,conn):
    """Insert the NAAC criteria-wise grades into the table."""
    cursor = conn.cursor()
    try:
        cursor.executemany(
            "INSERT INTO criteria_wise_grades (aishe_id, criterion_no, weightage, criterion_wise_weighted_grade_point, criterion_wise_gpa) VALUES (?, ?, ?, ?, ?)", data
        )
        conn.commit()
    except:
        print(f"Data causing error in insert_criteria_wise_grades: {data}")
    

def create_key_indicators_table(conn):
    """Create a table for key indicators."""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS key_indicators_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aishe_id TEXT,
            criterion_no FLOATING,
            key_indicator_weightage FLOATING,
            key_indicator_weigtage_gpa FLOATING,
            FOREIGN KEY (aishe_id) REFERENCES institution_details(aishe_id),
            FOREIGN KEY (criterion_no) REFERENCES criteria_key_indicators(criterion_no)
        )
    ''')
    conn.commit()

def insert_key_indicators_grades(data,conn):
    """Insert the NAAC key indicators grades into the table."""
    try:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO key_indicators_grades (aishe_id, criterion_no, key_indicator_weightage, key_indicator_weigtage_gpa) VALUES (?, ?, ?, ?)", data
        )
        conn.commit()
    except:
        print("Error inserting data for key indicators grades:", data)


def create_database_and_tables(conn):
    """Create the database and tables."""
    create_db(conn)
    create_criteria_table(conn)
    insert_criteria_key_indicators(conn)
    create_criteria_wise_grade_table(conn)
    create_key_indicators_table(conn)
    print("Database created and tables populated successfully.")


def extract_grades_from_pdf(pdf_file,aishe_id,conn):
    """Extract grades from the PDF file."""
    tables = []
    # Extract tables from the first page
    tables.extend(pdf_file.pages[1].extract_tables())
    for i, table in enumerate(tables):
        #print(f"Table {i+1}:")
        for row in table:
            #remove \n and \r from each cell
            row = [cell.replace('\n', ' ').replace('\r', ' ') if isinstance(cell, str) else cell for cell in row]
            #print(row)
            #if row[0] is an integer or float, print it as is
            # Check if the first element of the row contains digits
            try:
                float(row[0])
                data = (
                    aishe_id,
                    float(row[0]),  # criterion_no
                    float(row[2]),  # criterion_weightage
                    float(row[3]),  # criterion_weighted_grade_point
                    float(row[4]),  # criterion_gpa
                )
                # Insert the data into the key_indicators_grades table
                insert_criteria_wise_grades([data],conn)
            except (ValueError, TypeError):
                # If it raises an error, it means it's not a number
                pass

    tables = []
    for p in range(2,len(pdf_file.pages)):
        p = pdf_file.pages[p]
        tables.extend(p.extract_tables())


    for i, table in enumerate(tables):
        #print(f"Table {i+1}:")
        for row in table:
            #remove \n and \r from each cell
            row = [cell.replace('\n', ' ').replace('\r', ' ') if isinstance(cell, str) else cell for cell in row]
            #print(row)
            #if row[0] is an integer or float, print it as is
            # Check if the first element of the row contains digits
            try:
                float(row[0])
                data = (
                    aishe_id,
                    float(row[0]),  # criterion_no
                    float(row[2]),  # key_indicator_weightage
                    float(row[3]),  # key_indicator_weigtage_gpa
                )
                # Insert the data into the key_indicators_grades table
                insert_key_indicators_grades([data],conn)
            except (ValueError, TypeError):
                # If it raises an error, it means it's not a number
                pass

def extract_grades_from_pdf_folder(folder_path,conn):
    """Extract grades from all PDF files in the specified folder."""
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            pdf_file_path = os.path.join(folder_path, filename)
            print(f"Processing file: {pdf_file_path}")
            with pdfplumber.open(pdf_file_path) as pdf_file:
                # Extract the AISHE ID from the filename
                aishe_id = filename.split('_')[0]
                extract_grades_from_pdf(pdf_file, aishe_id,conn)
            print(f"Finished processing file: {pdf_file_path}")

def get_institution_name(aishe_id):
    """Get the institution name from the AISHE ID from the sqlite database"""
    conn = sqlite3.connect('naac_accreditation.db')
    cursor = conn.cursor()
    cursor.execute("SELECT hei_name FROM institution_details WHERE aishe_id=?", (aishe_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return None
    
def load_peer_team_reports_into_vector_db():
    """Load all pages from the Peer Team Report PDF folder."""
    for file in os.listdir(PEER_TEAM_REPORT_FOLDER):
        if file.endswith(".pdf"):
            print(f"Loading {file}...")
            institution_name = get_institution_name(file.split("_")[0])
            pages = []
            loader = PyPDFLoader(os.path.join(PEER_TEAM_REPORT_FOLDER, file))
            for page in loader.load():
                pages.append(page)
            print(f"Loaded {institution_name} pages from {file}.")

            # Create the vector database    
            create_vector_database(pages, institution_name)


    print("Vector databases created for all Peer Team Report files.")
    return pages

#Function to create the vector database
def create_vector_database(pages,institution_name):
    """Create a vector database from the loaded pages."""
    print("Creating vector database...")
    # Split the documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    docs = text_splitter.split_documents(pages)
    for doc in docs:
        # Add institution name to metadata
        doc.metadata["college_name"] = institution_name
    
    pinecone_api_key = os.environ.get("PINECONE_API_KEY")

    pc = Pinecone(
            api_key=pinecone_api_key
    )
    index_name = "naac-index"
    # Initialize index client
    index = pc.Index(name=index_name)
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = PineconeVectorStore(index=index, embedding=embeddings_model)
    vector_store.add_documents(documents=docs)
    print("Vector database persisted for docs of institution:", institution_name)
    return vector_store

if __name__ == "__main__":
    print("Starting script...")
    #Uncomment the following lines when you want to create and populate the DB for the first time
    #conn = sqlite3.connect('naac_accreditation.db')
    # create_database_and_tables(conn)
    # insert_all_from_json(naac_data_file='naac_accreditation_data_final_all.json',conn=conn)
    # extract_grades_from_pdf_folder(GRADE_SHEET_FOLDER,conn)
    #conn.close()

    load_peer_team_reports_into_vector_db()




