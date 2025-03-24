import os
import requests
from bs4 import BeautifulSoup
import datetime import datetime
from dotenv import load_dotenv
import logging

from energy_scraper.logger import setup_logger

setup_logger()

# .env 파일 로드 (NAS 경로 등 설정)
load_dotenv()

BASE_URL = "https://finance.naver.com/research/industry_list.naver"
NAS_PATH = os.getenv("NAS_PATH", "./downloads")  # NAS 경로 (기본값: 로컬)

def get_research_papers(page: int = 1):
    """네이버 증권 리서치 페이지에서 에너지 업종 문서 목록 가져오기"""
    url = f"{BASE_URL}?keyword=&brokerCode=&writeFromDate=&writeToDate=&searchType=upjong&upjong=%BF%A1%B3%CA%C1%F6&page={page}"
    
    response = requests.get(url)
    response.raise_for_status()
    print(f"✅ 요청 성공: {url}")

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("table.type_1 tr")  # 문서 리스트
    print(f"🔍 테이블 행 수: {len(rows)}")  # 여기가 0이면 선택자 문제

    papers = []
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        title = cols[1].text.strip()
        company = cols[2].text.strip()
        date = cols[3].text.strip()
        pdf_tag = cols[3].find("a")
        if not pdf_tag or "href" not in pdf_tag.attrs:
            print(f"❌ PDF 링크 없음: {title}")
            continue

        pdf_url = pdf_tag["href"]
        print(f"📎 PDF 있음 → {title} → {pdf_url}")

        papers.append({
            "title": title,
            "company": company,
            "date": date,
            "pdf_url": pdf_url,
        })

    return papers

def get_all_papers():
    """네이버 리서치 페이지에서 마지막까지 돌며 모든 리포트 수집"""
    all_papers = []
    page = 1

    while True:
        print(f"📄 {page}페이지 처리 중...")
        papers = get_research_papers(page)
        if not papers:
            print("❌ 더 이상 리포트 없음. 종료.")
            break

        all_papers.extend(papers)

        # 다음 페이지 버튼이 있는지 확인
        if not has_next_page(page):
            print("✅ 마지막 페이지 도달")
            break

        page += 1

    return all_papers

def has_next_page(current_page: int) -> bool:
    """현재 페이지에서 '다음' 버튼이 있는지 확인"""
    url = f"{BASE_URL}?searchType=upjong&upjong=%BF%A1%B3%CA%C1%F6&page={current_page}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    next_button = soup.select_one("td.pgR a")
    return next_button is not None



def download_pdf(title: str, pdf_url: str):
    """PDF 링크를 직접 다운로드하는 간단한 버전"""
    print(f"📥 다운로드 중: {title} → {pdf_url}")

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(pdf_url, headers=headers)
    response.raise_for_status()

    safe_title = title.replace("/", "_").replace(" ", "_").replace(":", "_").replace("?", "")
    pdf_path = os.path.join(NAS_PATH, f"{safe_title}.pdf")

    with open(pdf_path, "wb") as f:
        f.write(response.content)

    print(f"✅ 저장 완료: {pdf_path}")


def main():
    os.makedirs(NAS_PATH, exist_ok=True)
    all_papers = get_all_papers()
    print(f"📦 총 리포트 수집 개수: {len(all_papers)}")

    for paper in all_papers:
        print(f"📥 다운로드 중: {paper['title']}")
        download_pdf(paper["title"], paper["pdf_url"])



if __name__ == "__main__":
    main()
