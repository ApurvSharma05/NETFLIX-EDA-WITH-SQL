# 🎬 Netflix Data Analysis Using SQL

> SQL-based analysis of Netflix's global content catalog — uncovering trends in content type, country, genre, ratings, and more.

---

## 📌 Overview

This project answers **15 business-relevant questions** about Netflix's content library using SQL. It demonstrates data cleaning, aggregation, window functions, and string parsing on a real-world dataset.

**Dataset:** [Netflix Movies and TV Shows (Till 2025) — Kaggle](https://www.kaggle.com/datasets/bhargavchirumamilla/netflix-movies-and-tv-shows-till-2025)  
**Reference:** [Kaggle Notebook by ankush0511](https://www.kaggle.com/code/ankush0511/netflix-data-analysis)  
**Tools:** SQLite / PostgreSQL · SQL · Python (setup script)

---

## 📁 Project Files

| File | Description |
|------|-------------|
| `netflix_analysis.sql` | All 15 business questions + 5 bonus queries |
| `setup_database.py` | Loads the Kaggle CSV into a local SQLite `.db` file |
| `netflix_titles.csv` | Download from Kaggle (not included in repo) |

---

## 🚀 Getting Started

1. Download `netflix_titles.csv` from the [Kaggle dataset page](https://www.kaggle.com/datasets/bhargavchirumamilla/netflix-movies-and-tv-shows-till-2025)
2. Place it in this project folder
3. Run the setup script:
   ```bash
   python setup_database.py
   ```
4. Open `netflix_analysis.sql` in [DB Browser for SQLite](https://sqlitebrowser.org/) and run any query

---

## 📊 Business Questions Answered

| # | Question |
|---|----------|
| Q1 | Count Movies vs TV Shows |
| Q2 | Most common rating for Movies and TV Shows |
| Q3 | All movies released in 2020 |
| Q4 | Top 5 countries with the most Netflix content |
| Q5 | Identify the longest movie on Netflix |
| Q6 | Content added in the last 5 years |
| Q7 | All titles directed by 'Rajiv Chilaka' |
| Q8 | TV Shows with more than 5 seasons |
| Q9 | Content count in each genre |
| Q10 | Average content releases per year in India (top 5 years) |
| Q11 | All documentary movies |
| Q12 | Content with no director listed |
| Q13 | Movies featuring 'Salman Khan' in the last 10 years |
| Q14 | Top 10 actors in Indian Netflix movies |
| Q15 | Classify content as 'Good' or 'Bad' based on description keywords |

**Bonus Queries:** Year-wise additions · Top directors · Runtime distribution · US vs International · Peak upload month

---

## 💡 Key Findings

| Insight | Finding |
|---------|---------|
| Content split | Netflix has more Movies than TV Shows |
| Most common rating | TV-MA dominates both Movies and TV Shows |
| Top country | United States leads, followed by India and United Kingdom |
| Top genres | Dramas, Comedies, and Documentaries appear most frequently |
| Content without directors | A notable portion — mostly stand-up specials and reality formats |
| India trend | 2018–2020 saw the highest average content additions from India |
| 'Bad' content | A small percentage of titles contain keywords like 'kill' or 'violence' |

---

## 🧠 SQL Concepts Demonstrated

- `GROUP BY`, `ORDER BY`, `HAVING`
- Window functions: `RANK() OVER (PARTITION BY ...)`
- Aggregate functions: `COUNT`, `AVG`, `ROUND`, `MAX`
- Conditional logic: `CASE WHEN`
- Subqueries and derived tables
- String functions: `LIKE`, `TRIM`, `REPLACE`, `SUBSTR`, `INSTR`
- JSON parsing for multi-value columns: `json_each()` (SQLite) / `UNNEST + STRING_TO_ARRAY` (PostgreSQL)

---

## 📄 Resume Entry

> **Netflix Data Analysis Using SQL** — Performed 20+ SQL queries on a Netflix dataset (8,000+ titles) to answer business questions around content trends, country distribution, genre popularity, and audience targeting. Used window functions, conditional aggregation, and string parsing. Tools: SQLite, Python.

---

## About

Built as a portfolio project to demonstrate SQL proficiency and the ability to extract actionable business insights from real-world data.