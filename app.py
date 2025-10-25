import os
import json
from flask import Flask, request, jsonify, render_template, session
import time

# --- LIBRARY IMPORTS ---
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import docx # python-docx
except ImportError:
    docx = None

from fuzzywuzzy import fuzz
# --- END IMPORTS ---

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

app.secret_key = "edu_rank_2025_secure_key_please_change_in_prod"
os.makedirs('data', exist_ok=True)

# ======================
# UTILITY FUNCTIONS
# ======================

# --- UPGRADED FUNCTION 1: "Smart Parser" V2 ---
def extract_answers_from_file(filepath):
    text = ""
    if filepath.lower().endswith('.pdf'):
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is not installed")
        try:
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF: {e}")
            
    elif filepath.lower().endswith('.txt'):
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                text = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read TXT: {e}")

    elif filepath.lower().endswith('.docx'):
        if docx is None:
            raise RuntimeError("python-docx is not installed")
        try:
            doc = docx.Document(filepath)
            all_paragraphs = []
            for para in doc.paragraphs:
                all_paragraphs.append(para.text)
            text = "\n".join(all_paragraphs)
        except Exception as e:
            raise RuntimeError(f"Failed to read DOCX: {e}")
            
    else:
        raise RuntimeError("Unsupported file type")

    answers = {}
    lines = text.split('\n')

    # --- Smart Parser Logic V2 (Handles mixed formats) ---
    print("Starting parser V2...")
    current_q_num = 1 # Fallback question number
    
    for line in lines:
        line = line.strip()
        if not line: # Skip empty lines
            continue

        parsed_num = None
        parsed_ans = None

        # Try to parse a numbered line
        if line and line[0].isdigit():
            if '.' in line:
                parts = line.split('.', 1)
            elif ')' in line:
                parts = line.split(')', 1)
            else:
                parts = None # Just a digit, no separator
            
            if parts and len(parts) == 2:
                q_num_str = parts[0].strip()
                if q_num_str.isdigit():
                    parsed_num = int(q_num_str)
                    parsed_ans = parts[1].strip()

        if parsed_num is not None:
            # Found a numbered line, e.g., "4.c"
            answers[str(parsed_num)] = parsed_ans
            current_q_num = parsed_num + 1 # Set expectation for the *next* line
        else:
            # Did not find a numbered line, e.g., "b"
            # Assign it to the current question number
            answers[str(current_q_num)] = line
            current_q_num += 1 # Increment for the next un-numbered line
    
    print(f"Parser found {len(answers)} answers.")
    return answers

def load_correct_answers(week):
    filename = f"data/answers_{week.lower().replace(' ', '')}.json"
    if not os.path.exists(filename):
        sample = { "1": "Paris", "2": "Newton" }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sample, f, indent=2)
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- UPGRADED FUNCTION 2: "Hybrid Grader" ---
def calculate_score(extracted_answers, week):
    correct_answers = load_correct_answers(week)
    total = len(correct_answers)
    score = 0
    
    for q_num, correct_ans_text in correct_answers.items():
        student_ans_text = extracted_answers.get(q_num, "").strip()

        if not student_ans_text:
            continue # Skip if student didn't answer

        student_ans = student_ans_text.lower()
        correct_ans = correct_ans_text.lower()

        # --- Hybrid Grader Logic ---
        
        # 1. Try for a full-text fuzzy match first
        # (Works for "C. A location..." vs "C. A location...")
        if fuzz.ratio(student_ans, correct_ans) >= 85:
            score += 1
            
        # 2. If no full-text match, try a letter-only match
        # (Works for "C" or "C." vs "C. A location...")
        elif correct_ans.startswith(student_ans) and len(student_ans) <= 2: 
            # This checks if "c. a location..." starts with "c"
            # and that the student's answer is short (like "c" or "c.")
            score += 1

    return score, total

def get_leaderboard_path(week):
    return f"data/leaderboard_{week.lower().replace(' ', '')}.json"

def update_leaderboard(student_data, week):
    lb_path = get_leaderboard_path(week)
    leaderboard = []
    if os.path.exists(lb_path):
        with open(lb_path, 'r', encoding='utf-8') as f:
            try:
                leaderboard = json.load(f)
            except json.JSONDecodeError:
                leaderboard = []
    
    leaderboard = [s for s in leaderboard if s['roll'] != student_data['roll']]
    leaderboard.append(student_data)
    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    leaderboard = leaderboard[:20]

    with open(lb_path, 'w', encoding='utf-8') as f:
        json.dump(leaderboard, f, indent=2)

def get_leaderboard(week):
    lb_path = get_leaderboard_path(week)
    if not os.path.exists(lb_path):
        return []
    try:
        with open(lb_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

# ======================
# ROUTES (All Unchanged)
# ======================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    name = request.form.get('name', '').strip()
    roll = request.form.get('roll', '').strip()
    if not name or not roll:
        return jsonify({"error": "Name and Roll Number are required"}), 400
    session['name'] = name
    session['roll'] = roll
    return jsonify({"success": True})

@app.route('/grade', methods=['POST'])
def grade():
    if 'name' not in session or 'roll' not in session:
        return jsonify({"error": "Not logged in"}), 403

    week = request.form.get('week', 'Week 1')
    file = request.files.get('pdf') 
    if not file:
        return jsonify({"error": "File is required"}), 400

    filename = file.filename
    extension = os.path.splitext(filename)[1].lower()
    if extension not in ['.pdf', '.txt', '.docx']:
         return jsonify({"error": "File must be .pdf, .txt, or .docx"}), 400
    
    filepath = f"temp_{session['roll']}_{int(time.time())}{extension}"

    try:
        file.save(filepath)
        extracted = extract_answers_from_file(filepath)
        score, total = calculate_score(extracted, week)
        
        if total == 0:
            percentage = 0.0
        else:
            percentage = round((score / total) * 100, 1)

        student = {
            "name": session['name'],
            "roll": session['roll'],
            "score": percentage
        }
        update_leaderboard(student, week)

        return jsonify({
            "success": True,
            "score": score,
            "total": total,
            "percentage": percentage,
            "is_top": percentage >= 90
        })
    except Exception as e:
        print(f"Error during grading: {e}")
        return jsonify({"error": f"Grading failed: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/api/leaderboard')
def leaderboard_api():
    week = request.args.get('week', 'Week 1')
    data = get_leaderboard(week)
    return jsonify(data)

# ======================
if __name__ == '__main__':
    print("🚀 EduRank running at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

