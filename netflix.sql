-- ============================================================
--   Netflix Data Analysis Using SQL
--   Dataset: Netflix Movies and TV Shows (Till 2025)
--   Source:  https://www.kaggle.com/datasets/bhargavchirumamilla/netflix-movies-and-tv-shows-till-2025
--   Reference: https://www.kaggle.com/code/ankush0511/netflix-data-analysis
-- ============================================================


-- ============================================================
-- TABLE SCHEMA
-- ============================================================

CREATE TABLE netflix (
    show_id      VARCHAR(10),
    type         VARCHAR(10),
    title        VARCHAR(250),
    director     VARCHAR(550),
    casts        VARCHAR(1050),
    country      VARCHAR(550),
    date_added   VARCHAR(55),
    release_year INT,
    rating       VARCHAR(15),
    duration     VARCHAR(15),
    listed_in    VARCHAR(250),
    description  VARCHAR(550)
);


-- ============================================================
-- BASIC EXPLORATION
-- ============================================================

-- Preview the data
SELECT * FROM netflix LIMIT 10;

-- Total number of records
SELECT COUNT(*) AS total_content FROM netflix;


-- ============================================================
-- Q1. Count the number of Movies vs TV Shows
-- ============================================================

SELECT
    type,
    COUNT(*) AS total_content
FROM netflix
GROUP BY type;


-- ============================================================
-- Q2. Find the most common rating for Movies and TV Shows
-- ============================================================

SELECT
    type,
    rating
FROM (
    SELECT
        type,
        rating,
        COUNT(*) AS count,
        RANK() OVER (PARTITION BY type ORDER BY COUNT(*) DESC) AS ranking
    FROM netflix
    GROUP BY type, rating
) AS ranked
WHERE ranking = 1;


-- ============================================================
-- Q3. List all movies released in 2020
-- ============================================================

SELECT *
FROM netflix
WHERE type = 'Movie'
  AND release_year = 2020;


-- ============================================================
-- Q4. Find the top 5 countries with the most content on Netflix
-- ============================================================

-- PostgreSQL version (handles multi-country entries):
SELECT
    TRIM(UNNEST(STRING_TO_ARRAY(country, ','))) AS new_country,
    COUNT(show_id)                               AS total_content
FROM netflix
GROUP BY new_country
ORDER BY total_content DESC
LIMIT 5;

-- SQLite-compatible version:
SELECT
    TRIM(value)    AS country,
    COUNT(show_id) AS total_content
FROM netflix,
     json_each('["' || REPLACE(country, ', ', '","') || '"]')
WHERE country IS NOT NULL AND country != ''
GROUP BY country
ORDER BY total_content DESC
LIMIT 5;


-- ============================================================
-- Q5. Identify the longest movie on Netflix
-- ============================================================

SELECT
    title,
    CAST(REPLACE(duration, ' min', '') AS INTEGER) AS runtime_min
FROM netflix
WHERE type = 'Movie'
  AND duration LIKE '%min%'
ORDER BY runtime_min DESC
LIMIT 1;


-- ============================================================
-- Q6. Find content added in the last 5 years
-- ============================================================

-- SQLite-compatible:
SELECT *
FROM netflix
WHERE CAST(SUBSTR(TRIM(date_added), -4) AS INTEGER)
      >= (CAST(STRFTIME('%Y', 'now') AS INTEGER) - 5);

-- PostgreSQL:
-- SELECT * FROM netflix
-- WHERE TO_DATE(date_added, 'Month DD, YYYY') >= CURRENT_DATE - INTERVAL '5 years';


-- ============================================================
-- Q7. Find all movies/TV shows directed by 'Rajiv Chilaka'
-- ============================================================

SELECT *
FROM netflix
WHERE director LIKE '%Rajiv Chilaka%';


-- ============================================================
-- Q8. List all TV Shows with more than 5 seasons
-- ============================================================

SELECT *
FROM netflix
WHERE type = 'TV Show'
  AND CAST(
      TRIM(REPLACE(REPLACE(duration, ' Seasons', ''), ' Season', ''))
      AS INTEGER
  ) > 5;


-- ============================================================
-- Q9. Count the number of content items in each genre
-- ============================================================

-- SQLite:
SELECT
    TRIM(value)    AS genre,
    COUNT(show_id) AS total_content
FROM netflix,
     json_each('["' || REPLACE(listed_in, ', ', '","') || '"]')
WHERE listed_in IS NOT NULL
GROUP BY genre
ORDER BY total_content DESC;

-- PostgreSQL:
-- SELECT UNNEST(STRING_TO_ARRAY(listed_in, ',')) AS genre,
--        COUNT(show_id) AS total_content
-- FROM netflix GROUP BY genre ORDER BY total_content DESC;


