import os
import requests
import json
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import argparse

from dotenv import load_dotenv
from energy_scraper.logger import setup_logger
from energy_scraper.slack import send_slack_message  # 상단에 추가
from energy_scraper.metadata import save_metadata_to_mongo
from energy_scraper.nas import upload_to_nas

# 로그 설정
setup_logger()

# 환경 변수 로드
load_dotenv()

BASE_URL = "https://finance.naver.com/research/industry_list.naver"
NAS_PATH = os.environ.get("NAS_PATH", "./downloads")
LOG_PATH = "downloaded_ids.json"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

#############################################################################
#  이전에 다운한 pdf의 id를 저장하는 json 파일 load 
#############################################################################
def load_downloaded_ids():
    if not os.path.exists(LOG_PATH):
        return set()
    with open(LOG_PATH, "r") as f:
        return set(json.load(f))

def save_downloaded_id(nid: str):
    ids = load_downloaded_ids()
    ids.add(nid)
    with open(LOG_PATH, "w") as f:
        json.dump(list(ids), f, indent=2)

def get_nid_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("nid", [""])[0]

def get_research_papers(page: int = 1):
    url = f"{BASE_URL}?searchType=upjong&upjong=%BF%A1%B3%CA%C1%F6&page={page}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    logging.info(f"요청 성공: {url}")

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("table.type_1 tr")

    papers = []
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        title = cols[1].text.strip()
        company = cols[2].text.strip()
        date = cols[4].text.strip()
        link_tag = cols[1].find("a")
        pdf_tag = cols[3].find("a")

        if not link_tag or not pdf_tag:
            continue

        view_url = link_tag["href"]
        nid = get_nid_from_url(view_url)
        pdf_url = pdf_tag["href"]

        papers.append({
            "nid": nid,
            "title": title,
            "company": company,
            "date": date,
            "pdf_url": pdf_url,
        })

    return papers


def get_all_papers():
    all_papers = []
    page = 1
    while True:
        logging.info(f"{page}페이지 처리 중")
        papers = get_research_papers(page)
        if not papers:
            break

        all_papers.extend(papers)

        if not has_next_page(page):
            break
        page += 1
    return all_papers


def has_next_page(current_page: int) -> bool:
    url = f"{BASE_URL}?searchType=upjong&upjong=%BF%A1%B3%CA%C1%F6&page={current_page}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.select_one("td.pgR a") is not None


def download_pdf(title: str, pdf_url: str, raw_date: str):
    logging.info(f"다운로드 중: {title} → {pdf_url}")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(pdf_url, headers=headers)
    response.raise_for_status()

    safe_title = title.replace("/", "_").replace(" ", "_").replace(":", "_").replace("?", "")
    pdf_path = os.path.join(NAS_PATH, f"{safe_title}.pdf")
    
    with open(pdf_path, "wb") as f:
        f.write(response.content)

    logging.info(f"저장 완료: {pdf_path}")

    # 작성일 변환 처리
    try:
        report_date = datetime.strptime(raw_date, "%y.%m.%d").strftime("%Y-%m-%d")
    except ValueError:
        report_date = None

    metadata = {
        "source": "naver_research",
        "title": title,
        "date": report_date,
        "pdf_url": pdf_url,
        "downloaded_path": pdf_path,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    print("\n===== 추출된 메타데이터 =====")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    print("===========================\n")

    return metadata


def main(full: bool = False):
    if not os.path.exists(LOG_PATH):
        logging.info("처음 실행입니다. 전체 리포트를 다운로드합니다.")
        full = True
    os.makedirs(NAS_PATH, exist_ok=True)
    downloaded_ids = load_downloaded_ids()
    new_downloads = 0

    papers = get_all_papers() if full else get_research_papers(1)
    logging.info(f"수집된 리포트 개수: {len(papers)}")

    for paper in papers:
        if paper["nid"] in downloaded_ids:
            continue

        metadata = None
        try:
            metadata = download_pdf(
                title=paper["title"],
                pdf_url=paper["pdf_url"],
                raw_date=paper["date"]
            )
        except Exception as e:
            logging.error(f"PDF 다운로드 실패: {paper['title']} | {e}")
            if SLACK_WEBHOOK_URL:
                send_slack_message(
                    webhook_url=SLACK_WEBHOOK_URL,
                    message=f"[PDF 다운로드 실패] {paper['title']}\n{str(e)}",
                    username="리포트 수집기"
                )
            continue  # 다운로드 실패 시 다음 리포트로 넘어감

        try:
            upload_to_nas(metadata["downloaded_path"])
        except Exception as e:
            logging.error(f"NAS 업로드 실패: {paper['title']} | {e}")
            if SLACK_WEBHOOK_URL:
                send_slack_message(
                    webhook_url=SLACK_WEBHOOK_URL,
                    message=f"[NAS 업로드 실패] {paper['title']}\n{str(e)}",
                    username="리포트 수집기"
                )
            continue  # 업로드 실패해도 Mongo 저장 및 기록은 하지 않음

        save_downloaded_id(paper["nid"])
        save_metadata_to_mongo(metadata)
        new_downloads += 1

    if new_downloads > 0:
        logging.info(f"신규 리포트 {new_downloads}건 다운로드 완료")
        if SLACK_WEBHOOK_URL:
            send_slack_message(
                webhook_url=SLACK_WEBHOOK_URL,
                message=f"{new_downloads}건의 에너지 리포트가 다운로드되었습니다.",
                username="리포트 수집기"
            )
    else:
        logging.info("새로운 리포트가 없습니다.")
        if SLACK_WEBHOOK_URL:
            send_slack_message(
                    webhook_url=SLACK_WEBHOOK_URL,
                    message=f"{new_downloads}건의 에너지 리포트가 다운로드되었습니다.",
                    username="리포트 수집기"
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="전체 리포트를 강제로 다운로드할지 여부")
    args = parser.parse_args()

    main(full=args.full)
