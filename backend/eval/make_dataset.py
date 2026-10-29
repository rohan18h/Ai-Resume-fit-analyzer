"""Generate the synthetic evaluation resumes (PDF) and job descriptions (TXT). All people are fictional.

Run from backend/:  python eval/make_dataset.py

The pairs in pairs.json are chosen to cover a spread of fits, but their labels are left empty on purpose:
the team must label them by hand (Section 12). Add your own consented resumes the same way.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

EVAL_DIR = Path(__file__).resolve().parent
WIDTH, HEIGHT = A4
MARGIN = 56

RESUMES: dict[str, dict] = {
    "r01": {
        "name": "Kavya Menon",
        "contact": "kavya.menon@example.com | +91 90011 22334",
        "sections": {
            "SUMMARY": ["Backend developer with 2 years of experience building Python web services and REST APIs."],
            "SKILLS": ["Python, FastAPI, Django, PostgreSQL, Redis, Docker, AWS, Git, Linux, PyTest"],
            "EXPERIENCE": [
                "Software Engineer, Example Fintech (2023 - present)",
                "- Designed REST APIs in FastAPI for a payments dashboard used by 5,000 merchants.",
                "- Modelled PostgreSQL schemas and tuned slow queries, cutting response time by 40%.",
                "- Containerised services with Docker and deployed them to AWS ECS.",
                "- Added Redis caching and wrote PyTest suites for every endpoint.",
            ],
            "EDUCATION": ["B.E. Computer Engineering, Example Institute of Technology, 2023"],
        },
    },
    "r02": {
        "name": "Aditya Rao",
        "contact": "aditya.rao@example.com | +91 90022 33445",
        "sections": {
            "SUMMARY": ["Frontend developer who builds fast, accessible React interfaces."],
            "SKILLS": ["JavaScript, TypeScript, React, Redux, Next.js, HTML, CSS, Tailwind CSS, Jest, Git"],
            "EXPERIENCE": [
                "Frontend Developer, Example Media (2022 - present)",
                "- Rebuilt the news site in React and Next.js, improving Lighthouse scores from 60 to 95.",
                "- Managed shared state with Redux and wrote component tests in Jest.",
                "- Worked with designers on a responsive design system using Tailwind CSS.",
            ],
            "EDUCATION": ["B.Tech Information Technology, Example University, 2022"],
        },
    },
    "r03": {
        "name": "Simran Kaur",
        "contact": "simran.kaur@example.com | +91 90033 44556",
        "sections": {
            "SUMMARY": ["Data analyst who turns sales and marketing data into clear dashboards and decisions."],
            "SKILLS": ["SQL, Excel, Tableau, Power BI, Python, Pandas, Statistics, Data Visualization"],
            "EXPERIENCE": [
                "Data Analyst, Example Retail (2022 - present)",
                "- Wrote SQL queries over 10 million order rows to track weekly revenue and returns.",
                "- Built Tableau and Power BI dashboards used by regional managers.",
                "- Ran A/B test analysis with Python and Pandas and presented results to leadership.",
            ],
            "EDUCATION": ["B.Sc. Statistics, Example College, 2021"],
        },
    },
    "r04": {
        "name": "Harsh Vardhan",
        "contact": "harsh.v@example.com | +91 90044 55667",
        "sections": {
            "SUMMARY": ["Final-year student focused on machine learning and natural language processing."],
            "SKILLS": ["Python, PyTorch, scikit-learn, NLP, Hugging Face, Pandas, NumPy, Git"],
            "PROJECTS": [
                "- Fine-tuned a Hugging Face transformer for customer-support ticket classification (F1 0.89).",
                "- Built a resume parser with spaCy and scikit-learn as a college project.",
                "- Trained a CNN in PyTorch for plant disease detection on 20,000 images.",
            ],
            "EXPERIENCE": ["ML Intern, Example AI Labs (summer 2025): cleaned datasets and ran model experiments."],
            "EDUCATION": ["B.E. Artificial Intelligence and Data Science, Example College, 2026"],
        },
    },
    "r05": {
        "name": "Farhan Sheikh",
        "contact": "farhan.sheikh@example.com | +91 90055 66778",
        "sections": {
            "SUMMARY": ["DevOps engineer who automates infrastructure and keeps deployments boring."],
            "SKILLS": ["Linux, Bash, Docker, Kubernetes, Terraform, Jenkins, GitHub Actions, AWS, Ansible, Nginx"],
            "EXPERIENCE": [
                "DevOps Engineer, Example Cloud Co (2022 - present)",
                "- Managed Kubernetes clusters on AWS running 60 microservices.",
                "- Wrote Terraform modules for networking and databases; reviews done through pull requests.",
                "- Built CI/CD pipelines in Jenkins and GitHub Actions with automatic rollbacks.",
                "- Set up monitoring dashboards and on-call alerts.",
            ],
            "EDUCATION": ["B.E. Electronics and Telecommunication, Example University, 2021"],
        },
    },
    "r06": {
        "name": "Pooja Deshmukh",
        "contact": "pooja.d@example.com | +91 90066 77889",
        "sections": {
            "SUMMARY": ["Java backend developer building microservices for high-traffic systems."],
            "SKILLS": ["Java, Spring Boot, Microservices, MySQL, REST API, JUnit, Docker, Git, Jira"],
            "EXPERIENCE": [
                "Backend Engineer, Example Logistics (2021 - present)",
                "- Built Spring Boot microservices for shipment tracking handling 2 million events a day.",
                "- Designed REST APIs and MySQL schemas; wrote JUnit tests with 80% coverage.",
                "- Worked in Scrum with two-week sprints, tracked in Jira.",
            ],
            "EDUCATION": ["B.E. Computer Engineering, Example Institute, 2021"],
        },
    },
    "r07": {
        "name": "Nikhil Jain",
        "contact": "nikhil.jain@example.com | +91 90077 88990",
        "sections": {
            "SUMMARY": ["Android developer with three published apps on the Play Store."],
            "SKILLS": ["Kotlin, Java, Android, Firebase, REST API, Git"],
            "EXPERIENCE": [
                "Android Developer, Example Apps (2023 - present)",
                "- Built a grocery delivery app in Kotlin with offline support and push notifications.",
                "- Integrated Firebase authentication and REST APIs for orders and payments.",
            ],
            "EDUCATION": ["B.Tech Computer Science, Example University, 2023"],
        },
    },
    "r08": {
        "name": "Rahul Patwardhan",
        "contact": "rahul.p@example.com | +91 90088 99001",
        "sections": {
            "SUMMARY": ["Mechanical engineering graduate interested in product design and manufacturing."],
            "SKILLS": ["AutoCAD, SolidWorks, MATLAB, Excel, Six Sigma, Technical drawing"],
            "EXPERIENCE": [
                "Graduate Engineer Trainee, Example Motors (2024 - present)",
                "- Designed fixtures in SolidWorks for the assembly line, reducing setup time by 15%.",
                "- Analysed defect data in Excel and MATLAB for weekly quality reports.",
            ],
            "EDUCATION": ["B.E. Mechanical Engineering, Example College of Engineering, 2024"],
        },
    },
    "r09": {
        "name": "Tanvi Kulkarni",
        "contact": "tanvi.k@example.com | +91 90099 00112",
        "sections": {
            "SUMMARY": ["QA engineer moving from manual testing to test automation."],
            "SKILLS": ["Manual Testing, Selenium, Python, PyTest, Postman, Jira, Test Automation, SQL"],
            "EXPERIENCE": [
                "QA Engineer, Example Insurance (2022 - present)",
                "- Wrote and ran manual test cases for the policy portal and logged defects in Jira.",
                "- Automated 150 regression tests with Selenium and PyTest.",
                "- Tested REST APIs with Postman collections in every release.",
            ],
            "EDUCATION": ["B.Sc. Computer Science, Example College, 2022"],
        },
    },
    "r10": {
        "name": "Sahil Ansari",
        "contact": "sahil.ansari@example.com | +91 90100 11223",
        "sections": {
            "SUMMARY": ["Full stack MERN developer who enjoys shipping features end to end."],
            "SKILLS": ["JavaScript, MongoDB, Express.js, React, Node.js, REST API, HTML, CSS, Git"],
            "EXPERIENCE": [
                "Full Stack Developer, Example Startup (2023 - present)",
                "- Built a booking platform with React on the frontend and Node.js with Express.js on the backend.",
                "- Designed MongoDB collections and REST endpoints for bookings and payments.",
            ],
            "EDUCATION": ["B.E. Computer Engineering, Example Institute, 2023"],
        },
    },
}

JDS: dict[str, str] = {
    "j01": """Backend Python Developer

