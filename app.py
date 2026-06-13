# from flask import Flask, jsonify, request
# from flask_cors import CORS
# from pymongo import MongoClient
# from bson import ObjectId
# import os
# from dotenv import load_dotenv

# load_dotenv()

# app = Flask(__name__)
# CORS(app)

# # MongoDB Connection
# db = client["resource_planner_db"]

# # Helper function to convert MongoDB ObjectId to string before sending to React
# def serialize_doc(doc):
#     if not doc:
#         return None
#     doc["_id"] = str(doc["_id"])
#     return doc


# # ================= EMPLOYEES API =================

# @app.route('/api/employees', methods=['GET'])
# def get_employees():
#     employees = list(db.employees.find())
#     serialized_employees = []
    
#     for emp in employees:
#         emp_id_str = str(emp["_id"])
#         # Find all allocations for this specific employee
#         allocations = list(db.allocations.find({"employee_id": emp_id_str}))
        
#         # Get the project names they are assigned to
#         project_titles = []
#         for alloc in allocations:
#             proj = db.projects.find_one({"_id": ObjectId(alloc["project_id"])})
#             if proj:
#                 project_titles.append(f"{proj['title']} ({alloc['allocated_hours_per_week']}h)")
        
#         emp_serialized = serialize_doc(emp)
#         emp_serialized["assigned_projects"] = project_titles
#         serialized_employees.append(emp_serialized)
        
#     return jsonify(serialized_employees)

# @app.route('/api/employees', methods=['POST'])
# def add_employee():
#     data = request.json
    
#     # Structure matching our schema blueprint
#     new_employee = {
#         "name": data.get("name"),
#         "email": data.get("email"),
#         "skills": data.get("skills", []), # Expecting an array of strings like ["React", "Python"]
#         "experience_level": data.get("experience_level", "Intermediate"),
#         "max_capacity_weeks": int(data.get("max_capacity_weeks", 40)),
#         "current_allocated_hours": 0 
#     }
    
#     result = db.employees.insert_one(new_employee)
#     return jsonify({"message": "Employee added successfully!", "id": str(result.inserted_id)}), 201


# # ================= PROJECTS API =================

# @app.route('/api/projects', methods=['GET'])
# def get_projects():
#     projects = list(db.projects.find())
#     return jsonify([serialize_doc(p) for p in projects])

# @app.route('/api/projects', methods=['POST'])
# def add_project():
#     data = request.json
    
#     # Structure matching our schema blueprint
#     new_project = {
#         "title": data.get("title"),
#         "description": data.get("description"),
#         "required_skills": data.get("required_skills", []),
#         "estimated_hours_required": int(data.get("estimated_hours_required", 0)),
#         "status": data.get("status", "Planned"),
#         "start_date": data.get("start_date"),
#         "end_date": data.get("end_date")
#     }
    
#     result = db.projects.insert_one(new_project)
#     return jsonify({"message": "Project created successfully!", "id": str(result.inserted_id)}), 201


# # ================= ALLOCATION & SMART ALGORITHM API =================

# @app.route('/api/projects/<project_id>/recommendations', methods=['GET'])
# def get_recommendations(project_id):
#     # 1. Find the project
#     project = db.projects.find_one({"_id": ObjectId(project_id)})
#     if not project:
#         return jsonify({"message": "Project not found"}), 404
        
#     # Get required skills and convert them to lowercase for accurate matching
#     req_skills = [skill.lower() for skill in project.get("required_skills", [])]
    
#     # 2. Fetch all employees
#     all_employees = list(db.employees.find())
#     recommended_team = []
    
#     for emp in all_employees:
#         # Convert employee skills to lowercase to prevent case issues
#         emp_skills = [s.lower() for s in emp.get("skills", [])]
        
#         # Calculate overlapping skills
#         matching_skills = list(set(req_skills).intersection(set(emp_skills)))
#         match_count = len(matching_skills)
        
#         # Calculate available weekly hours remaining (40 max capacity - what they already work)
#         available_hours = emp.get("max_capacity_weeks", 40) - emp.get("current_allocated_hours", 0)
        
