from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import sqlite3
from datetime import datetime
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import pdfplumber
import docx
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['DATABASE'] = 'instance/skill_gap.db'

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Database initialization
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_name TEXT NOT NULL,
            job_description_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resume_text TEXT NOT NULL,
            selected_role TEXT NOT NULL,
            similarity_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skill_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            missing_skill TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roadmap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill TEXT NOT NULL,
            week INTEGER NOT NULL,
            topic TEXT NOT NULL,
            resource_link TEXT,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# Resume parsing functions
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = pdfplumber.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def extract_text_from_docx(docx_path):
    text = ""
    try:
        doc = docx.Document(docx_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text

# NLP processing functions
def preprocess_text(text):
    # Convert to lowercase
    text = text.lower()
    # Remove special characters and numbers
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    # Tokenize
    tokens = word_tokenize(text)
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]
    return ' '.join(tokens)

def calculate_similarity(resume_text, job_description):
    # Preprocess texts
    resume_processed = preprocess_text(resume_text)
    job_processed = preprocess_text(job_description)
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([resume_processed, job_processed])
    
    # Calculate cosine similarity
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return similarity

def extract_skills_from_text(text):
    # Common technical skills keywords
    skill_keywords = [
        'python', 'java', 'javascript', 'react', 'nodejs', 'html', 'css', 'sql',
        'mongodb', 'postgresql', 'mysql', 'docker', 'kubernetes', 'aws', 'azure',
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
        'data analysis', 'data science', 'statistics', 'excel', 'tableau', 'power bi',
        'git', 'github', 'gitlab', 'ci/cd', 'devops', 'linux', 'ubuntu', 'windows',
        'c++', 'c#', '.net', 'angular', 'vue', 'django', 'flask', 'spring boot',
        'microservices', 'rest api', 'graphql', 'nosql', 'elasticsearch', 'redis',
        'agile', 'scrum', 'jira', 'confluence', 'slack', 'microsoft office',
        'project management', 'leadership', 'communication', 'teamwork'
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in skill_keywords:
        if skill in text_lower:
            found_skills.append(skill)
    
    return found_skills

def detect_skill_gaps(resume_text, job_description):
    resume_skills = set(extract_skills_from_text(resume_text))
    job_skills = set(extract_skills_from_text(job_description))
    
    missing_skills = job_skills - resume_skills
    return list(missing_skills)

# Learning path generator
def generate_learning_path(missing_skills, job_role=None):
    # Role-specific learning priorities and additional skills
    role_priorities = {
        'full stack developer': {
            'priority_skills': ['python', 'javascript', 'react', 'nodejs', 'html', 'css', 'sql', 'mongodb', 'postgresql'],
            'additional_skills': ['git', 'rest api', 'microservices', 'docker', 'aws']
        },
        'data scientist': {
            'priority_skills': ['python', 'machine learning', 'tensorflow', 'pytorch', 'scikit-learn', 'statistics'],
            'additional_skills': ['data analysis', 'data science', 'sql', 'tableau', 'power bi', 'excel']
        },
        'devops engineer': {
            'priority_skills': ['docker', 'kubernetes', 'aws', 'azure', 'linux', 'ci/cd'],
            'additional_skills': ['devops', 'git', 'microservices', 'python', 'bash']
        },
        'frontend developer': {
            'priority_skills': ['html', 'css', 'javascript', 'react', 'angular', 'vue'],
            'additional_skills': ['git', 'responsive design', 'ui/ux', 'typescript']
        },
        'backend developer': {
            'priority_skills': ['python', 'java', 'nodejs', 'sql', 'nosql', 'mongodb', 'postgresql'],
            'additional_skills': ['rest api', 'microservices', 'docker', 'aws', 'git']
        },
        'machine learning engineer': {
            'priority_skills': ['python', 'tensorflow', 'pytorch', 'scikit-learn', 'machine learning', 'deep learning'],
            'additional_skills': ['docker', 'kubernetes', 'aws', 'mlops', 'data engineering']
        }
    }
    
    learning_resources = {
        'python': [
            {'week': 1, 'topic': 'Python Fundamentals - Variables, Data Types, Control Flow', 'resource': 'https://www.coursera.org/learn/python-for-everybody'},
            {'week': 2, 'topic': 'Python Data Structures - Lists, Dictionaries, Sets', 'resource': 'https://www.youtube.com/watch?v=rfscVS0vtbw'},
            {'week': 3, 'topic': 'Object-Oriented Programming in Python', 'resource': 'https://realpython.com/oop-in-python/'},
            {'week': 4, 'topic': 'Python Standard Library and Best Practices', 'resource': 'https://docs.python.org/3/tutorial/'}
        ],
        'javascript': [
            {'week': 1, 'topic': 'JavaScript Fundamentals - ES6+ Features', 'resource': 'https://www.javascript.info/'},
            {'week': 2, 'topic': 'DOM Manipulation and Event Handling', 'resource': 'https://developer.mozilla.org/en-US/docs/Learn/JavaScript'},
            {'week': 3, 'topic': 'Asynchronous JavaScript - Promises, Async/Await', 'resource': 'https://javascript.info/async'},
            {'week': 4, 'topic': 'JavaScript Frameworks and Modern Development', 'resource': 'https://www.youtube.com/watch?v=W6NZfCO5SIk'}
        ],
        'react': [
            {'week': 1, 'topic': 'React Basics - Components, Props, State', 'resource': 'https://reactjs.org/tutorial/tutorial.html'},
            {'week': 2, 'topic': 'React Hooks - useState, useEffect, Custom Hooks', 'resource': 'https://www.youtube.com/watch?v=TNhaISOUy6Q'},
            {'week': 3, 'topic': 'React Router and Navigation', 'resource': 'https://reactrouter.com/'},
            {'week': 4, 'topic': 'State Management with Redux/Context API', 'resource': 'https://redux.js.org/tutorials/fundamentals/part-1-overview-concepts'}
        ],
        'nodejs': [
            {'week': 1, 'topic': 'Node.js Fundamentals - Modules, File System, Events', 'resource': 'https://nodejs.org/en/docs/'},
            {'week': 2, 'topic': 'Express.js Framework - REST APIs, Middleware', 'resource': 'https://expressjs.com/'},
            {'week': 3, 'topic': 'Building RESTful APIs with Node.js', 'resource': 'https://www.youtube.com/watch?v=fgTGADljAeg'},
            {'week': 4, 'topic': 'Authentication and Security in Node.js', 'resource': 'https://www.passportjs.org/'}
        ],
        'sql': [
            {'week': 1, 'topic': 'SQL Basics - SELECT, INSERT, UPDATE, DELETE', 'resource': 'https://www.w3schools.com/sql/'},
            {'week': 2, 'topic': 'Advanced SQL - JOINs, Subqueries, Aggregations', 'resource': 'https://www.coursera.org/learn/sql-for-data-science'},
            {'week': 3, 'topic': 'Database Design and Normalization', 'resource': 'https://www.youtube.com/watch?v=FR4QIeZaPeM'},
            {'week': 4, 'topic': 'SQL Performance Optimization and Indexing', 'resource': 'https://www.use-the-index-luke.com/'}
        ],
        'machine learning': [
            {'week': 1, 'topic': 'Machine Learning Introduction - Supervised vs Unsupervised', 'resource': 'https://www.coursera.org/learn/machine-learning'},
            {'week': 2, 'topic': 'Supervised Learning - Regression, Classification', 'resource': 'https://scikit-learn.org/stable/supervised_learning.html'},
            {'week': 3, 'topic': 'Model Evaluation and Cross-Validation', 'resource': 'https://www.youtube.com/watch?v=1OEoXo_8_xY'},
            {'week': 4, 'topic': 'Deep Learning Fundamentals with TensorFlow', 'resource': 'https://www.coursera.org/learn/deep-learning'}
        ],
        'docker': [
            {'week': 1, 'topic': 'Docker Basics - Images, Containers, Dockerfile', 'resource': 'https://docs.docker.com/get-started/'},
            {'week': 2, 'topic': 'Docker Compose and Multi-Container Applications', 'resource': 'https://www.youtube.com/watch?v=3c-iBn73dDE'},
            {'week': 3, 'topic': 'Docker Networking and Volumes', 'resource': 'https://www.docker.com/101-tutorial'},
            {'week': 4, 'topic': 'Docker in Production - Best Practices and Security', 'resource': 'https://www.udemy.com/course/docker-mastery/'}
        ],
        'aws': [
            {'week': 1, 'topic': 'AWS Cloud Fundamentals - IAM, VPC, Security', 'resource': 'https://aws.amazon.com/training/'},
            {'week': 2, 'topic': 'AWS Compute Services - EC2, Lambda, Elastic Beanstalk', 'resource': 'https://www.youtube.com/watch?v=a9__D53Wsus'},
            {'week': 3, 'topic': 'AWS Storage and Database Services - S3, RDS, DynamoDB', 'resource': 'https://aws.amazon.com/getting-started/'},
            {'week': 4, 'topic': 'AWS DevOps and Serverless Architecture', 'resource': 'https://aws.amazon.com/devops/'}
        ],
        'kubernetes': [
            {'week': 1, 'topic': 'Kubernetes Basics - Pods, Services, Deployments', 'resource': 'https://kubernetes.io/docs/tutorials/'},
            {'week': 2, 'topic': 'Kubernetes Architecture and Components', 'resource': 'https://www.youtube.com/watch?v=X48VuDVv0do'},
            {'week': 3, 'topic': 'Kubernetes Networking and Storage', 'resource': 'https://kubernetes.io/docs/concepts/'},
            {'week': 4, 'topic': 'Kubernetes in Production - Monitoring and Scaling', 'resource': 'https://www.udemy.com/course/kubernetes-for-developers/'}
        ],
        'git': [
            {'week': 1, 'topic': 'Git Fundamentals - Clone, Add, Commit, Push', 'resource': 'https://www.atlassian.com/git/tutorials/'},
            {'week': 2, 'topic': 'Branching and Merging in Git', 'resource': 'https://www.youtube.com/watch?v=Y9XufQdZ7a4'},
            {'week': 3, 'topic': 'Git Workflows - Feature Branches, Pull Requests', 'resource': 'https://www.atlassian.com/git/tutorials/comparing-workflows'},
            {'week': 4, 'topic': 'Advanced Git - Rebase, Cherry-pick, Stash', 'resource': 'https://git-scm.com/book'}
        ],
        'html': [
            {'week': 1, 'topic': 'HTML5 Fundamentals - Semantic Markup, Forms', 'resource': 'https://developer.mozilla.org/en-US/docs/Learn/HTML'},
            {'week': 2, 'topic': 'Advanced HTML5 - Canvas, SVG, Web Components', 'resource': 'https://www.youtube.com/watch?v=kUMe1FH4CHE'},
            {'week': 3, 'topic': 'HTML Accessibility and SEO Best Practices', 'resource': 'https://www.w3.org/WAI/WCAG21/quickref/'}
        ],
        'css': [
            {'week': 1, 'topic': 'CSS3 Fundamentals - Selectors, Box Model, Layout', 'resource': 'https://developer.mozilla.org/en-US/docs/Learn/CSS'},
            {'week': 2, 'topic': 'CSS Grid and Flexbox - Modern Layout Systems', 'resource': 'https://css-tricks.com/snippets/css/complete-guide-grid/'},
            {'week': 3, 'topic': 'CSS Animations and Transitions', 'resource': 'https://www.youtube.com/watch?v=LaARn1CgZbE'},
            {'week': 4, 'topic': 'Responsive Design and Mobile-First CSS', 'resource': 'https://www.w3schools.com/css/css_rwd_intro.asp'}
        ],
        'mongodb': [
            {'week': 1, 'topic': 'MongoDB Basics - Documents, Collections, CRUD Operations', 'resource': 'https://www.mongodb.com/docs/manual/'},
            {'week': 2, 'topic': 'MongoDB Querying and Aggregation Framework', 'resource': 'https://www.mongodb.com/docs/manual/aggregation/'},
            {'week': 3, 'topic': 'MongoDB Indexing and Performance Optimization', 'resource': 'https://www.youtube.com/watch?v=5V5J9hG2SE4'},
            {'week': 4, 'topic': 'MongoDB with Node.js - Mongoose ODM', 'resource': 'https://mongoosejs.com/docs/'}
        ],
        'postgresql': [
            {'week': 1, 'topic': 'PostgreSQL Fundamentals - Data Types, Basic Queries', 'resource': 'https://www.postgresql.org/docs/'},
            {'week': 2, 'topic': 'Advanced PostgreSQL - Functions, Triggers, Stored Procedures', 'resource': 'https://www.postgresql.org/docs/current/plpgsql.html'},
            {'week': 3, 'topic': 'PostgreSQL Performance and Optimization', 'resource': 'https://www.youtube.com/watch?v=2w9Rl3Y3P5k'},
            {'week': 4, 'topic': 'PostgreSQL with Node.js - pg Library and ORMs', 'resource': 'https://node-postgres.com/'}
        ],
        'tensorflow': [
            {'week': 1, 'topic': 'TensorFlow Basics - Tensors, Variables, Operations', 'resource': 'https://www.tensorflow.org/tutorials/'},
            {'week': 2, 'topic': 'Neural Networks with TensorFlow - Dense Layers, Activation Functions', 'resource': 'https://www.coursera.org/learn/introduction-tensorflow'},
            {'week': 3, 'topic': 'TensorFlow for Computer Vision - CNNs, Image Classification', 'resource': 'https://www.youtube.com/watch?v=tPYj3fFJGjk'},
            {'week': 4, 'topic': 'TensorFlow for NLP - RNNs, Transformers', 'resource': 'https://www.tensorflow.org/tutorials/text'}
        ],
        'pytorch': [
            {'week': 1, 'topic': 'PyTorch Fundamentals - Tensors, Autograd, Neural Networks', 'resource': 'https://pytorch.org/tutorials/'},
            {'week': 2, 'topic': 'Deep Learning with PyTorch - CNNs, RNNs, LSTMs', 'resource': 'https://www.coursera.org/learn/deep-neural-networks-with-pytorch'},
            {'week': 3, 'topic': 'PyTorch for Computer Vision - Transfer Learning, Object Detection', 'resource': 'https://www.youtube.com/watch?v=9zhrxE5PQgY'},
            {'week': 4, 'topic': 'PyTorch Lightning and Production Deployment', 'resource': 'https://www.pytorchlightning.ai/'}
        ],
        'azure': [
            {'week': 1, 'topic': 'Azure Fundamentals - Portal, Resource Groups, Subscriptions', 'resource': 'https://docs.microsoft.com/en-us/azure/'},
            {'week': 2, 'topic': 'Azure Compute Services - VMs, App Service, Functions', 'resource': 'https://www.youtube.com/watch?v=I4j2k2Sj2lM'},
            {'week': 3, 'topic': 'Azure Storage and Database Services', 'resource': 'https://azure.microsoft.com/en-us/services/'},
            {'week': 4, 'topic': 'Azure DevOps and CI/CD Pipelines', 'resource': 'https://azure.microsoft.com/en-us/services/devops/'}
        ],
        'microservices': [
            {'week': 1, 'topic': 'Microservices Architecture - Principles and Patterns', 'resource': 'https://microservices.io/'},
            {'week': 2, 'topic': 'Building Microservices with Node.js and Express', 'resource': 'https://www.youtube.com/watch?v=C5-fI_A_z8Y'},
            {'week': 3, 'topic': 'Service Discovery and API Gateway Patterns', 'resource': 'https://www.nginx.com/blog/building-microservices-using-ngix-and-docker/'},
            {'week': 4, 'topic': 'Microservices Testing and Deployment Strategies', 'resource': 'https://martinfowler.com/articles/microservices.html'}
        ],
        'rest api': [
            {'week': 1, 'topic': 'REST API Design Principles - HTTP Methods, Status Codes', 'resource': 'https://restfulapi.net/'},
            {'week': 2, 'topic': 'Building REST APIs with Express.js and Node.js', 'resource': 'https://www.youtube.com/watch?v=fgTGADljAeg'},
            {'week': 3, 'topic': 'API Authentication and Security - JWT, OAuth', 'resource': 'https://jwt.io/'},
            {'week': 4, 'topic': 'API Documentation and Testing - Swagger, Postman', 'resource': 'https://swagger.io/'}
        ],
        'angular': [
            {'week': 1, 'topic': 'Angular Fundamentals - Components, Templates, Data Binding', 'resource': 'https://angular.io/tutorial'},
            {'week': 2, 'topic': 'Angular Services and Dependency Injection', 'resource': 'https://angular.io/guide/architecture-services'},
            {'week': 3, 'topic': 'Angular Routing and Navigation', 'resource': 'https://angular.io/guide/router'},
            {'week': 4, 'topic': 'Angular Forms and Reactive Programming', 'resource': 'https://angular.io/guide/reactive-forms'}
        ],
        'vue': [
            {'week': 1, 'topic': 'Vue.js Fundamentals - Components, Props, Events', 'resource': 'https://vuejs.org/tutorial/'},
            {'week': 2, 'topic': 'Vue Router and State Management with Vuex/Pinia', 'resource': 'https://vuejs.org/guide/scaling-up/routing.html'},
            {'week': 3, 'topic': 'Vue 3 Composition API and Reactivity', 'resource': 'https://www.youtube.com/watch?v=CYPZBK8sO4Y'},
            {'week': 4, 'topic': 'Vue.js Best Practices and Performance', 'resource': 'https://vuejs.org/style-guide/'}
        ],
        'django': [
            {'week': 1, 'topic': 'Django Fundamentals - Models, Views, Templates', 'resource': 'https://docs.djangoproject.com/en/stable/intro/tutorial01/'},
            {'week': 2, 'topic': 'Django ORM and Database Operations', 'resource': 'https://docs.djangoproject.com/en/stable/topics/db/'},
            {'week': 3, 'topic': 'Django REST Framework - Building APIs', 'resource': 'https://www.django-rest-framework.org/tutorial/'},
            {'week': 4, 'topic': 'Django Authentication and Security', 'resource': 'https://docs.djangoproject.com/en/stable/topics/auth/'}
        ],
        'flask': [
            {'week': 1, 'topic': 'Flask Basics - Routes, Templates, Static Files', 'resource': 'https://flask.palletsprojects.com/tutorial/'},
            {'week': 2, 'topic': 'Flask Forms and User Input Handling', 'resource': 'https://flask.palletsprojects.com/en/stable/patterns/wtforms/'},
            {'week': 3, 'topic': 'Flask Database Integration with SQLAlchemy', 'resource': 'https://flask-sqlalchemy.palletsprojects.com/'},
            {'week': 4, 'topic': 'Flask Authentication and REST APIs', 'resource': 'https://flask-jwt-extended.readthedocs.io/'}
        ],
        'java': [
            {'week': 1, 'topic': 'Java Fundamentals - Syntax, OOP, Collections', 'resource': 'https://www.coursera.org/learn/java-programming'},
            {'week': 2, 'topic': 'Java Advanced Topics - Generics, Lambda Expressions', 'resource': 'https://www.youtube.com/watch?v=grEKMHGYyns'},
            {'week': 3, 'topic': 'Spring Boot Framework - REST APIs, Dependency Injection', 'resource': 'https://spring.io/guides/gs/spring-boot/'},
            {'week': 4, 'topic': 'Java Testing and Best Practices', 'resource': 'https://junit.org/junit5/'}
        ],
        'c++': [
            {'week': 1, 'topic': 'C++ Fundamentals - Syntax, Pointers, Memory Management', 'resource': 'https://www.coursera.org/learn/cpp-for-c'},
            {'week': 2, 'topic': 'C++ Standard Library - STL, Containers, Algorithms', 'resource': 'https://www.youtube.com/watch?v=8jLOx1hD3ow'},
            {'week': 3, 'topic': 'C++ Object-Oriented Programming and Design Patterns', 'resource': 'https://www.learncpp.com/'},
            {'week': 4, 'topic': 'Modern C++ - C++11/14/17 Features', 'resource': 'https://github.com/AnthonyCalandra/modern-cpp-features'}
        ],
        'c#': [
            {'week': 1, 'topic': 'C# Fundamentals - Syntax, .NET Framework', 'resource': 'https://dotnet.microsoft.com/learn/csharp'},
            {'week': 2, 'topic': 'C# Object-Oriented Programming and LINQ', 'resource': 'https://www.youtube.com/watch?v=GhQdlIFALjQ'},
            {'week': 3, 'topic': 'ASP.NET Core - Web APIs and MVC', 'resource': 'https://docs.microsoft.com/en-us/aspnet/core/'},
            {'week': 4, 'topic': 'C# Advanced Topics - Async Programming, Entity Framework', 'resource': 'https://docs.microsoft.com/en-us/dotnet/csharp/'}
        ],
        '.net': [
            {'week': 1, 'topic': '.NET Core Fundamentals - CLR, Assemblies, NuGet', 'resource': 'https://dotnet.microsoft.com/learn/dotnet/what-is-dotnet'},
            {'week': 2, 'topic': 'ASP.NET Core Web Development', 'resource': 'https://docs.microsoft.com/en-us/aspnet/core/'},
            {'week': 3, 'topic': '.NET Desktop Applications - WPF, WinForms', 'resource': 'https://github.com/dotnet/wpf'},
            {'week': 4, 'topic': '.NET Microservices and Docker', 'resource': 'https://docs.microsoft.com/en-us/dotnet/architecture/microservices/'}
        ],
        'data analysis': [
            {'week': 1, 'topic': 'Data Analysis Fundamentals - Pandas, NumPy', 'resource': 'https://www.coursera.org/learn/data-analysis-with-python'},
            {'week': 2, 'topic': 'Data Visualization with Matplotlib and Seaborn', 'resource': 'https://www.youtube.com/watch?v=DAQNHzOcO5A'},
            {'week': 3, 'topic': 'Statistical Analysis and Hypothesis Testing', 'resource': 'https://www.khanacademy.org/math/statistics-probability'},
            {'week': 4, 'topic': 'Data Cleaning and Preprocessing Techniques', 'resource': 'https://towardsdatascience.com/data-cleaning-with-python-6ac3b3a8d7b'}
        ],
        'data science': [
            {'week': 1, 'topic': 'Data Science Fundamentals - CRISP-DM Methodology', 'resource': 'https://www.coursera.org/learn/data-science-methodology'},
            {'week': 2, 'topic': 'Exploratory Data Analysis and Feature Engineering', 'resource': 'https://www.youtube.com/watch?v=0Mr9N3t8ZeI'},
            {'week': 3, 'topic': 'Machine Learning for Data Science', 'resource': 'https://www.coursera.org/learn/machine-learning'},
            {'week': 4, 'topic': 'Data Science Project Portfolio Development', 'resource': 'https://www.kaggle.com/learn'}
        ],
        'statistics': [
            {'week': 1, 'topic': 'Descriptive Statistics - Mean, Median, Mode, Standard Deviation', 'resource': 'https://www.khanacademy.org/math/statistics-probability'},
            {'week': 2, 'topic': 'Inferential Statistics - Hypothesis Testing, Confidence Intervals', 'resource': 'https://www.coursera.org/learn/statistics-with-python'},
            {'week': 3, 'topic': 'Probability Theory and Distributions', 'resource': 'https://www.youtube.com/watch?v=uzkc-qNVoOk'},
            {'week': 4, 'topic': 'Statistical Modeling and Regression Analysis', 'resource': 'https://www.statlearning.com/'}
        ],
        'tableau': [
            {'week': 1, 'topic': 'Tableau Fundamentals - Connecting to Data, Basic Visualizations', 'resource': 'https://www.tableau.com/learn/training'},
            {'week': 2, 'topic': 'Advanced Tableau - Calculations, Parameters, Dashboards', 'resource': 'https://www.youtube.com/watch?v=3AK_kp1G0tU'},
            {'week': 3, 'topic': 'Tableau Server and Sharing Visualizations', 'resource': 'https://www.tableau.com/learn/servers'},
            {'week': 4, 'topic': 'Tableau Best Practices and Storytelling with Data', 'resource': 'https://www.tableau.com/learn/whitepapers'}
        ],
        'power bi': [
            {'week': 1, 'topic': 'Power BI Fundamentals - Data Import, Basic Reports', 'resource': 'https://docs.microsoft.com/en-us/power-bi/'},
            {'week': 2, 'topic': 'Power BI DAX and Data Modeling', 'resource': 'https://www.youtube.com/watch?v=0N8k3b3v3aM'},
            {'week': 3, 'topic': 'Power BI Service and Sharing Reports', 'resource': 'https://powerbi.microsoft.com/'},
            {'week': 4, 'topic': 'Advanced Power BI - Power Query, Custom Visuals', 'resource': 'https://www.coursera.org/learn/power-bi'}
        ],
        'excel': [
            {'week': 1, 'topic': 'Excel Fundamentals - Formulas, Functions, Charts', 'resource': 'https://support.microsoft.com/en-us/excel'},
            {'week': 2, 'topic': 'Advanced Excel - PivotTables, VLOOKUP, Data Analysis', 'resource': 'https://www.youtube.com/watch?v=UMFI1hdm9o8'},
            {'week': 3, 'topic': 'Excel Macros and VBA Programming', 'resource': 'https://exceljet.net/vba-tutorial'},
            {'week': 4, 'topic': 'Excel for Business Intelligence and Reporting', 'resource': 'https://www.coursera.org/learn/excel-for-everyone'}
        ],
        'linux': [
            {'week': 1, 'topic': 'Linux Fundamentals - Command Line, File System Navigation', 'resource': 'https://www.linuxfoundation.org/training/introduction-to-linux'},
            {'week': 2, 'topic': 'Linux System Administration - Users, Permissions, Processes', 'resource': 'https://www.youtube.com/watch?v=ROjZy1WpICA'},
            {'week': 3, 'topic': 'Linux Networking and Security', 'resource': 'https://www.coursera.org/learn/linux'},
            {'week': 4, 'topic': 'Shell Scripting and Automation', 'resource': 'https://www.gnu.org/software/bash/manual/'}
        ],
        'ubuntu': [
            {'week': 1, 'topic': 'Ubuntu Installation and Basic Setup', 'resource': 'https://ubuntu.com/tutorials/install-ubuntu-desktop'},
            {'week': 2, 'topic': 'Ubuntu Package Management and Software Installation', 'resource': 'https://help.ubuntu.com/lts/serverguide/apt.html'},
            {'week': 3, 'topic': 'Ubuntu Server Administration', 'resource': 'https://ubuntu.com/server/docs'},
            {'week': 4, 'topic': 'Ubuntu Security and Best Practices', 'resource': 'https://ubuntu.com/security'}
        ],
        'devops': [
            {'week': 1, 'topic': 'DevOps Fundamentals - Culture, Practices, Tools', 'resource': 'https://www.coursera.org/learn/devops-introduction'},
            {'week': 2, 'topic': 'CI/CD Pipelines with Jenkins and GitHub Actions', 'resource': 'https://www.youtube.com/watch?v=scEDHsr3APg'},
            {'week': 3, 'topic': 'Infrastructure as Code - Terraform, Ansible', 'resource': 'https://www.terraform.io/tutorials'},
            {'week': 4, 'topic': 'Monitoring and Logging in DevOps', 'resource': 'https://www.prometheus.io/docs/'}
        ],
        'ci/cd': [
            {'week': 1, 'topic': 'CI/CD Fundamentals - Continuous Integration and Deployment', 'resource': 'https://www.atlassian.com/continuous-delivery'},
            {'week': 2, 'topic': 'GitHub Actions for CI/CD', 'resource': 'https://docs.github.com/en/actions'},
            {'week': 3, 'topic': 'Jenkins Pipelines and Automation', 'resource': 'https://www.jenkins.io/doc/tutorials/'},
            {'week': 4, 'topic': 'CI/CD Best Practices and Security', 'resource': 'https://owasp.org/www-project-devsecops-guideline/'}
        ],
        'agile': [
            {'week': 1, 'topic': 'Agile Fundamentals - Principles, Values, Manifesto', 'resource': 'https://www.atlassian.com/agile'},
            {'week': 2, 'topic': 'Scrum Framework - Roles, Events, Artifacts', 'resource': 'https://www.scrum.org/resources'},
            {'week': 3, 'topic': 'Agile Estimation and Planning Techniques', 'resource': 'https://www.youtube.com/watch?v=Z9flB_h9M4E'},
            {'week': 4, 'topic': 'Agile Tools and Best Practices', 'resource': 'https://www.atlassian.com/agile/tutorial'}
        ],
        'scrum': [
            {'week': 1, 'topic': 'Scrum Fundamentals - Sprint Planning, Daily Standups', 'resource': 'https://www.scrum.org/resources'},
            {'week': 2, 'topic': 'Scrum Roles - Product Owner, Scrum Master, Development Team', 'resource': 'https://www.mountaingoatsoftware.com/agile/scrum'},
            {'week': 3, 'topic': 'Scrum Events and Artifacts', 'resource': 'https://www.youtube.com/watch?v=TRcRe5sE5FQ'},
            {'week': 4, 'topic': 'Advanced Scrum - Scaling, Metrics, Improvement', 'resource': 'https://scrumguides.org/'}
        ],
        'project management': [
            {'week': 1, 'topic': 'Project Management Fundamentals - Planning, Execution, Monitoring', 'resource': 'https://www.coursera.org/learn/project-management'},
            {'week': 2, 'topic': 'Agile Project Management and Scrum', 'resource': 'https://www.pmi.org/about/learn-about-pmi/what-is-project-management'},
            {'week': 3, 'topic': 'Risk Management and Quality Assurance', 'resource': 'https://www.youtube.com/watch?v=SiJ0CjCk9bM'},
            {'week': 4, 'topic': 'Project Management Tools - Jira, Trello, Asana', 'resource': 'https://www.atlassian.com/software/jira'}
        ],
        'leadership': [
            {'week': 1, 'topic': 'Leadership Fundamentals - Vision, Communication, Decision Making', 'resource': 'https://www.coursera.org/learn/leadership'},
            {'week': 2, 'topic': 'Team Building and Motivation', 'resource': 'https://www.youtube.com/watch?v=hY1V12eQ51I'},
            {'week': 3, 'topic': 'Conflict Resolution and Negotiation Skills', 'resource': 'https://hbr.org/topic/leadership'},
            {'week': 4, 'topic': 'Strategic Leadership and Change Management', 'resource': 'https://www.mckinsey.com/capabilities/people-and-organizational-performance/our-insights/leadership'}
        ],
        'communication': [
            {'week': 1, 'topic': 'Effective Communication - Verbal and Non-Verbal Skills', 'resource': 'https://www.coursera.org/learn/business-communication'},
            {'week': 2, 'topic': 'Presentation Skills and Public Speaking', 'resource': 'https://www.youtube.com/watch?v=HAnw168huqA'},
            {'week': 3, 'topic': 'Written Communication - Email, Reports, Documentation', 'resource': 'https://www.purdue.edu/owl/'},
            {'week': 4, 'topic': 'Cross-Cultural Communication and Remote Work', 'resource': 'https://hbr.org/topic/collaboration'}
        ],
        'teamwork': [
            {'week': 1, 'topic': 'Team Dynamics and Collaboration', 'resource': 'https://www.coursera.org/learn/teamwork-skills'},
            {'week': 2, 'topic': 'Effective Team Meetings and Facilitation', 'resource': 'https://www.youtube.com/watch?v=J0A2Ai9lswQ'},
            {'week': 3, 'topic': 'Conflict Resolution in Teams', 'resource': 'https://www.mindtools.com/pages/article/newTMM_79.htm'},
            {'week': 4, 'topic': 'Building High-Performance Teams', 'resource': 'https://hbr.org/topic/teams'}
        ]
    }
    
    # Sort missing skills based on role priorities
    if job_role and job_role.lower() in role_priorities:
        role_config = role_priorities[job_role.lower()]
        priority_skills = role_config['priority_skills']
        additional_skills = role_config['additional_skills']
        
        # Separate skills into priority and additional
        priority_missing = [skill for skill in missing_skills if skill.lower() in priority_skills]
        additional_missing = [skill for skill in missing_skills if skill.lower() in additional_skills]
        other_missing = [skill for skill in missing_skills if skill.lower() not in priority_skills + additional_skills]
        
        # Order: priority skills first, then additional, then others
        ordered_missing_skills = priority_missing + additional_missing + other_missing
    else:
        # If no specific role, maintain original order
        ordered_missing_skills = missing_skills
    
    roadmap = []
    week_counter = 1
    
    for skill in ordered_missing_skills:
        if skill.lower() in learning_resources:
            for resource in learning_resources[skill.lower()]:
                roadmap.append({
                    'skill': skill,
                    'week': week_counter,
                    'topic': resource['topic'],
                    'resource_link': resource['resource']
                })
                week_counter += 1
        else:
            # Generic learning path for skills not in the predefined list
            roadmap.append({
                'skill': skill,
                'week': week_counter,
                'topic': f'Introduction to {skill}',
                'resource_link': f'https://www.google.com/search?q={skill}+tutorial'
            })
            week_counter += 1
    
    return roadmap

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                        (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    job_roles = conn.execute('SELECT * FROM job_roles').fetchall()
    conn.close()
    
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file uploaded', 'error')
            return render_template('analyze.html', job_roles=job_roles)
        
        file = request.files['resume']
        selected_role = request.form['job_role']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return render_template('analyze.html', job_roles=job_roles)
        
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from resume
            if filename.endswith('.pdf'):
                resume_text = extract_text_from_pdf(filepath)
            elif filename.endswith('.docx'):
                resume_text = extract_text_from_docx(filepath)
            else:
                flash('Unsupported file format. Please upload PDF or DOCX', 'error')
                return render_template('analyze.html', job_roles=job_roles)
            
            # Get job description
            conn = get_db_connection()
            job_role = conn.execute('SELECT * FROM job_roles WHERE id = ?', 
                                   (selected_role,)).fetchone()
            conn.close()
            
            if not job_role:
                flash('Invalid job role selected', 'error')
                return render_template('analyze.html', job_roles=job_roles)
            
            # Calculate similarity and detect skill gaps
            similarity_score = calculate_similarity(resume_text, job_role['job_description_text'])
            missing_skills = detect_skill_gaps(resume_text, job_role['job_description_text'])
            
            # Store analysis results
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert resume analysis
            cursor.execute('''
                INSERT INTO user_resumes (user_id, resume_text, selected_role, similarity_score)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], resume_text, job_role['role_name'], similarity_score))
            resume_id = cursor.lastrowid
            
            # Insert skill gaps
            for skill in missing_skills:
                cursor.execute('''
                    INSERT INTO skill_gaps (user_id, missing_skill)
                    VALUES (?, ?)
                ''', (session['user_id'], skill))
            
            conn.commit()
            conn.close()
            
            # Generate learning path
            learning_path = generate_learning_path(missing_skills, job_role['role_name'])
            
            # Store learning path
            conn = get_db_connection()
            cursor = conn.cursor()
            for item in learning_path:
                cursor.execute('''
                    INSERT INTO roadmap (user_id, skill, week, topic, resource_link)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session['user_id'], item['skill'], item['week'], 
                      item['topic'], item['resource_link']))
            conn.commit()
            conn.close()
            
            session['analysis_complete'] = True
            session['similarity_score'] = similarity_score
            session['missing_skills'] = missing_skills
            
            return redirect(url_for('result'))
    
    return render_template('analyze.html', job_roles=job_roles)

@app.route('/result')
def result():
    if 'user_id' not in session or 'analysis_complete' not in session:
        return redirect(url_for('login'))
    
    similarity_score = session.get('similarity_score', 0)
    missing_skills = session.get('missing_skills', [])
    
    return render_template('result.html', 
                         similarity_score=similarity_score,
                         missing_skills=missing_skills)

@app.route('/roadmap')
def roadmap():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    roadmap_items = conn.execute('''
        SELECT * FROM roadmap 
        WHERE user_id = ? 
        ORDER BY week ASC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('roadmap.html', roadmap_items=roadmap_items)

@app.route('/progress_report')
def progress_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get detailed progress data
    roadmap_items = conn.execute('''
        SELECT * FROM roadmap 
        WHERE user_id = ? 
        ORDER BY week ASC
    ''', (session['user_id'],)).fetchall()
    
    # Get skill gaps with completion status
    skill_gaps = conn.execute('''
        SELECT DISTINCT missing_skill FROM skill_gaps 
        WHERE user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    # Get recent analyses
    recent_analyses = conn.execute('''
        SELECT * FROM user_resumes 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    # Calculate progress statistics
    total_items = len(roadmap_items)
    completed_items = len([item for item in roadmap_items if item['completed']])
    
    # Group skills by completion status
    skills_by_status = {}
    for item in roadmap_items:
        skill = item['skill']
        if skill not in skills_by_status:
            skills_by_status[skill] = {'total': 0, 'completed': 0, 'weeks': []}
        
        skills_by_status[skill]['total'] += 1
        skills_by_status[skill]['weeks'].append(item)
        if item['completed']:
            skills_by_status[skill]['completed'] += 1
    
    # Calculate skill completion percentages
    skill_progress = []
    for skill, data in skills_by_status.items():
        completion_rate = (data['completed'] / data['total']) * 100 if data['total'] > 0 else 0
        skill_progress.append({
            'skill': skill,
            'completion_rate': completion_rate,
            'total_weeks': data['total'],
            'completed_weeks': data['completed'],
            'weeks': data['weeks']
        })
    
    # Sort by completion rate
    skill_progress.sort(key=lambda x: x['completion_rate'], reverse=True)
    
    return render_template('progress_report.html',
                         roadmap_items=roadmap_items,
                         skill_progress=skill_progress,
                         total_items=total_items,
                         completed_items=completed_items,
                         progress_percentage=(completed_items / total_items * 100) if total_items > 0 else 0,
                         recent_analyses=recent_analyses)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get user's recent analyses
    recent_analyses = conn.execute('''
        SELECT * FROM user_resumes 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    # Get skill gaps
    skill_gaps = conn.execute('''
        SELECT missing_skill, COUNT(*) as count 
        FROM skill_gaps 
        WHERE user_id = ? 
        GROUP BY missing_skill
    ''', (session['user_id'],)).fetchall()
    
    # Get progress
    total_roadmap_items = conn.execute('''
        SELECT COUNT(*) as count FROM roadmap WHERE user_id = ?
    ''', (session['user_id'],)).fetchone()['count']
    
    completed_items = conn.execute('''
        SELECT COUNT(*) as count FROM roadmap 
        WHERE user_id = ? AND completed = TRUE
    ''', (session['user_id'],)).fetchone()['count']
    
    conn.close()
    
    progress_percentage = (completed_items / total_roadmap_items * 100) if total_roadmap_items > 0 else 0
    
    return render_template('dashboard.html',
                         recent_analyses=recent_analyses,
                         skill_gaps=skill_gaps,
                         progress_percentage=progress_percentage,
                         completed_items=completed_items,
                         total_items=total_roadmap_items)

@app.route('/update_roadmap', methods=['POST'])
def update_roadmap():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.get_json()
    roadmap_id = data.get('roadmap_id')
    completed = data.get('completed', False)
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE roadmap 
        SET completed = ? 
        WHERE id = ? AND user_id = ?
    ''', (completed, roadmap_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    if not os.path.exists('instance'):
        os.makedirs('instance')
    init_db()
    app.run(debug=True)