About us: Example Payments builds billing software for small businesses across India. Our engineering team of
twelve owns the APIs that power invoicing, payouts and reporting.

Responsibilities:
- Design, build and maintain REST APIs in Python for our billing platform.
- Model data in PostgreSQL and keep queries fast as traffic grows.
- Write automated tests and review pull requests from teammates.
- Package services with Docker and support deployments to the cloud.
- Work with product managers to turn requirements into small, shippable features.
- Investigate production issues and improve logging and monitoring.

Requirements:
- 2+ years of professional experience with Python.
- Experience with FastAPI or Django for building web APIs.
- Strong SQL skills and hands-on experience with PostgreSQL.
- Experience with Docker and Git in a team workflow.
- Good understanding of REST API design and authentication.

Nice to have:
- AWS experience, especially ECS or Lambda.
- Redis or another caching layer.
- Experience with background job queues.
""",
    "j02": """Frontend React Developer

About us: Example Media publishes news and video for millions of readers every month. We care about fast pages
and an experience that works for everyone, on every device.

Responsibilities:
- Build user interfaces in React with reusable, well-tested components.
- Work closely with designers to deliver responsive design across phones, tablets and desktops.
- Improve page speed and Core Web Vitals on our most visited pages.
- Make sure new features meet accessibility standards.
- Write unit tests for components and review code from other developers.

