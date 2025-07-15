from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fetch_news import fetch_news
from analyze_news import analyze_article, summarize_overall, extract_keywords_from_question_gemini, markdown_to_plain_text
import os
import requests
import pandas as pd
import re
import numpy as np

app = FastAPI()

# CORS middleware để frontend React có thể gọi API
app.add_middleware(
    CORSMiddleware,
    origins = [
    "https://esg-monitor-agent-website.onrender.com",  # domain frontend của bạn
    "http://localhost:3000",  # nếu chạy local frontend
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FINNHUB_API_KEY = "d1qsvrhr01qo4qd99jkgd1qsvrhr01qo4qd99jl0"

# Load ESG data từ file CSV
ESG_DATA_PATH = "data.csv"
try:
    esg_df = pd.read_csv(ESG_DATA_PATH)
    esg_df['ticker'] = esg_df['ticker'].str.upper()  # Chuẩn hóa cột ticker
    print("Columns in data.csv:", esg_df.columns.tolist())  # Debug: In danh sách cột
except Exception as e:
    print(f"Failed to load ESG data: {e}")
    esg_df = pd.DataFrame()

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

class AskRequest(BaseModel):
    question: str

class QuestionAnswerResponse(BaseModel):
    question: str
    summary: str
    articles: List[ArticleAnalysis]

class ESGRequest(BaseModel):
    symbol: str

@app.post("/api/search_query")
async def search_query(request: AskRequest):
    question = request.question
    print(f"Received question: {question}")  # Debug

    # Gọi Gemini để trích xuất từ khóa
    response = extract_keywords_from_question_gemini(question)
    print("Gemini raw response:", response)

    # Trích xuất dòng chứa từ khóa
    match = re.search(r"- Keywords:\s*(.*?)(?:\n|$)", response, re.DOTALL)
    if match:
        keyword_line = match.group(1)
        keywords = [kw.strip().lower() for kw in keyword_line.split(",") if kw.strip()]
    else:
        keywords = [response.strip().lower()]  # Fallback: sử dụng toàn bộ response
    print(f"✅ Extracted keywords: {keywords}")

    # Kiểm tra cột 'name' trong DataFrame
    if 'name' not in esg_df.columns:
        print("Error: 'name' column not found in data.csv")
        return {"error": "Invalid data format: 'name' column missing in ESG data"}

    # Danh sách tên công ty chuẩn hóa từ dữ liệu
    company_names_in_data = [c.lower().strip() for c in esg_df['name'].tolist()]
    print(f"Company names in data: {company_names_in_data}")

    # Tìm từ khóa nào khớp với tên công ty
    matched_companies = []
    for kw in keywords:
        for company_name in company_names_in_data:
            if kw in company_name or company_name in kw:
                matched_companies.append(company_name)
    matched_companies = list(set(matched_companies))  # Loại bỏ trùng lặp

    if matched_companies:
        company_name = matched_companies[0]
    else:
        company_name = keywords[0] if keywords else "Unknown"
    print(f"🔍 Matched company: {company_name}")

    # Tạo map tên công ty → ticker
    companyToTicker = {row['name'].lower().strip(): row['ticker'] for _, row in esg_df.iterrows()}
    print(f"companyToTicker: {companyToTicker}")

    # Lấy ticker nếu có
    ticker = companyToTicker.get(company_name.lower().strip())
    print(f"Found ticker: {ticker}")

    if ticker:
        esg_data = esg_df[esg_df["ticker"].str.upper() == ticker.upper()]
        if not esg_data.empty:
            row = esg_data.iloc[0]
            # Chuyển đổi numpy.int64 sang int để tránh lỗi JSON serialization
            return {
                "ticker": ticker,
                "company": row["name"],
                "environment_score": int(row["environment_score"]) if pd.notnull(row["environment_score"]) else None,
                "social_score": int(row["social_score"]) if pd.notnull(row["social_score"]) else None,
                "governance_score": int(row["governance_score"]) if pd.notnull(row["governance_score"]) else None,
                "total_score": int(row["total_score"]) if pd.notnull(row["total_score"]) else None,
                "environment_grade": row["environment_grade"],
                "social_grade": row["social_grade"],
                "governance_grade": row["governance_grade"],
                "total_grade": row["total_grade"]
            }

    return {
        "error": f"No ESG data found for company '{company_name}'. This may be due to limited public ESG disclosures, common for smaller companies in emerging markets like China's education sector."
    }

@app.post("/api/finnhub_esg")
async def finnhub_esg(request: ESGRequest):
    symbol = request.symbol.upper()
    esg_data = esg_df[esg_df["ticker"].str.upper() == symbol]
    if not esg_data.empty:
        row = esg_data.iloc[0]
        # Chuyển đổi numpy.int64 sang int
        return {
            "ticker": symbol,
            "company": row["name"],
            "environment_score": int(row["environment_score"]) if pd.notnull(row["environment_score"]) else None,
            "social_score": int(row["social_score"]) if pd.notnull(row["social_score"]) else None,
            "governance_score": int(row["governance_score"]) if pd.notnull(row["governance_score"]) else None,
            "total_score": int(row["total_score"]) if pd.notnull(row["total_score"]) else None,
            "environment_grade": row["environment_grade"],
            "social_grade": row["social_grade"],
            "governance_grade": row["governance_grade"],
            "total_grade": row["total_grade"]
        }
    return {
        "error": f"No ESG data found for ticker '{symbol}'. This may be due to limited public ESG disclosures."
    }

def analyze_company_esg(company: str) -> CompanyAnalysisResponse:
    articles = fetch_news(company, limit=5)
    if not articles:
        return CompanyAnalysisResponse(
            company=company,
            articles=[],
            overall_summary=f"No articles found for {company}. This may be due to limited news coverage."
        )

    analyzed_articles = []
    analyses = []
    for article in articles:
        analysis = analyze_article(article['title'], article['content'], company)
        analyses.append(analysis)
        analyzed_articles.append(
            ArticleAnalysis(
                title=article['title'],
                url=article['url'],
                analysis=analysis
            )
        )

    overall_summary = summarize_overall(company, analyses)
    return CompanyAnalysisResponse(
        company=company,
        articles=analyzed_articles,
        overall_summary=overall_summary
    )

@app.post("/api/analyze_companies", response_model=List[CompanyAnalysisResponse])
async def analyze_companies_api(request: CompanyRequest):
    results = []
    for company in request.companies:
        result = analyze_company_esg(company)
        results.append(result)
    return results

@app.get("/api/analyze_default_companies", response_model=List[CompanyAnalysisResponse])
async def analyze_default_companies():
    try:
        with open("company_list.txt", "r") as f:
            companies = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

    results = []
    for company in companies:
        result = analyze_company_esg(company)
        results.append(result)
    return results

@app.post("/api/ask", response_model=QuestionAnswerResponse)
async def ask_ai(request: AskRequest):
    question = request.question
    response = extract_keywords_from_question_gemini(question)
    print("🔍 Gemini response for /api/ask:", response)

    # Trích xuất từ khóa
    match = re.search(r"- Keywords:\s*(.*?)(?:\n|$)", response, re.DOTALL)
    if match:
        keyword_line = match.group(1)
        keywords = [kw.strip().lower() for kw in keyword_line.split(",") if kw.strip()]
    else:
        keywords = [response.strip().lower()]
    print(f"✅ Extracted keywords for /api/ask: {keywords}")

    all_articles = []
    for keyword in keywords:
        articles = fetch_news(keyword)
        for article in articles:
            analysis = analyze_article(article['title'], article['content'])
            all_articles.append({
                "title": article['title'],
                "url": article['url'],
                "analysis": analysis
            })

    def relevance_score(article):
        return sum(kw.lower() in article['title'].lower() for kw in keywords)

    sorted_articles = sorted(all_articles, key=relevance_score, reverse=True)
    overall_summary = summarize_overall(question, [a["analysis"] for a in sorted_articles])

    return QuestionAnswerResponse(
        question=question,
        summary=overall_summary,
        articles=[ArticleAnalysis(**a) for a in sorted_articles]
    )