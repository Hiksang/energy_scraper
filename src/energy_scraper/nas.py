import os
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()

# 환경변수에서 NAS 설정 읽기
NAS_IP = os.getenv("NAS_IP")
FTP_PORT = int(os.getenv("FTP_PORT", 21))
USERNAME = os.getenv("NAS_USERNAME")
PASSWORD = os.getenv("NAS_PASSWORD")
NAS_FOLDER = os.getenv("NAS_FOLDER", "/")

def upload_to_nas(file_path: str):
    """
    지정한 파일을 NAS의 FTP 경로에 업로드합니다.
    
    Parameters:
        file_path (str): 업로드할 로컬 파일 경로
    """
    if not all([NAS_IP, USERNAME, PASSWORD]):
        raise ValueError("NAS 접속 정보가 누락되었습니다. .env 파일을 확인하세요.")

    file_name = os.path.basename(file_path)

    ftp = FTP()
    ftp.connect(NAS_IP, FTP_PORT)
    ftp.login(USERNAME, PASSWORD)
    ftp.cwd(NAS_FOLDER)

    with open(file_path, "rb") as f:
        ftp.storbinary(f"STOR {file_name}", f)

    ftp.quit()
    print(f"NAS 업로드 완료: {NAS_FOLDER}/{file_name}")