Requirements:
- Strong JavaScript and TypeScript skills.
- 2+ years of professional experience with React and Redux.
- Solid HTML and CSS, including responsive layouts and accessibility.
- Experience working with REST APIs from the frontend.
- Comfortable using Git and taking part in code review.

Nice to have:
- Next.js experience for server-side rendering.
- Testing with Jest.
- Experience with Tailwind CSS or another utility-first CSS framework.
""",
    "j03": """Data Analyst

About us: Example Retail runs 150 stores and an online shop. Our analytics team helps buyers, marketing and store
managers make decisions with data instead of guesswork.

Responsibilities:
- Write SQL queries to answer business questions about sales, stock and customers.
- Build and maintain dashboards and weekly reports for managers.
- Analyse promotions and A/B tests and explain what worked and why.
- Clean and combine data from several sources before analysis.
- Present insights clearly to non-technical teams.

Requirements:
- Excellent SQL skills, including joins and window functions.
- Advanced Excel, including pivot tables and lookups.
- Experience with Tableau or Power BI for data visualization.
- Good understanding of statistics, such as averages, distributions and significance tests.
- Clear written and spoken communication.

Good to have:
- Python with Pandas for data analysis.
- Experience in retail or e-commerce analytics.
""",
    "j04": """Machine Learning Engineer

About us: Example Support AI helps companies answer customer questions faster. We are building machine learning
features that sort, search and summarise millions of support tickets.

Responsibilities:
- Train, evaluate and deploy machine learning models for text problems.
- Work on NLP problems such as text classification, search and summarisation.
- Build data pipelines that prepare training data from raw tickets.
- Turn experiments into reliable services with clear metrics.
- Monitor models in production and retrain them when quality drops.

Requirements:
- Strong Python skills.
- Experience with scikit-learn and PyTorch or TensorFlow.
- Hands-on NLP experience with real text data.
- Good knowledge of statistics and machine learning fundamentals, such as evaluation metrics and overfitting.
- Experience with Pandas and NumPy.

Nice to have:
- Hugging Face transformers and fine-tuning pretrained models.
- Docker and AWS for deploying models.
- Experience with LLMs and prompt engineering.
""",
    "j05": """DevOps Engineer

About us: Example Cloud Co runs a SaaS product used by 2,000 companies. Our platform team keeps it fast, secure
and available around the clock.

Responsibilities:
- Operate Kubernetes clusters and container workloads in production.
- Automate infrastructure as code for networks, databases and clusters.
- Build and maintain CI/CD pipelines for more than forty services.
- Improve monitoring, alerting and on-call runbooks.
- Help developers ship safely with good defaults and clear documentation.

Requirements:
- Strong Linux and Bash skills.
- Production experience with Docker and Kubernetes.
- Terraform for infrastructure as code.
- Experience with AWS services such as EC2, RDS and IAM.
- CI/CD with Jenkins or GitHub Actions.

Nice to have:
- Ansible for configuration management.
- Monitoring and alerting experience with Prometheus or similar tools.
- Nginx configuration and troubleshooting.
""",
    "j06": """Java Backend Developer

About us: Example Logistics moves parcels for online shops across the country. Our platform tracks every shipment
in real time and handles millions of events a day.

Responsibilities:
- Build and maintain Spring Boot microservices for shipment tracking.
- Design REST APIs and database schemas that scale.
- Write unit tests and take part in code review.
- Work in an agile team with two-week sprints.
- Improve the performance and reliability of existing services.

Requirements:
- 3+ years of professional Java experience.
- Strong Spring Boot and microservices experience.
- Good SQL skills with MySQL or PostgreSQL.
- Unit testing with JUnit.
- Understanding of REST API design.

Nice to have:
- Docker and Kubernetes.
- Experience with Jira and Scrum.
- Knowledge of design patterns and system design.
""",
    "j07": """QA Automation Engineer

About us: Example Insurance sells policies online and through partners. We release every two weeks and want each
release to be safe without long manual test cycles.

