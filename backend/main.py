from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fetch_news import fetch_news
from analyze_news import analyze_article, summarize_overall, extract_keywords_from_question_gemini
import pandas as pd
import re
import asyncio

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://esg-monitor-agent-website.onrender.com",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load ESG data
ESG_DATA_PATH = "data.csv"
try:
    esg_df = pd.read_csv(ESG_DATA_PATH)
    esg_df['ticker'] = esg_df['ticker'].str.upper()
    print("✅ Loaded ESG data columns:", esg_df.columns.tolist())
except Exception as e:
    print(f"❌ Failed to load ESG data: {e}")
    esg_df = pd.DataFrame()

# Request / Response models
class CompanyRequest(BaseModel):
    companies: List[str]

class ArticleAnalysis(BaseModel):
    title: str
    url: str
    analysis: str

class CompanyAnalysisResponse(BaseModel):
    company: str
    articles: List[ArticleAnalysis]
    overall_summary: str
    esg: dict = None

class AskRequest(BaseModel):
    question: str

class QuestionAnswerResponse(BaseModel):
    question: str
    summary: str
    articles: List[ArticleAnalysis]

# Cache
news_cache = {}
analysis_cache = {}

# Core function
def analyze_company_esg(company: str) -> CompanyAnalysisResponse:
    if company in analysis_cache:
        return analysis_cache[company]

    # Fetch news with cache
    articles = news_cache.get(company)
    if not articles:
        articles = fetch_news(company, limit=5)
        news_cache[company] = articles

    analyzed_articles = []
    analyses = []
    for article in articles:
        title = article.get('title', '')
        content = article.get('content', '')
        if not title or not content:
            continue
        try:
            analysis = analyze_article(title, content, company)
            analyses.append(analysis)
            analyzed_articles.append(
                ArticleAnalysis(
                    title=title,
                    url=article.get('url', ''),
                    analysis=analysis
                )
            )
        except Exception as e:
            print(f"⚠️ Failed to analyze article: {e}")

    # ESG info
    esg_info = {}
    matches = esg_df[esg_df['name'].str.lower() == company.lower()]
    if not matches.empty:
        row = matches.iloc[0]
        esg_info = {
            "environment_score": int(row["environment_score"]) if pd.notnull(row["environment_score"]) else None,
            "social_score": int(row["social_score"]) if pd.notnull(row["social_score"]) else None,
            "governance_score": int(row["governance_score"]) if pd.notnull(row["governance_score"]) else None,
            "total_score": int(row["total_score"]) if pd.notnull(row["total_score"]) else None,
            "environment_grade": row["environment_grade"],
            "social_grade": row["social_grade"],
            "governance_grade": row["governance_grade"],
            "total_grade": row["total_grade"],
        }

    overall_summary = summarize_overall(company, analyses)
    response = CompanyAnalysisResponse(
        company=company,
        articles=analyzed_articles,
        overall_summary=overall_summary,
        esg=esg_info
    )
    analysis_cache[company] = response
    return response

# API: /analyze_companies
@app.post("/api/analyze_companies", response_model=List[CompanyAnalysisResponse])
async def analyze_companies_api(request: CompanyRequest):
    async def run_in_thread(company):
        return await asyncio.to_thread(analyze_company_esg, company)
    tasks = [run_in_thread(company) for company in request.companies]
    return await asyncio.gather(*tasks)

# API: /analyze_default_companies
@app.get("/api/analyze_default_companies", response_model=List[CompanyAnalysisResponse])
async def analyze_default_companies():
    try:
        with open("company_list.txt", "r") as f:
            companies = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

    async def run_in_thread(company):
        return await asyncio.to_thread(analyze_company_esg, company)
    tasks = [run_in_thread(c) for c in companies]
    return await asyncio.gather(*tasks)

# API: /ask
@app.post("/api/ask", response_model=QuestionAnswerResponse)
async def ask_ai(request: AskRequest):
    question = request.question
    response = extract_keywords_from_question_gemini(question)
    print("🔍 Gemini response:", response)

    # Extract keywords
    match = re.search(r"- Keywords:\s*(.*?)(?:\n|$)", response, re.DOTALL)
    if match:
        keywords = [kw.strip().lower() for kw in match.group(1).split(",") if kw.strip()]
    else:
        keywords = [response.strip().lower()]

    # Fetch and analyze
    all_articles = []
    for keyword in keywords:
        articles = fetch_news(keyword)
        for article in articles:
            try:
                analysis = analyze_article(article['title'], article['content'])
                all_articles.append({
                    "title": article['title'],
                    "url": article['url'],
                    "analysis": analysis
                })
            except:
                continue

    # Sort by relevance
    def relevance_score(article):
        return sum(kw.lower() in article['title'].lower() for kw in keywords)
    sorted_articles = sorted(all_articles, key=relevance_score, reverse=True)

    # Overall summary
    overall_summary = summarize_overall(question, [a["analysis"] for a in sorted_articles])

    return QuestionAnswerResponse(
        question=question,
        summary=overall_summary,
        articles=[ArticleAnalysis(**a) for a in sorted_articles]
    )
