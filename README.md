## 초기 실행

처음 실행 시에는 downloaded_ids.json 파일이 없기 때문에, 자동으로 전체 리포트 크롤링을 수행합니다.

'''bash
docker run --env-file .env naverresearch

'''

## 크론잡 설정

'''bash
0 \* \* \* \* docker run --rm --env-file /path/to/.env naverresearch

'''