#         # We recommend them if they have at least one matching skill AND have open hours
#         if match_count > 0 and available_hours > 0:
#             emp_serialized = serialize_doc(emp)
#             # Attach custom tracking metrics to send to React
#             emp_serialized["match_count"] = match_count
#             emp_serialized["matching_skills"] = matching_skills
#             emp_serialized["available_hours"] = available_hours
#             recommended_team.append(emp_serialized)
            
#     # Sort the recommendations so the employees with the MOST skill matches appear at the top
#     recommended_team = sorted(recommended_team, key=lambda x: x["match_count"], reverse=True)
    
#     return jsonify(recommended_team)


# @app.route('/api/allocations', methods=['POST'])
# def allocate_resource():
#     data = request.json
#     emp_id = data.get("employee_id")
#     proj_id = data.get("project_id")
#     hours = int(data.get("allocated_hours_per_week", 0))
    
#     # 1. Update the employee's current allocated workload counter
#     db.employees.update_one(
#         {"_id": ObjectId(emp_id)},
#         {"$inc": {"current_allocated_hours": hours}}
#     )
    
#     # 2. Record the assignment entry mapping
#     new_allocation = {
#         "employee_id": emp_id,
#         "project_id": proj_id,
#         "allocated_hours_per_week": hours
#     }
#     db.allocations.insert_one(new_allocation)
    
#     return jsonify({"message": "Employee successfully allocated to project!"}), 201


# @app.route('/')
# def home():
#     return jsonify({"message": "Flask backend with Database APIs is running!"})

# if __name__ == '__main__':
#     app.run(debug=True, port=5000)

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import jwt
import bcrypt
import datetime
from functools import wraps

load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    # If running locally, print a reminder to set up your environment variables
    print("⚠️ WARNING: MONGO_URI environmental variable not found!")
    
client = MongoClient(MONGO_URI)
db = client["resource_planner_db"]

def serialize_doc(doc):
    if not doc:
        return None
    doc["_id"] = str(doc["_id"])
    return doc


# ================= JWT VERIFICATION GUARDRAIL =================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({"message": "Access Denied: Token Missing!"}), 401
            
        try:
            data = jwt.decode(token, "super-secret-hr-planner-key-2026", algorithms=["HS256"])
            current_user = db.users.find_one({"_id": ObjectId(data["user_id"])})
            if not current_user:
                return jsonify({"message": "Invalid session profile!"}), 401
                
            # ➕ Extract multi-tenant metadata constraints
            user_context = {
                "user_id": data["user_id"],
                "user_name": data.get("user_name", "HR Manager")
            }
        except Exception as e:
            return jsonify({"message": "Session expired or invalid!"}), 401
            
        # 🔄 Pass context directly into the endpoint routine arguments block
        return f(user_context, *args, **kwargs)
    return decorated

# ================= EMPLOYEES API =================

@app.route('/api/employees', methods=['GET'])
@token_required
def get_employees(user_context):
    employees = list(db.employees.find({"user_id": user_context["user_id"]}))
    serialized_employees = []
    
    for emp in employees:
        emp_id_str = str(emp["_id"])
        # Find all allocations for this employee
        allocations = list(db.allocations.find({"employee_id": emp_id_str}))
        
        project_titles = []
        for alloc in allocations:
            proj = db.projects.find_one({"_id": ObjectId(alloc["project_id"])})
            if proj:
                project_titles.append(f"{proj['title']} ({alloc['allocated_hours_per_week']}h)")
        
        emp_serialized = serialize_doc(emp)
        emp_serialized["assigned_projects"] = project_titles
        serialized_employees.append(emp_serialized)
        
    return jsonify(serialized_employees)

@app.route('/api/employees', methods=['POST'])
@token_required
def add_employee(user_context):
    data = request.json
    new_employee = {
        "user_id": user_context["user_id"],
        "name": data.get("name"),
        "email": data.get("email"),
        "skills": data.get("skills", []),
        "experience_level": data.get("experience_level", "Intermediate"),
        "max_capacity_weeks": int(data.get("max_capacity_weeks", 40)),
        "current_allocated_hours": 0 
    }
    result = db.employees.insert_one(new_employee)
    return jsonify({"message": "Employee added!", "id": str(result.inserted_id)}), 201

