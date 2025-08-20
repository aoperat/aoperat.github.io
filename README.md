# Chirpy Jekyll 블로그 명령어 가이드

본 문서는 Chirpy Jekyll 테마 기반 블로그 운영에 필요한 주요 CLI 명령어와 절차를 정리한 안내서입니다.

---

## 1. 환경 준비

### Ruby, Bundler 설치
```bash
# MacOS
brew install ruby
gem install bundler
```

# Windows
# Ruby 다운로드: https://rubyinstaller.org
# 명령 프롬프트(관리자 권한)
gem install bundler


```bash
# 깃헙 저장소 복제
git clone [YOUR_REPO_URL] my-blog
cd my-blog

# gem 패키지 설치
bundle install
```

```bash
# 기본 개발 서버 실행 (localhost:4000)
bundle exec jekyll serve

# 포트 변경 (예: 5000)
bundle exec jekyll serve --port 5000
```