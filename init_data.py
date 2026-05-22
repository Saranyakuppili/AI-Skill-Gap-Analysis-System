import sqlite3
import os

def init_job_roles():
    # Ensure instance directory exists
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    conn = sqlite3.connect('instance/skill_gap.db')
    cursor = conn.cursor()
    
    # Create job_roles table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_name TEXT NOT NULL,
            job_description_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    job_roles = [
        {
            'role_name': 'Full Stack Developer',
            'job_description_text': '''
            We are looking for a Full Stack Developer to join our team. The ideal candidate should have
            strong experience in Python, JavaScript, React, Node.js, HTML, CSS, and SQL. Knowledge of
            MongoDB, PostgreSQL, Docker, and AWS is required. Experience with REST APIs, Git, and
            agile development methodologies is essential. The candidate should be familiar with
            microservices architecture and have experience with CI/CD pipelines.
            '''
        },
        {
            'role_name': 'Data Scientist',
            'job_description_text': '''
            Seeking a Data Scientist with expertise in Python, machine learning, deep learning,
            TensorFlow, PyTorch, and scikit-learn. Strong knowledge of statistics, data analysis,
            SQL, and data visualization tools like Tableau and Power BI is required. Experience with
            big data technologies, data preprocessing, and model deployment is essential. The
            candidate should have excellent communication skills and be able to present complex
            findings to stakeholders.
            '''
        },
        {
            'role_name': 'DevOps Engineer',
            'job_description_text': '''
            We are hiring a DevOps Engineer with extensive experience in Docker, Kubernetes,
            AWS, Azure, and Linux. Strong knowledge of CI/CD pipelines, infrastructure as code,
            and monitoring tools is required. Experience with scripting languages like Python and
            Bash, as well as configuration management tools, is essential. The candidate should
            be familiar with microservices, container orchestration, and cloud security best
            practices.
            '''
        },
        {
            'role_name': 'Frontend Developer',
            'job_description_text': '''
            Looking for a Frontend Developer with expertise in HTML, CSS, JavaScript, React,
            Angular, and Vue.js. Strong understanding of responsive design, cross-browser
            compatibility, and web performance optimization is required. Experience with
            state management, REST APIs, Git, and modern build tools is essential. The candidate
            should have a good eye for design and user experience.
            '''
        },
        {
            'role_name': 'Backend Developer',
            'job_description_text': '''
            Seeking a Backend Developer with strong experience in Python, Java, Node.js,
            SQL, and NoSQL databases like MongoDB and PostgreSQL. Knowledge of REST APIs,
            microservices architecture, Docker, and cloud platforms like AWS is required.
            Experience with authentication, security best practices, and scalable system
            design is essential. The candidate should be familiar with agile methodologies
            and version control systems.
            '''
        },
        {
            'role_name': 'Machine Learning Engineer',
            'job_description_text': '''
            We are looking for a Machine Learning Engineer with expertise in Python,
            TensorFlow, PyTorch, scikit-learn, and deep learning. Strong knowledge of
            machine learning algorithms, data preprocessing, model deployment, and MLOps
            is required. Experience with cloud platforms, containerization, and distributed
            computing is essential. The candidate should have excellent problem-solving
            skills and be able to optimize models for production.
            '''
        }
    ]
    
    for role in job_roles:
        cursor.execute('''
            INSERT OR IGNORE INTO job_roles (role_name, job_description_text)
            VALUES (?, ?)
        ''', (role['role_name'], role['job_description_text']))
    
    conn.commit()
    conn.close()
    print("Job roles initialized successfully!")

if __name__ == '__main__':
    init_job_roles()
