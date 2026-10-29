"""Generate the parser test PDFs in this folder. All people and details are fictional.

Run from backend/:  python tests/fixtures/make_fixtures.py

Readable fixtures (Objective 1 measure: at least 9 of these 10 extract correctly):
    sample_resume_backend.pdf   single column (also a sample resume for trying the app)
    sample_resume_frontend.pdf  two columns (also a sample resume for trying the app)
    sidebar_layout.pdf          narrow left sidebar + wide main column
    with_table.pdf              skills in a ruled table
    with_image.pdf              photo-like image next to the text
    six_pages.pdf               6 pages (the API rejects it later, but the parser must read it)
    header_footer.pdf           repeated header, footer and page numbers on 3 pages
    special_tokens.pdf          C++, C#, Node.js, .NET, CI/CD and unusual bullet glyphs
    multi_font.pdf              several font families and sizes
    data_analyst_resume.pdf     all-caps headings, numbers, percentages, date ranges

Unreadable fixtures:
    scanned.pdf     a page that is only an image of text
    blank.pdf       a valid PDF with an empty page
    truncated.pdf   starts with %PDF but the rest is cut off
    corrupt.pdf     a text file renamed to .pdf

ATS fixtures (Step 8):
    ats_good_resume.pdf  passes all 10 checks (embedded Arial, so bullets are real Unicode characters)
    ats_bad_resume.pdf   two columns, a table, icons and star ratings, many fonts (the demo's "bad resume")
    image_page.pdf       page 1 is text, page 2 is only an image of text
    many_fonts.pdf       five font families
    decorative.pdf       star ratings and icon symbols
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table, TableStyle

OUT = Path(__file__).resolve().parent
WIDTH, HEIGHT = A4
WINDOWS_FONTS = Path("C:/Windows/Fonts")


def new_canvas(name: str) -> Canvas:
    canvas = Canvas(str(OUT / name), pagesize=A4, invariant=True)  # same bytes on every run
    canvas.setTitle(name)
    canvas.setAuthor("Resume Fit Analyzer test fixtures")
    return canvas


def write_lines(canvas: Canvas, x: float, y: float, lines: list[str], font: str = "Helvetica",
                size: float = 10, leading: float = 14) -> float:
    """Draw lines top-down starting at y (reportlab origin is bottom-left). Returns the next y."""
    canvas.setFont(font, size)
    for line in lines:
        canvas.drawString(x, y, line)
        y -= leading
    return y


def heading(canvas: Canvas, x: float, y: float, text: str, size: float = 12) -> float:
    canvas.setFont("Helvetica-Bold", size)
    canvas.drawString(x, y, text)
    return y - size - 6


# ---------------------------------------------------------------------------
# Readable fixtures
# ---------------------------------------------------------------------------


def sample_resume_backend() -> None:
    c = new_canvas("sample_resume_backend.pdf")
    x, y = 56, HEIGHT - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, "Asha Verma")
    y = write_lines(c, x, y - 18, ["asha.verma@example.com | +91 98765 43210 | linkedin.com/in/ashaverma-demo"], size=9)
    y -= 8
    y = heading(c, x, y, "SUMMARY")
    y = write_lines(c, x, y, [
        "Backend developer with two years of experience building REST APIs in Python.",
        "Interested in clean API design, databases and cloud deployment.",
    ])
    y -= 8
    y = heading(c, x, y, "SKILLS")
    y = write_lines(c, x, y, [
        "Languages: Python, SQL, JavaScript",
        "Frameworks: FastAPI, Flask, Django",
        "Tools: Git, Docker, PostgreSQL, Redis, Linux, Postman",
    ])
    y -= 8
    y = heading(c, x, y, "EXPERIENCE")
    y = write_lines(c, x, y, ["Software Engineer Intern, Example Tech Pvt Ltd (Jun 2024 - Dec 2024)"], font="Helvetica-Bold")
    y = write_lines(c, x, y, [
        "\u2022 Built REST APIs with FastAPI and PostgreSQL for an internal inventory tool.",
        "\u2022 Wrote unit tests with PyTest and raised coverage from 40% to 85%.",
        "\u2022 Packaged services with Docker and deployed them on a Linux server.",
    ])
    y -= 8
    y = heading(c, x, y, "PROJECTS")
    y = write_lines(c, x, y, [
        "\u2022 Library Management API: Flask, SQLite and JWT authentication.",
        "\u2022 Chat server using WebSockets and Redis pub/sub.",
    ])
    y -= 8
    y = heading(c, x, y, "EDUCATION")
    write_lines(c, x, y, [
        "Bachelor of Engineering in Computer Engineering, Example Institute of Technology (2022 - 2026)",
        "CGPA: 8.4 / 10",
    ])
    c.save()


def _two_column(name: str, split_x: float, left: list[tuple[str, list[str]]], right: list[tuple[str, list[str]]],
                person: str, contact: str) -> None:
    c = new_canvas(name)
    margin = 50
    c.setFont("Helvetica-Bold", 20)
    c.drawString(margin, HEIGHT - 60, person)
    c.setFont("Helvetica", 9)
    c.drawString(margin, HEIGHT - 78, contact)
    c.setStrokeColor(colors.lightgrey)
    c.line(margin, HEIGHT - 88, WIDTH - margin, HEIGHT - 88)

    y = HEIGHT - 112
    for title, lines in left:
        y = heading(c, margin, y, title, size=11)
        y = write_lines(c, margin, y, lines, size=9.5, leading=13) - 10

    y = HEIGHT - 112
    for title, lines in right:
        y = heading(c, split_x + 24, y, title, size=11)
        y = write_lines(c, split_x + 24, y, lines, size=9.5, leading=13) - 10
    c.save()


def sample_resume_frontend() -> None:
    _two_column(
        "sample_resume_frontend.pdf",
        split_x=WIDTH * 0.42,
        person="Rohit Kulkarni",
        contact="rohit.k@example.com  |  +91 91234 56780  |  github.com/rohit-demo",
        left=[
            ("SKILLS", ["JavaScript", "TypeScript", "React", "Redux", "HTML", "CSS", "Tailwind CSS", "Jest", "Git"]),
            ("EDUCATION", ["B.E. Computer Engineering", "Example College of Engineering", "2021 - 2025"]),
            ("CERTIFICATIONS", ["Responsive Web Design", "JavaScript Algorithms"]),
        ],
        right=[
            ("EXPERIENCE", [
                "Frontend Developer Intern, Demo Labs",
                "Developed a React dashboard used by",
                "200 staff members to track orders.",
                "Improved page load time by 35% with",
                "code splitting and lazy loading.",
            ]),
            ("PROJECTS", [
                "Weather App: React and a public weather",
                "API with responsive design and charts.",
                "Portfolio site built with Vite, deployed",
                "on Vercel with GitHub Actions.",
            ]),
        ],
    )


def sidebar_layout() -> None:
    _two_column(
        "sidebar_layout.pdf",
        split_x=170,
        person="Neha Joshi",
        contact="neha.joshi@example.com  |  +91 99887 76655",
        left=[
            ("CONTACT", ["Pune, India", "Open to relocate"]),
            ("SKILLS", ["Java", "Spring Boot", "MySQL", "Kafka", "AWS", "Kubernetes", "Jenkins"]),
            ("LANGUAGES", ["English", "Hindi", "Marathi"]),
        ],
        right=[
            ("SUMMARY", [
                "Java developer who enjoys building reliable backend services",
                "and automating deployments for distributed systems.",
            ]),
            ("EXPERIENCE", [
                "Associate Engineer, Sample Systems (2023 - present)",
                "Designed microservices in Spring Boot that process payment",
                "events from Kafka topics for over one million users.",
                "Set up Jenkins pipelines that deploy containers to Kubernetes.",
            ]),
            ("EDUCATION", ["B.Tech Information Technology, Example University, 2023"]),
        ],
    )


def with_table() -> None:
    c = new_canvas("with_table.pdf")
    x, y = 56, HEIGHT - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, "Karan Shah")
    y = write_lines(c, x, y - 18, ["karan.shah@example.com"], size=9) - 8
    y = heading(c, x, y, "SUMMARY")
    y = write_lines(c, x, y, [
        "Cloud and DevOps enthusiast with hands-on experience in containers and CI/CD.",
        "Comfortable with Linux administration and scripting in Bash and Python.",
    ]) - 8
    y = heading(c, x, y, "TECHNICAL SKILLS")
    data = [
        ["Skill", "Level", "Years"],
        ["Docker", "Advanced", "3"],
        ["Kubernetes", "Intermediate", "2"],
        ["Terraform", "Intermediate", "1"],
        ["Python", "Advanced", "4"],
    ]
    table = Table(data, colWidths=[160, 120, 60])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    _, table_height = table.wrapOn(c, WIDTH, HEIGHT)
    table.drawOn(c, x, y - table_height + 10)
    y -= table_height + 16
    y = heading(c, x, y, "EXPERIENCE")
    y = write_lines(c, x, y, [
        "DevOps Intern, Example Cloud Services (2024)",
        "\u2022 Automated infrastructure on AWS with Terraform modules.",
        "\u2022 Reduced build times by 30% by caching Docker layers in GitHub Actions.",
    ]) - 8
    y = heading(c, x, y, "EDUCATION")
    write_lines(c, x, y, ["B.E. Computer Engineering, Example Institute (2021 - 2025)"])
    c.save()


def _photo_png() -> ImageReader:
    image = Image.new("RGB", (240, 300), (180, 200, 220))
    draw = ImageDraw.Draw(image)
    draw.ellipse((70, 40, 170, 140), fill=(120, 140, 160))
    draw.rectangle((40, 160, 200, 300), fill=(120, 140, 160))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def with_image() -> None:
    c = new_canvas("with_image.pdf")
    x, y = 56, HEIGHT - 60
    c.drawImage(_photo_png(), WIDTH - 56 - 90, HEIGHT - 50 - 112, width=90, height=112)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, "Priya Nair")
    y = write_lines(c, x, y - 18, ["priya.nair@example.com | +91 90000 11111"], size=9) - 8
    y = heading(c, x, y, "PROFILE")
    y = write_lines(c, x, y, [
        "Machine learning student focused on NLP and computer vision projects.",
        "Experienced with Pandas, NumPy, scikit-learn and PyTorch.",
    ]) - 30
    y = heading(c, x, y, "PROJECTS")
    y = write_lines(c, x, y, [
        "\u2022 Fake news classifier using TF-IDF features and logistic regression (91% accuracy).",
        "\u2022 Image caption generator with a CNN encoder and an LSTM decoder in PyTorch.",
        "\u2022 Sales forecasting dashboard in Power BI for a college fest.",
    ]) - 8
    y = heading(c, x, y, "EDUCATION")
    write_lines(c, x, y, ["B.E. Artificial Intelligence and Data Science, Example College (2022 - 2026)"])
    c.save()


def six_pages() -> None:
    c = new_canvas("six_pages.pdf")
    for number in range(1, 7):
        y = HEIGHT - 70
        if number == 1:
            c.setFont("Helvetica-Bold", 18)
            c.drawString(56, y, "Vikram Rao")
            y -= 30
        y = heading(c, 56, y, f"Project {number}: Inventory Module Version {number}")
        write_lines(c, 56, y, [
            f"Worked on release {number} of a warehouse system written in Java and Spring Boot.",
            "Added REST endpoints, wrote JUnit tests and reviewed code from two teammates.",
            "Tracked tasks in Jira and followed Scrum with two-week sprints.",
        ])
        c.showPage()
    c.save()


def header_footer() -> None:
    c = new_canvas("header_footer.pdf")
    sections = [
        ("EXPERIENCE", [
            "Data Engineer Intern, Example Analytics (2024)",
            "\u2022 Built ETL jobs in Python and Apache Spark that load sales data into PostgreSQL.",
            "\u2022 Scheduled pipelines and monitored failures with simple alerting scripts.",
        ]),
        ("PROJECTS", [
            "\u2022 Movie recommendation engine using collaborative filtering in Pandas.",
            "\u2022 Real-time tweet sentiment tracker using Kafka and a Flask dashboard.",
        ]),
        ("EDUCATION", [
            "B.E. Computer Engineering, Example Institute of Technology (2021 - 2025)",
            "Relevant courses: DBMS, Operating Systems, Computer Networks, Statistics.",
        ]),
    ]
    for page, (title, lines) in enumerate(sections, start=1):
        c.setFont("Helvetica", 8)
        c.drawString(56, HEIGHT - 30, "Meera Iyer - Resume - Confidential")
        c.drawRightString(WIDTH - 56, 28, f"Page {page} of {len(sections)}")
        y = heading(c, 56, HEIGHT - 90, title)
        write_lines(c, 56, y, lines + ["Additional details are available on request for this section."])
        c.showPage()
    c.save()


def special_tokens() -> None:
    pdfmetrics.registerFont(TTFont("SegoeSymbol", str(WINDOWS_FONTS / "seguisym.ttf")))
    c = new_canvas("special_tokens.pdf")
    x, y = 56, HEIGHT - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, "Arjun Desai")
    y -= 34
    y = heading(c, x, y, "SKILLS")
    y = write_lines(c, x, y, [
        "C++, C#, Node.js, .NET, ASP.NET, CI/CD, Socket.IO, Vue.js",
        "Python \u00b7 Go \u00b7 Rust \u00b7 Bash",
    ]) - 8
    y = heading(c, x, y, "EXPERIENCE")
    bullets = ["\u25cf", "\u25aa", "\u27a2"]
    items = [
        "Wrote a game engine module in C++ with multithreading.",
        "Built Windows tools in C# on .NET 8 with unit tests.",
        "Maintained Node.js services and their CI/CD pipelines.",
    ]
    for bullet, item in zip(bullets, items):
        c.setFont("SegoeSymbol", 10)
        c.drawString(x, y, bullet)
        c.setFont("Helvetica", 10)
        c.drawString(x + 14, y, item)
        y -= 14
    y -= 8
    y = heading(c, x, y, "EDUCATION")
    write_lines(c, x, y, ["B.E. Computer Engineering, Example Institute of Technology (2021 - 2025)"])
    c.save()


def multi_font() -> None:
    c = new_canvas("multi_font.pdf")
    x, y = 56, HEIGHT - 60
    c.setFont("Times-Bold", 22)
    c.drawString(x, y, "Sneha Patil")
    y = write_lines(c, x, y - 20, ["sneha.patil@example.com"], font="Courier", size=9) - 8
    y = heading(c, x, y, "SUMMARY")
    y = write_lines(c, x, y, [
        "Full stack developer who likes TypeScript, Next.js and well-designed databases.",
        "Enjoys writing technical documentation and mentoring juniors.",
    ], font="Times-Roman", size=11) - 8
    y = heading(c, x, y, "EXPERIENCE")
    y = write_lines(c, x, y, [
        "Full Stack Intern, Sample Software (2024)",
        "Built a Next.js storefront backed by a GraphQL API and MongoDB.",
        "Added Cypress end-to-end tests for the checkout flow.",
    ], font="Courier", size=9.5) - 8
    y = heading(c, x, y, "EDUCATION")
    write_lines(c, x, y, ["B.Tech Computer Science, Example University (2021 - 2025)"], font="Helvetica-Oblique")
    c.save()


def data_analyst_resume() -> None:
    c = new_canvas("data_analyst_resume.pdf")
    x, y = 56, HEIGHT - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, "Ananya Gupta")
    y = write_lines(c, x, y - 18, ["ananya.g@example.com | (+91) 98111-22233"], size=9) - 8
    y = heading(c, x, y, "PROFESSIONAL SUMMARY")
    y = write_lines(c, x, y, [
        "Data analyst with strong Excel, SQL and Tableau skills and a background in statistics.",
    ]) - 8
    y = heading(c, x, y, "WORK HISTORY")
    y = write_lines(c, x, y, [
        "Junior Data Analyst, Example Retail Ltd. (Jan 2023 - Mar 2025)",
        "- Cleaned and analysed 1.2 million sales records with SQL and Pandas.",
        "- Built 12 Tableau dashboards; weekly reporting time fell by 60%.",
        "- Ran A/B tests and presented results to the marketing team.",
    ]) - 8
    y = heading(c, x, y, "EDUCATION")
    write_lines(c, x, y, ["B.Sc. Statistics, Example College (2019 - 2022), 78%"])
    c.save()


# ---------------------------------------------------------------------------
# Unreadable fixtures
# ---------------------------------------------------------------------------


def scanned() -> None:
    image = Image.new("L", (1240, 1754), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(WINDOWS_FONTS / "arial.ttf"), 34)
    lines = ["Scanned Resume", "", "Skills: Python, SQL, Excel", "Experience: Data entry operator, 2021 - 2024",
             "Education: B.Com, Example College"]
    for index, line in enumerate(lines):
        draw.text((100, 120 + index * 60), line, fill=0, font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    c = new_canvas("scanned.pdf")
    c.drawImage(ImageReader(buffer), 0, 0, width=WIDTH, height=HEIGHT)
    c.save()


def blank() -> None:
    c = new_canvas("blank.pdf")
    c.showPage()
    c.save()


def truncated() -> None:
    data = (OUT / "sample_resume_backend.pdf").read_bytes()
    (OUT / "truncated.pdf").write_bytes(data[:400])


def corrupt() -> None:
    (OUT / "corrupt.pdf").write_text("This is a plain text file that was renamed to .pdf.\n" * 10, encoding="utf-8")


# ---------------------------------------------------------------------------
# ATS fixtures
# ---------------------------------------------------------------------------


def register_ttf(name: str, filename: str) -> str:
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, str(WINDOWS_FONTS / filename)))
    return name


def _text_png(lines: list[str], size: tuple[int, int] = (1240, 1754), font_px: int = 34) -> ImageReader:
    image = Image.new("L", size, 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(WINDOWS_FONTS / "arial.ttf"), font_px)
    for index, line in enumerate(lines):
        draw.text((60, 60 + index * (font_px + 20)), line, fill=0, font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def ats_good_resume() -> None:
    arial, arial_bold = register_ttf("ArialTTF", "arial.ttf"), register_ttf("ArialBoldTTF", "arialbd.ttf")
    c = new_canvas("ats_good_resume.pdf")
    x, y = 56, HEIGHT - 60
    c.setFont(arial_bold, 18)
    c.drawString(x, y, "Divya Shetty")
    y = write_lines(c, x, y - 18, ["divya.shetty@example.com | +91 98200 12345 | Pune"], font=arial, size=9) - 8
    sections = [
        ("SUMMARY", ["Software engineer with two years of experience building web APIs and data tools in Python."]),
        ("SKILLS", ["Python, FastAPI, Django, PostgreSQL, Docker, Git, Linux, REST API, PyTest"]),
        ("EXPERIENCE", [
            "Software Engineer, Example Analytics (2023 - present)",
            "• Built REST APIs in FastAPI that serve reports to 3,000 customers.",
            "• Moved nightly jobs into Docker containers and cut failures by half.",
            "• Wrote PyTest suites and reviewed code for a team of five.",
        ]),
        ("PROJECTS", [
            "• Expense tracker: Django and PostgreSQL with user authentication.",
            "• Log analyser: Python command-line tool that summarises server logs.",
        ]),
        ("EDUCATION", ["B.E. Computer Engineering, Example Institute of Technology (2019 - 2023)"]),
    ]
    for title, lines in sections:
        c.setFont(arial_bold, 12)
        c.drawString(x, y, title)
        y = write_lines(c, x, y - 18, lines, font=arial, size=10) - 8
    c.save()


def ats_bad_resume() -> None:
    symbols = register_ttf("SegoeSymbol", "seguisym.ttf")
    georgia, verdana = register_ttf("GeorgiaTTF", "georgia.ttf"), register_ttf("VerdanaTTF", "verdana.ttf")
    c = new_canvas("ats_bad_resume.pdf")
    c.setFont(georgia, 20)
    c.drawString(50, HEIGHT - 60, "Manish Gupta")
    c.setFont(symbols, 10)
    c.drawString(50, HEIGHT - 80, "✉ manish.g@example.com    ☎ call me    ⌂ Mumbai")

    split = WIDTH * 0.38
    y = HEIGHT - 120
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "MY TOOLBOX")
    y -= 18
    for skill, stars in [("Java", 5), ("Spring", 4), ("MySQL", 4), ("Docker", 3), ("AWS", 2)]:
        c.setFont(verdana, 9.5)
        c.drawString(50, y, skill)
        c.setFont(symbols, 9.5)
        c.drawString(120, y, "★" * stars + "☆" * (5 - stars))
        y -= 15
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "HOBBIES")
    write_lines(c, 50, y - 18, ["Chess", "Cricket", "Photography", "Travel", "Reading"], font="Times-Roman", size=10)

    y = HEIGHT - 120
    c.setFont("Helvetica-Bold", 11)
    c.drawString(split + 20, y, "WHERE I HAVE WORKED")
    y -= 18
    for line in ["Java Developer, Example Bank (2022 - present)", "Built Spring services for loan approvals",
                 "and moved reports to a MySQL warehouse.", "Mentored two interns in my second year."]:
        c.setFont(symbols, 10)
        c.drawString(split + 20, y, "➤")
        c.setFont("Courier", 9.5)
        c.drawString(split + 34, y, line)
        y -= 14
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(split + 20, y, "STUDIES")
    table = Table(
        [["Degree", "College", "Year"], ["B.E. IT", "Example College", "2022"], ["HSC", "Example School", "2018"]],
        colWidths=[90, 130, 50],
    )
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    _, table_height = table.wrapOn(c, WIDTH, HEIGHT)
    table.drawOn(c, split + 20, y - table_height - 8)
    c.save()


def image_page() -> None:
    c = new_canvas("image_page.pdf")
    y = heading(c, 56, HEIGHT - 70, "EXPERIENCE")
    write_lines(c, 56, y, [
        "Operations Analyst, Example Logistics (2021 - present)",
        "Tracked delivery performance in Excel and SQL and built weekly reports for regional managers.",
        "Automated the monthly invoice check with Python, saving two days of manual work each month.",
    ])
    c.showPage()
    c.drawImage(_text_png(["EDUCATION", "B.Com, Example College, 2020", "SKILLS", "Excel, SQL, Python, Tableau"]),
                0, 0, width=WIDTH, height=HEIGHT)
    c.save()


def many_fonts() -> None:
    fonts = ["Helvetica", "Times-Roman", "Courier", register_ttf("GeorgiaTTF", "georgia.ttf"),
             register_ttf("VerdanaTTF", "verdana.ttf")]
    c = new_canvas("many_fonts.pdf")
    y = HEIGHT - 70
    lines = [
        "Lakshmi Iyer, lakshmi.iyer@example.com, +91 98450 67890",
        "SUMMARY: Product analyst who enjoys turning data into clear decisions.",
        "SKILLS: SQL, Excel, Tableau, Python, Statistics",
        "EXPERIENCE: Product Analyst, Example Commerce (2022 - present). Built funnel dashboards.",
        "EDUCATION: B.Sc. Mathematics, Example University, 2021",
    ]
    for font, line in zip(fonts, lines):
        y = write_lines(c, 56, y, [line], font=font, size=10.5, leading=22)
    c.save()


def decorative() -> None:
    symbols = register_ttf("SegoeSymbol", "seguisym.ttf")
    c = new_canvas("decorative.pdf")
    x, y = 56, HEIGHT - 70
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "Rohan Mehta")
    y -= 26
    rows = [
        ("✉✉ rohan.m@example.com ☎☎ +91 99000 11223", None),
        ("SKILLS ★★★", None),
        ("Python", "★★★★☆"), ("SQL", "★★★☆☆"),
        ("Excel", "★★★★★"), ("Communication", "★★★★☆"),
        ("✨ EXPERIENCE ✨", None),
        ("Junior analyst at Example Retail, building weekly sales reports ☺", None),
    ]
    for text, stars in rows:
        c.setFont(symbols, 10)
        c.drawString(x, y, text)
        if stars:
            c.drawString(x + 120, y, stars)
        y -= 16
    c.save()


def main() -> None:
    for build in (sample_resume_backend, sample_resume_frontend, sidebar_layout, with_table, with_image, six_pages,
                  header_footer, special_tokens, multi_font, data_analyst_resume, scanned, blank, truncated, corrupt,
                  ats_good_resume, ats_bad_resume, image_page, many_fonts, decorative):
        build()
    print("Fixtures written to", OUT)


if __name__ == "__main__":
    main()
