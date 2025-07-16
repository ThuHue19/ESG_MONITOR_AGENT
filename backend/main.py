from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fetch_news import fetch_news
from analyze_news import analyze_article, summarize_overall, extract_keywords_from_question_gemini
import pandas as pd
import re
import asyncio
from rapidfuzz import process


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

def find_best_matching_company(company_query: str, choices: List[str]) -> str:
    match, score, _ = process.extractOne(company_query, choices)
    return match if score > 75 else None

def analyze_company_esg(company: str) -> CompanyAnalysisResponse:
    if company in analysis_cache:
        return analysis_cache[company]

    company_names = esg_df['name'].tolist()
    best_match = find_best_matching_company(company, company_names)

    # Nếu không tìm được tên chuẩn thì fallback lại company gốc
    search_name = best_match or company

    articles = news_cache.get(search_name)
    if not articles:
        articles = fetch_news(search_name, limit=5)   # <-- Dùng tên chuẩn để tìm bài
        news_cache[search_name] = articles

    analyzed_articles = []
    analyses = []
    for article in articles:
        title = article.get('title', '')
        content = article.get('content', '')
        if not title or not content:
            continue
        try:
            analysis = analyze_article(title, content, search_name)
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

    esg_info = {}
    if best_match:
        row = esg_df[esg_df['name'] == best_match].iloc[0]
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

    overall_summary = summarize_overall(search_name, analyses)
    response = CompanyAnalysisResponse(
        company=best_match or company,
        articles=analyzed_articles,
        overall_summary=overall_summary,
        esg=esg_info
    )
    analysis_cache[company] = response
    return response

@app.post("/api/analyze_companies", response_model=List[CompanyAnalysisResponse])
async def analyze_companies_api(request: CompanyRequest):
    async def run_in_thread(company):
        return await asyncio.to_thread(analyze_company_esg, company)
    tasks = [run_in_thread(company) for company in request.companies]
    return await asyncio.gather(*tasks)

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
@app.post("/api/ask", response_model=QuestionAnswerResponse)
async def ask_ai(request: AskRequest):
    question = request.question
    response = extract_keywords_from_question_gemini(question)
    print("🔍 Gemini response:", response)

    # Tách danh sách Companies và Keywords trong response (theo format Gemini trả về)
    match_c = re.search(r"- Companies:\s*(.*?)(?:\n|$)", response, re.IGNORECASE)
    companies = [c.strip() for c in match_c.group(1).split(",")] if match_c else []

    match_k = re.search(r"- Keywords:\s*(.*?)(?:\n|$)", response, re.IGNORECASE)
    keywords = [k.strip() for k in match_k.group(1).split(",")] if match_k else []

    # Lấy danh sách tên công ty chuẩn từ dataset ESG
    company_names = esg_df['name'].tolist()
    
    # Tìm công ty gần đúng đầu tiên trong companies + keywords
    matched_company = None
    for c in companies + keywords:
        match = find_best_matching_company(c, company_names)
        print(f"Trying to match '{c}' -> Found: '{match}'")
        if match:
            matched_company = match
            break

    # Nếu tìm được tên công ty chuẩn thì phân tích và trả kết quả
    if matched_company:
        result = analyze_company_esg(matched_company)

        total_score = result.esg.get("total_score", 0) if result.esg else 0
        risk_level = "Low" if total_score > 1000 else "Moderate" if total_score > 700 else "High"
        risk_percent = round(100 - (total_score / 1200) * 100)
        recommendation = "Buy" if total_score > 1000 else "Hold" if total_score > 700 else "Avoid"

        summary = f"""
**Investment Recommendation**: {recommendation}  
**Estimated Risk Level**: {risk_level} (~{risk_percent}% risk)  
**Overall ESG Score**: {total_score}

{result.overall_summary}
"""

        return QuestionAnswerResponse(
            question=question,
            summary=summary.strip(),
            articles=result.articles
        )

    # Nếu không tìm được công ty chuẩn, fallback tìm bài báo theo keywords
    all_articles = []
    for keyword in keywords:
        articles = fetch_news(keyword)
        for article in articles:
            try:
                analysis = analyze_article(article['title'], article['content'], keyword)
                all_articles.append({
                    "title": article['title'],
                    "url": article['url'],
                    "analysis": analysis
                })
            except Exception as e:
                print(f"⚠️ Failed to analyze fallback article: {e}")
                continue

    # Sắp xếp bài báo theo mức độ liên quan (dựa vào keywords)
    def relevance_score(article):
        return sum(kw.lower() in article['title'].lower() for kw in keywords)

    sorted_articles = sorted(all_articles, key=relevance_score, reverse=True)
    overall_summary = summarize_overall(question, [a["analysis"] for a in sorted_articles])

    return QuestionAnswerResponse(
        question=question,
        summary=overall_summary,
        articles=[ArticleAnalysis(**a) for a in sorted_articles]
    )
