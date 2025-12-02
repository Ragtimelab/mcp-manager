# mcp-manager

Simple CLI tool for managing MCP (Model Context Protocol) servers.

## 목적

- MCP 서버 목록 조회
- MCP 서버 업데이트 (brew upgrade처럼)
- MCP 서버 상태 확인
- 설정 백업/복원
- 설정 진단 및 문제 해결 (brew doctor처럼)

## 설치

```bash
cd ~/automation-toolkit/mcp-manager
uv tool install .
```

## 사용법

### 서버 목록 조회

```bash
# 기본
mcpm list
mcpm ls  # 별칭

# 상세 정보 (env 포함)
mcpm list -v
mcpm list --verbose
```

### 서버 업데이트

```bash
# 전체 서버 업데이트
mcpm upgrade
mcpm up  # 별칭

# 특정 서버만 업데이트
mcpm upgrade context7
mcpm up time
```

### 서버 상태 확인

```bash
# 전체 서버 체크
mcpm health

# 특정 서버만 체크
mcpm health context7
```

### 서버 상세 정보

```bash
mcpm show context7
mcpm show time
```

### 설정 백업/복원

```bash
# 백업 생성
mcpm backup

# 백업 목록
mcpm backup -l
mcpm backup --list

# 백업 복원
mcpm backup -r 20251202-143052
mcpm backup --restore 20251202-143052
```

### 설정 진단

```bash
# MCP 설정 진단 및 문제 확인
mcpm doctor
```

## 명령어 도움말

```bash
# 전체 도움말
mcpm --help

# 특정 명령어 도움말
mcpm list --help
mcpm upgrade --help
mcpm health --help
mcpm show --help
mcpm backup --help
```

## 구현 원칙

- **추측 금지, 검증 우선**: 모든 입력 검증
- **우회 금지, 근본 해결**: subprocess 직접 실행
- **아첨 금지, 비판적 사고**: 모든 에러 케이스 처리

## 기술 스택

- Python 3.10+
- typer (CLI 프레임워크)
- rich (출력 포맷팅)

## 라이센스

MIT
