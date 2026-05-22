# AI-Skill-Gap-Analysis-System
# Skill Gap Analyzer and Recommendation System

A Flask-based web application that analyzes resumes against job role requirements using TF-IDF vectorization and cosine similarity to identify skill gaps and generate personalized learning paths.

## Features

- **Resume Analysis**: Upload PDF/DOCX resumes for analysis
- **TF-IDF Vectorization**: Uses scikit-learn for text vectorization
- **Cosine Similarity**: Calculates similarity scores between resumes and job descriptions
- **Skill Gap Detection**: Identifies missing skills from job requirements
- **Personalized Learning Paths**: Generates week-by-week roadmaps with recommended resources
- **Progress Tracking**: Monitor learning progress and completed skills
- **User Authentication**: Secure login/registration system

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **NLP Libraries**: scikit-learn, nltk
- **Resume Parsing**: PyPDF2, python-docx
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup Instructions

1. **Clone or download the project** to your local directory

2. **Navigate to the project directory**:
   ```bash
   cd skill_gap_analyzer
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Initialize the database**:
   ```bash
   python init_data.py
   ```

6. **Run the application**:
   ```bash
   python app.py
   ```

7. **Access the application**:
   Open your web browser and go to `http://127.0.0.1:5000`

## Usage

### 1. Register/Login
- Create a new account or login with existing credentials
- Passwords must be at least 6 characters long

### 2. Analyze Resume
- Select your target job role from the dropdown
- Upload your resume (PDF or DOCX format)
- Click "Analyze My Skills" to process

### 3. View Results
- See your resume-job match score (percentage)
- Review detected skill gaps
- Get personalized recommendations

### 4. Follow Learning Path
- Access your week-by-week learning roadmap
- Mark completed items to track progress
- Click resource links for learning materials

### 5. Track Progress
- Monitor overall learning progress on the dashboard
- View recent analyses and skill gap history
- Track completed vs remaining learning items

## Project Structure

```
skill_gap_analyzer/
├── app.py                 # Main Flask application
├── init_data.py          # Database initialization with sample job roles
├── requirements.txt      # Python dependencies
├── README.md            # Project documentation
├── instance/            # SQLite database directory
│   └── skill_gap.db    # Application database
├── static/             # Static files
│   ├── css/
│   │   └── style.css   # Custom styles
│   ├── js/
│   │   └── script.js   # Custom JavaScript
│   └── uploads/        # Resume uploads directory
└── templates/          # HTML templates
    ├── base.html       # Base template
    ├── login.html      # Login page
    ├── register.html   # Registration page
    ├── analyze.html    # Resume upload page
    ├── result.html     # Analysis results page
    ├── roadmap.html    # Learning path page
    └── dashboard.html  # User dashboard
```

## Database Schema

### Tables

1. **users**: User accounts and authentication
2. **job_roles**: Available job positions and descriptions
3. **user_resumes**: Resume analysis results
4. **skill_gaps**: Detected missing skills
5. **roadmap**: Personalized learning path items

## Algorithm Details

### TF-IDF Vectorization
- Text preprocessing: lowercase, remove special characters, tokenize, remove stopwords
- TF-IDF vectorizer converts text to numerical vectors
- Captures term importance across documents

### Cosine Similarity
- Measures angle between resume and job description vectors
- Returns similarity score between 0 (no match) and 1 (perfect match)
- Used to rank resume-job compatibility

### Skill Gap Detection
- Extracts skill keywords from job descriptions
- Compares with skills found in resume text
- Identifies missing skills for targeted learning

### Learning Path Generation
- Maps missing skills to structured learning resources
- Provides week-by-week progression
- Includes course links and tutorial recommendations

## Sample Job Roles

The system includes 6 pre-configured job roles:
1. Full Stack Developer
2. Data Scientist
3. DevOps Engineer
4. Frontend Developer
5. Backend Developer
6. Machine Learning Engineer

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **NLTK Download Errors**:
   - The application automatically downloads required NLTK data
   - If errors occur, manually download: `python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"`

2. **File Upload Issues**:
   - Ensure uploads directory exists and is writable
   - Check file size limit (10MB max)
   - Supported formats: PDF, DOCX

3. **Database Issues**:
   - Ensure instance directory exists
   - Run `init_data.py` to initialize database
   - Check file permissions

4. **Port Conflicts**:
   - Default port is 5000
   - Change in app.py if needed: `app.run(debug=True, port=8080)`

## License

This project is for educational purposes. Feel free to use and modify according to your needs.

## Support

For issues and questions, please check the troubleshooting section or create an issue in the repository.
