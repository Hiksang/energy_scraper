import os
import requests
from ftplib import FTP
from bs4 import BeautifulSoup

# 네이버 리서치 페이지 (에너지 업종 보고서 예제)
BASE_URL = "https://finance.naver.com/research/industry_list.naver"
NAVER_DOMAIN = "https://finance.naver.com"

# NAS FTP 서버 정보
NAS_IP = "192.9.64.233"  # NAS IP 주소
FTP_PORT = 21            # FTP 포트 (기본 21)
USERNAME = "solution.hkn"     # NAS 사용자 계정
PASSWORD = "Euro12!@" # NAS 비밀번호
NAS_FOLDER = "/naverResearch"  # NAS에 업로드할 폴더

# 저장할 로컬 폴더
LOCAL_SAVE_DIR = "pdf_reports"
os.makedirs(LOCAL_SAVE_DIR, exist_ok=True)

# HTTP 요청 헤더 (User-Agent 설정)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

def get_pdf_links():
    """네이버 리서치 페이지에서 PDF 링크 추출"""
    response = requests.get(BASE_URL, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    reports = []
    rows = soup.select("table.type_1 tr")

    for row in rows[1:]:  # 첫 번째 행(헤더) 제외
        columns = row.find_all("td")
        if len(columns) < 6:
            continue  # 데이터 부족하면 스킵

        title = columns[1].get_text(strip=True)
        pdf_tag = columns[3].find("a", href=True)

        if pdf_tag:
            pdf_url = pdf_tag["href"]
            reports.append((title, pdf_url))

    return reports

def download_pdf(title, pdf_url):
    """PDF 다운로드"""
    response = requests.get(pdf_url, headers=HEADERS, stream=True)
    response.raise_for_status()

    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title) + ".pdf"
    pdf_path = os.path.join(LOCAL_SAVE_DIR, safe_title)

    with open(pdf_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            f.write(chunk)

    print(f"✅ PDF 다운로드 완료: {pdf_path}")
    return pdf_path

def upload_to_nas(file_path):
    """NAS의 FTP 서버에 파일 업로드"""
    ftp = FTP()
    ftp.connect(NAS_IP, FTP_PORT)
    ftp.login(USERNAME, PASSWORD)
    ftp.cwd(NAS_FOLDER)

    with open(file_path, "rb") as f:
        file_name = os.path.basename(file_path)
        ftp.storbinary(f"STOR {file_name}", f)

    ftp.quit()
    print(f"📤 NAS 업로드 완료: {NAS_FOLDER}/{file_name}")

# 실행 로직
pdf_reports = get_pdf_links()

if pdf_reports:
    for title, pdf_url in pdf_reports[:3]:  # 상위 3개 PDF만 다운로드 & 업로드 (테스트용)
        pdf_path = download_pdf(title, pdf_url)
        upload_to_nas(pdf_path)
else:
    print("❌ PDF 파일을 찾을 수 없습니다.")