Responsibilities:
- Design and maintain automated UI and API tests.
- Run regression suites before every release and report the results.
- Report, track and verify defects with developers.
- Review requirements early to find gaps before development starts.
- Help the team improve test coverage over time.

Requirements:
- Experience with Selenium for test automation.
- Programming skills in Python or Java.
- API testing with Postman.
- Good understanding of manual testing practices and writing test cases.
- Basic SQL to check data in the database.

Nice to have:
- Jenkins or other CI/CD tools.
- Jira for defect tracking.
- Experience with PyTest or JUnit.
""",
    "j08": """Android Developer

About us: Example Grocer delivers groceries in under thirty minutes in five cities. Our customer app is used by
thousands of people every day.

Responsibilities:
- Develop new features for our Android app.
- Integrate with REST APIs and handle offline data.
- Fix bugs and improve app start-up time and battery use.
- Work with designers and backend engineers on new features.
- Release updates to the Play Store every two weeks.

Requirements:
- Strong Kotlin skills.
- 2+ years of Android development.
- Experience consuming REST APIs.
- Firebase experience, including authentication and push notifications.
- Comfortable with Git.

Nice to have:
- Java.
- Unit testing for Android apps.
""",
}

# (pair id, resume, job description, factual note). Labels are filled in by the team, not here.
PAIRS: list[tuple[str, str, str, str]] = [
    ("p01", "r01", "j01", "Python backend resume vs Python backend JD"),
    ("p02", "r02", "j02", "React frontend resume vs React frontend JD"),
    ("p03", "r03", "j03", "Data analyst resume vs data analyst JD"),
    ("p04", "r04", "j04", "ML student resume vs ML engineer JD"),
    ("p05", "r05", "j05", "DevOps resume vs DevOps JD"),
    ("p06", "r06", "j06", "Java backend resume vs Java backend JD"),
    ("p07", "r09", "j07", "QA resume vs QA automation JD"),
    ("p08", "r07", "j08", "Android resume vs Android JD"),
    ("p09", "r10", "j02", "MERN full stack resume vs React frontend JD"),
    ("p10", "r10", "j01", "MERN full stack resume vs Python backend JD"),
    ("p11", "r04", "j03", "ML student resume vs data analyst JD"),
    ("p12", "r06", "j01", "Java backend resume vs Python backend JD"),
    ("p13", "r08", "j01", "Mechanical engineering resume vs Python backend JD"),
    ("p14", "r08", "j04", "Mechanical engineering resume vs ML engineer JD"),
    ("p15", "r03", "j05", "Data analyst resume vs DevOps JD"),
    ("p16", "r02", "j05", "React frontend resume vs DevOps JD"),
]


def write_resume(path: Path, resume: dict) -> None:
    canvas = Canvas(str(path), pagesize=A4, invariant=True)  # same bytes on every run
    canvas.setTitle(path.name)
    y = HEIGHT - 60
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(MARGIN, y, resume["name"])
    y -= 18
    canvas.setFont("Helvetica", 9)
    canvas.drawString(MARGIN, y, resume["contact"])
    y -= 26
    for title, lines in resume["sections"].items():
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(MARGIN, y, title)
        y -= 18
        canvas.setFont("Helvetica", 10)
        for line in lines:
            for part in simpleSplit(line, "Helvetica", 10, WIDTH - 2 * MARGIN):
                canvas.drawString(MARGIN, y, part)
                y -= 14
        y -= 8
    canvas.save()


def main() -> None:
    import json

    (EVAL_DIR / "resumes").mkdir(exist_ok=True)
    (EVAL_DIR / "jds").mkdir(exist_ok=True)
    for key, resume in RESUMES.items():
        write_resume(EVAL_DIR / "resumes" / f"{key}.pdf", resume)
    for key, text in JDS.items():
        (EVAL_DIR / "jds" / f"{key}.txt").write_text(text, encoding="utf-8", newline="\n")

    pairs_path = EVAL_DIR / "pairs.json"
    existing = {}
    if pairs_path.exists():  # keep labels the team has already entered
        existing = {p["id"]: p for p in json.loads(pairs_path.read_text(encoding="utf-8"))}
    pairs = [
        {
            "id": pair_id,
            "resume_file": f"resumes/{resume}.pdf",
            "jd_file": f"jds/{jd}.txt",
            "label": existing.get(pair_id, {}).get("label"),
            "notes": note,
        }
        for pair_id, resume, jd, note in PAIRS
    ]
    pairs_path.write_text(json.dumps(pairs, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(RESUMES)} resumes, {len(JDS)} job descriptions and {len(pairs)} pairs to {EVAL_DIR}")


if __name__ == "__main__":
    main()
