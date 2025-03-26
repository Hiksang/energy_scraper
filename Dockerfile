# 1. 베이스 이미지
FROM python:3.13-slim

# 2. 시스템 패키지 설치 및 poetry 설치
RUN apt-get update && apt-get install -y curl gcc && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get clean

# poetry가 설치되는 경로를 PATH에 추가
ENV PATH="/root/.local/bin:$PATH"

# 3. 작업 디렉토리 생성
WORKDIR /app

# 4. 프로젝트 파일 복사
COPY pyproject.toml poetry.lock ./
COPY src ./src
COPY main.py ./

# 5. PYTHONPATH 설정 (src 내부 모듈 인식용)
ENV PYTHONPATH=/app/src

# 6. 의존성 설치
RUN poetry install --no-root

# 7. 실행 명령
ENTRYPOINT ["poetry", "run", "python", "main.py"]
