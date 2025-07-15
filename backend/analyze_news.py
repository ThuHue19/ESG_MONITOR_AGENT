import os
import time
import re
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load model
model = genai.GenerativeModel(model_name="gemini-2.5-flash")
#Convert markdown response to plain text
def markdown_to_plain_text(md_text: str) -> str:
    # Step 1: Remove ** (bold) by replacing **...** with ... (keep content)
    no_bold = re.sub(r'\*\*(.*?)\*\*', r'\1', md_text)

    # Step 2: Remove list markers such as * or -
    no_list_symbols = re.sub(r'^\s*[\*\-\+]\s+', '', no_bold, flags=re.MULTILINE)

    # Step 3: Remove leading whitespace (indentation) at the beginning of lines
    no_indent = re.sub(r'^\s+', '', no_list_symbols, flags=re.MULTILINE)

    # Step 4: Replace multiple consecutive blank lines with a single blank line
    no_extra_blank_lines = re.sub(r'\n\s*\n+', '\n\n', no_indent)

    return no_extra_blank_lines.strip()

# --- 1. Extract keywords and analyze intent from question ---
def extract_keywords_from_question_gemini(question: str) -> str:
    prompt = f"""
You are an ESG investment assistant tasked with analyzing the following question.

Tasks:
1. Extract the most important **keywords** (e.g., company names, ESG-related topics, industries).
2. Identify the **main intent** of the question (e.g., ESG risk, opportunity, regulatory impact).
3. Provide a **brief answer** to the question (2–3 sentences), using relevant data or context if possible.
4. Suggest 2–3 **related search topics** or sub-keywords for article look-up.

Respond using this format:
- Keywords: ...
- Question Intent: ...
- Quick Answer: ...
- Suggested Search Terms: ...

Question: {question}
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Keyword Extraction Failed: {e}"

# --- 2. Analyze a single ESG-related article ---
def analyze_article(title: str, content: str, company: str) -> str:
    prompt = f"""
ESG Investment Article Analysis

You are an experienced ESG analyst. Your task is to evaluate the following article with regard to the ESG profile of the specified company.

Company: {company}  
Article Title: {title}  
Article Content: {content}

== TASKS ==

Step 1: Relevance Check  
- If the article is NOT relevant to {company} (either directly or indirectly through industry context, supply chain, technology trends, or ESG policy landscape), reply only:  
"This article is not relevant to {company}'s ESG analysis and will be excluded from investment evaluation."

Step 2: If relevant, continue the analysis:

1. **Summary**: Provide a concise 2–3 sentence summary of the article.  
2. **ESG Highlights**: List notable claims, ESG risks/opportunities, and especially bold any **key numbers or impactful statements**.  
3. **Company Relevance**: Explain how this article relates to {company}, whether directly (e.g., regulations, actions, controversies) or indirectly (e.g., trends, peers, policy shifts).  
4. **ESG Risk Breakdown**:  
   - Environmental: emissions, raw materials, waste, water, energy  
   - Social: labor, privacy, human rights, DEI, AI ethics, customer trust  
   - Governance: compliance, board oversight, corporate ethics, transparency  
5. **Opportunities**:  
   - ESG actions or initiatives the company could consider  
   - Potential brand, innovation, or competitive advantages arising from this situation  
6. **Strategic Impact**: Comment on long-term effects on {company}'s risk profile, stakeholder trust, brand equity, or regulatory exposure.  
7. **Investment Recommendation**: Choose one — Buy / Hold / Sell  
   - Justify your rating with ESG-based reasoning.

== FORMAT ==  
Summary:  
ESG Highlights:  
Company Relevance:  
ESG Risks:  
Opportunities:  
Strategic Impact:  
Investment Recommendation:  
Justification:  
"""

    try:
        response = model.generate_content(prompt)
        time.sleep(1)  # rate limit buffer
        return response.text if response.text else "No analysis returned."
    except Exception as e:
        return f"Gemini Analysis Failed: {e}"

# --- 3. Summarize multiple article analyses into one overall report ---
def summarize_overall(company: str, analyses: List[str]) -> str:
    if not analyses:
        return f"No analyses available for {company}."

    joined_analyses = "\n\n".join(analyses)
    prompt = f"""
ESG Investment Summary

You are reviewing multiple ESG article analyses for the company: {company}.

=== Goals ===
1. Summarize the **overall ESG sentiment** (positive / neutral / negative).  
2. Identify **recurring risks**, strengths, or themes from the articles.  
3. Highlight any **notable data** (e.g., emissions stats, new regulations, supply chain issues).  
4. Provide a final investment recommendation: Strong Buy / Buy / Hold / Sell / Strong Sell  
5. Justify your recommendation in 3–5 sentences based on ESG impact and strategic implications.

== FORMAT ==
Overall Sentiment:  
Common ESG Risks & Strengths:  
Key Data Highlights:  
Final Recommendation:  
Justification:  
"""
    try:
        response = model.generate_content(prompt)
        return response.text if response.text else "No summary generated."
    except Exception as e:
        return f"Summary generation failed: {e}"

def analyze_question_semantically(question: str) -> str:
    prompt = f"""
You are an intelligent ESG assistant.

Please analyze the following user question and return:
1. The real intent (comparison, evaluation, ESG concern, etc.)
2. All company names or proper nouns involved
3. Whether the user is comparing companies, asking about one, or seeking ESG clarification
4. A cleaned version of the question suitable for ESG article search
5. Return a structured JSON-like response

Question: "{question}"
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Semantic Parsing Failed: {e}"

def normalize_question(question: str) -> str:
    # Fix common pattern: "Which company is better, Apple or Samsung"
    if "which company is better" in question.lower() and " or " in question.lower():
        return question.replace("which company is better, ", "Compare ESG performance between ")
    return question

def detect_question_type(keywords: List[str]) -> str:
    companies = [kw for kw in keywords if kw.lower() in ["apple", "samsung", "google", "microsoft"]]  # can expand
    if len(companies) == 2:
        return "comparison"
    elif len(companies) == 1:
        return "single_company"
    else:
        return "general_question"