-- ============================================================
-- Q10. Find each year and the average number of content releases
--      IN INDIA on Netflix — return top 5 years
-- ============================================================

SELECT
    country,
    release_year,
    COUNT(show_id) AS total_release,
    ROUND(
        COUNT(show_id) * 1.0 /
        (SELECT COUNT(show_id) FROM netflix WHERE country = 'India') * 100,
        2
    ) AS avg_release_pct
FROM netflix
WHERE country = 'India'
GROUP BY country, release_year
ORDER BY avg_release_pct DESC
LIMIT 5;


-- ============================================================
-- Q11. List all movies that are Documentaries
-- ============================================================

SELECT *
FROM netflix
WHERE listed_in LIKE '%Documentaries%'
  AND type = 'Movie';


-- ============================================================
-- Q12. Find all content without a director
-- ============================================================

SELECT *
FROM netflix
WHERE director IS NULL OR TRIM(director) = '';


-- ============================================================
-- Q13. How many movies has 'Salman Khan' appeared in
--      over the last 10 years?
-- ============================================================

SELECT *
FROM netflix
WHERE casts LIKE '%Salman Khan%'
  AND type = 'Movie'
  AND release_year > (CAST(STRFTIME('%Y', 'now') AS INTEGER) - 10);


-- ============================================================
-- Q14. Find the top 10 actors who have appeared in the highest
--      number of movies produced in India
-- ============================================================

SELECT
    TRIM(value)  AS actor,
    COUNT(*)     AS appearances
FROM netflix,
     json_each('["' || REPLACE(casts, ', ', '","') || '"]')
WHERE country LIKE '%India%'
  AND casts IS NOT NULL AND casts != ''
GROUP BY actor
ORDER BY appearances DESC
LIMIT 10;


-- ============================================================
-- Q15. Categorize content as 'Good' or 'Bad' based on keywords
--      'kill' or 'violence' appearing in the description
-- ============================================================

-- Summary count:
SELECT
    category,
    COUNT(*) AS content_count
FROM (
    SELECT
        CASE
            WHEN description LIKE '%kill%'
              OR description LIKE '%violence%' THEN 'Bad'
            ELSE 'Good'
        END AS category
    FROM netflix
) AS categorized
GROUP BY category
ORDER BY content_count DESC;

-- Full labeled list:
SELECT
    title,
    type,
    description,
    CASE
        WHEN description LIKE '%kill%'
          OR description LIKE '%violence%' THEN 'Bad'
        ELSE 'Good'
    END AS content_label
FROM netflix
ORDER BY content_label;


-- ============================================================
-- BONUS QUERIES
-- ============================================================

-- B1. Year-wise content additions to Netflix
SELECT
    SUBSTR(TRIM(date_added), -4) AS year_added,
    COUNT(*)                     AS titles_added
FROM netflix
WHERE date_added IS NOT NULL AND date_added != ''
GROUP BY year_added
ORDER BY year_added DESC;


-- B2. Top 5 most prolific directors on Netflix
SELECT
    director,
    COUNT(show_id) AS total_titles
FROM netflix
WHERE director IS NOT NULL AND TRIM(director) != ''
GROUP BY director
ORDER BY total_titles DESC
LIMIT 5;


-- B3. Movie runtime distribution (bucketed)
SELECT
    CASE
        WHEN CAST(REPLACE(duration, ' min', '') AS INTEGER) < 60  THEN 'Under 1 hr'
        WHEN CAST(REPLACE(duration, ' min', '') AS INTEGER) < 90  THEN '1 – 1.5 hrs'
        WHEN CAST(REPLACE(duration, ' min', '') AS INTEGER) < 120 THEN '1.5 – 2 hrs'
        WHEN CAST(REPLACE(duration, ' min', '') AS INTEGER) < 150 THEN '2 – 2.5 hrs'
        ELSE 'Over 2.5 hrs'
    END           AS runtime_bucket,
    COUNT(*)      AS movie_count
FROM netflix
WHERE type = 'Movie' AND duration LIKE '%min%'
GROUP BY runtime_bucket;


-- B4. US vs International content ratio
SELECT
    CASE
        WHEN country = 'United States' THEN 'US Content'
        ELSE 'International'
    END           AS origin,
    COUNT(*)      AS total,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM netflix WHERE country IS NOT NULL), 1) AS pct
FROM netflix
WHERE country IS NOT NULL AND country != ''
GROUP BY origin;


-- B5. Which month does Netflix add the most content?
SELECT
    TRIM(SUBSTR(date_added, 1, INSTR(date_added, ' ') - 1)) AS month,
    COUNT(*) AS titles_added
FROM netflix
WHERE date_added IS NOT NULL AND date_added != ''
GROUP BY month
ORDER BY titles_added DESC;