# ================= PROJECTS API =================

@app.route('/api/projects', methods=['GET'])
@token_required
def get_projects(user_context):
    projects = list(db.projects.find({"user_id": user_context["user_id"]}))
    serialized_projects = []
    
    for proj in projects:
        proj_id_str = str(proj["_id"])
        # Find all allocations booked to this specific project
        allocations = list(db.allocations.find({"project_id": proj_id_str}))
        total_booked = sum(int(a.get("allocated_hours_per_week", 0)) for a in allocations)
        
        proj_serialized = serialize_doc(proj)
        proj_serialized["total_allocated_hours"] = total_booked
        serialized_projects.append(proj_serialized)
        
    return jsonify(serialized_projects)

@app.route('/api/projects', methods=['POST'])
@token_required
def add_project(user_context):
    data = request.json
    new_project = {
        "user_id": user_context["user_id"],
        "title": data.get("title"),
        "description": data.get("description"),
        "required_skills": data.get("required_skills", []),
        "estimated_hours_required": int(data.get("estimated_hours_required", 0)),
        "status": data.get("status", "In Progress"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date")
    }
    result = db.projects.insert_one(new_project)
    return jsonify({"message": "Project created!", "id": str(result.inserted_id)}), 201

# ================= SMART ALLOCATION API =================

@app.route('/api/projects/<project_id>/recommendations', methods=['GET'])
@token_required
def get_recommendations(user_context, project_id):
    project = db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        return jsonify({"message": "Project not found"}), 404
        
    req_skills = [skill.lower() for skill in project.get("required_skills", [])]
    all_employees = list(db.employees.find({"user_id": user_context["user_id"]}))
    
    # --- ➕ SKILL DEFICIENCY CALCULATION ---
    all_agency_skills = set()
    for emp in all_employees:
        for s in emp.get("skills", []):
            all_agency_skills.add(s.lower())
            
    missing_from_agency = [skill for skill in req_skills if skill not in all_agency_skills]
    # ----------------------------------------
    
    recommended_team = []
    for emp in all_employees:
        emp_skills = [s.lower() for s in emp.get("skills", [])]
        matching_skills = list(set(req_skills).intersection(set(emp_skills)))
        match_count = len(matching_skills)
        
        available_hours = emp.get("max_capacity_weeks", 40) - emp.get("current_allocated_hours", 0)
        
        if match_count > 0:
            suitability_score = match_count 
            exp = emp.get("experience_level", "Intermediate")
            if exp == "Senior":
                suitability_score += 2.0
            elif exp == "Intermediate":
                suitability_score += 1.0
                
            emp_serialized = serialize_doc(emp)
            emp_serialized["match_count"] = match_count
            emp_serialized["matching_skills"] = matching_skills
            emp_serialized["available_hours"] = available_hours
            emp_serialized["suitability_score"] = suitability_score
            recommended_team.append(emp_serialized)
            
    recommended_team = sorted(recommended_team, key=lambda x: x["suitability_score"], reverse=True)
    
    # ➕ Updated return payload format
    return jsonify({
        "recommendations": recommended_team,
        "missing_skills": missing_from_agency
    })

@app.route('/api/allocations', methods=['POST'])
@token_required
def allocate_resource(user_context):
    data = request.json
    emp_id = data.get("employee_id")
    proj_id = data.get("project_id")
    hours = int(data.get("allocated_hours_per_week", 0))

    project = db.projects.find_one({"_id": ObjectId(proj_id), "user_id": user_context["user_id"]})
    if not project:
        return jsonify({"message": "Access Denied: Project not found in your workspace!"}), 403
    
    # 1. Fetch employee details to check experience level
    employee = db.employees.find_one({"_id": ObjectId(emp_id)})
    if not employee:
        return jsonify({"message": "Employee not found"}), 404
        
    # --- MENTORSHIP GUARDRAIL TRIGGER ---
    if employee.get("experience_level") == "Junior":
        # Check if any Senior is already allocated to this project
        existing_allocs = list(db.allocations.find({"project_id": proj_id}))
        has_senior = False
        
        for alloc in existing_allocs:
            assigned_emp = db.employees.find_one({"_id": ObjectId(alloc["employee_id"])})
            if assigned_emp and assigned_emp.get("experience_level") == "Senior":
                has_senior = True
                break
                
        # Block allocation if no Senior supervisor is present
        if not has_senior:
            return jsonify({
                "error": "mentorship_required",
                "message": "Warning: This project requires a Senior engineer for oversight."
            }), 400
    # ------------------------------------
    
    # Update employee allocation total counter
    db.employees.update_one(
        {"_id": ObjectId(emp_id)},
        {"$inc": {"current_allocated_hours": hours}}
    )
    
    # Store explicit mapping configuration
    new_allocation = {
        "employee_id": emp_id,
        "project_id": proj_id,
        "allocated_hours_per_week": hours
    }
    db.allocations.insert_one(new_allocation)
    return jsonify({"message": "Allocation stored!"}), 201


# ================= EDIT/UPDATE API ROUTES =================

@app.route('/api/employees/<id>', methods=['PUT'])
@token_required
def edit_employee(user_context,id):
    data = request.json
    updated_fields = {
        "name": data.get("name"),
        "email": data.get("email"),
        "skills": data.get("skills", []),
        "experience_level": data.get("experience_level")
    }
    
    db.employees.update_one({"_id": ObjectId(id), "user_id": user_context["user_id"]}, {"$set": updated_fields})
    return jsonify({"message": "Employee updated successfully!"})


@app.route('/api/projects/<id>', methods=['PUT'])
@token_required
def edit_project(user_context,id):
    data = request.json
    updated_fields = {
        "title": data.get("title"),
        "description": data.get("description"),
        "required_skills": data.get("required_skills", []),
        "estimated_hours_required": int(data.get("estimated_hours_required", 0)),
        "start_date": data.get("start_date"), 
        "end_date": data.get("end_date")
    }
    
    db.projects.update_one({"_id": ObjectId(id), "user_id": user_context["user_id"]}, {"$set": updated_fields})
    return jsonify({"message": "Project updated successfully!"})



@app.route('/api/allocations/remove', methods=['POST'])
@token_required
def remove_allocation(user_context):
    data = request.json
    emp_id = data.get("employee_id")
    # Because our string tracking format in get_employees is "Project Title (Xh)"
    project_title_string = data.get("project_string") 
    
    # Extract the project title from the string (e.g., "Internal AI Dashboard (20h)" -> "Internal AI Dashboard")
    if " (" in project_title_string:
        project_title = project_title_string.split(" (")[0]
        # Find the hour value from the string to subtract it
        hours_to_subtract = int(project_title_string.split("(")[1].replace("h)", ""))
    else:
        return jsonify({"message": "Invalid allocation string format"}), 400

    # 1. Find the project ID by matching the title
    project = db.projects.find_one({"title": project_title, "user_id": user_context["user_id"]})
    if not project:
        return jsonify({"message": "Project mapping not found in your workspace!"}), 404

    # 2. Remove the specific allocation document from the collection
    db.allocations.delete_one({
        "employee_id": emp_id,
        "project_id": str(project["_id"]),
        "allocated_hours_per_week": hours_to_subtract
    })

    # 3. Deduct the hours from the employee's profile
    db.employees.update_one(
        {"_id": ObjectId(emp_id)},
        {"$inc": {"current_allocated_hours": -hours_to_subtract}}
    )

    return jsonify({"message": "Resource successfully released from project!"})


@app.route('/api/projects/<id>/status', methods=['PUT'])
@token_required
def update_project_status(user_context,id):
    data = request.json
    new_status = data.get("status") # Expecting "Planned", "In Progress", or "Completed"
    
    # 1. Update the project status in the database
    result = db.projects.update_one(
        {"_id": ObjectId(id), "user_id": user_context["user_id"]}, 
        {"$set": {"status": new_status}}
    )
    if result.matched_count == 0:
        return jsonify({"message": "Project scope validation failed!"}), 403
    
    # 2. TRIGGER: If marked as Completed, automatically release all assigned engineers
    if new_status == "Completed":
        # Find all allocations bound to this project
        project_allocations = list(db.allocations.find({"project_id": id}))
        
        for alloc in project_allocations:
            emp_id = alloc["employee_id"]
            allocated_hours = int(alloc.get("allocated_hours_per_week", 0))
            
            # Reduce the employee's cumulative workload tracking counter
            db.employees.update_one(
                {"_id": ObjectId(emp_id)},
                {"$inc": {"current_allocated_hours": -allocated_hours}}
            )
            
        # Delete all allocation mapping records for this project out of the database
        db.allocations.delete_many({"project_id": id})
        
    return jsonify({"message": f"Project status updated to {new_status} and resources synchronized!"})


# ================= ARCHIVE PROJECT API ROUTE =================

@app.route('/api/projects/<id>/archive', methods=['PUT'])
@token_required
def archive_project(user_context,id):
    # Instead of deleting, soft-update the project's state flag to "Archived"
    result = db.projects.update_one(
        {"_id": ObjectId(id), "user_id": user_context["user_id"]}, 
        {"$set": {"status": "Archived"}}
    )
    if result.matched_count == 0: return jsonify({"message": "Unauthorized"}), 403
    
        
    return jsonify({"message": "Project successfully moved to historical archives!"}), 200


# ================= UNARCHIVE PROJECT API ROUTE =================

@app.route('/api/projects/<id>/unarchive', methods=['PUT'])
@token_required
def unarchive_project(user_context,id):
    # Set status back to "In Progress" to move it back to the active execution board
    result = db.projects.update_one(
        {"_id": ObjectId(id), "user_id": user_context["user_id"]}, 
        {"$set": {"status": "In Progress"}}
    )
    if result.matched_count == 0: return jsonify({"message": "Unauthorized"}), 403
        
    return jsonify({"message": "Project successfully restored to active operations!"}), 200


# ================= AUTH CONTROLLERS =================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not name or not email or not password:
        return jsonify({"message": "Missing required entry fields!"}), 400
    if db.users.find_one({"email": email}):
        return jsonify({"message": "An account with this email already exists!"}), 400
        
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    db.users.insert_one({"name": name, "email": email, "password": hashed_password})
    return jsonify({"message": "Account registered successfully!"}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    user = db.users.find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        return jsonify({"message": "Invalid credentials!"}), 401
        
    token = jwt.encode({
        "user_id": str(user["_id"]),
        "user_name": user.get("name", "HR Manager"),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, "super-secret-hr-planner-key-2026", algorithm="HS256")
    
    return jsonify({"token": token, "email": user["email"], "name": user.get("name", "HR Manager")}), 200

# ================= CSV DATA EXPORT GENERATOR API =================

@app.route('/api/exports/csv', methods=['GET'])
@token_required
def export_resource_forecast(user_context):
    # Fetch all employees and projects bound to this specific manager
    employees = list(db.employees.find({"user_id": user_context["user_id"]}))
    
    # Construct CSV headers string
    csv_data = "Employee Name,Experience Tiers,Current Allocated Hours,Remaining Capacity,Assigned Project Loads\n"
    
    for emp in employees:
        emp_id_str = str(emp["_id"])
        allocations = list(db.allocations.find({"employee_id": emp_id_str}))
        
        project_strings = []
        for alloc in allocations:
            proj = db.projects.find_one({"_id": ObjectId(alloc["project_id"])})
            if proj:
                project_strings.append(f"{proj['title']} ({alloc['allocated_hours_per_week']}h)")
        
        # Build clean comma-separated values row strings
        name = emp.get("name").replace(",", "")
        exp = emp.get("experience_level")
        booked_hours = emp.get("current_allocated_hours", 0)
        free_hours = 40 - booked_hours
        roles = " | ".join(project_strings) if project_strings else "Bench (Idle)"
        
        csv_data += f"{name},{exp},{booked_hours}h,{free_hours}h,{roles}\n"
        
    # Return as an explicit downloadable stream attachment file structure
    return csv_data, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=resource_allocation_forecast.csv'
    }


@app.route('/')
def home():
    return jsonify({"message": "API Pipeline Online"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)