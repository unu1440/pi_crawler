# pi_crawler

흩어진 진로 정보를 라즈베리 파이 한 대에서 자동으로 모으고, 검증 가능한 데이터로 정리하는 마이크로서비스 시스템.

A microservice system on a single Raspberry Pi 5 that gathers scattered academic career information and turns it into organized, verifiable data.

## 문제 (Problem)

대학원 진학과 진로 준비에 필요한 정보는 학교 공지, 연구실 페이지, 뉴스에 나뉘어 있음.
사람이 매일 확인하면 놓치기 쉽고, 한 번 본 정보는 다시 비교하거나 통계로 보기 어렵기에 기획하게 됨.

이 프로젝트에서 다음 세 가지를 검증함.

1. 작은 단일 보드 컴퓨터에서 여러 서비스를 안정적으로 운영할 수 있는가
2. 서로 다른 언어로 만든 서버가 하나의 사용자 세션을 공유할 수 있는가
3. 자동 수집한 정보의 분류와 요약을 얼마나 믿을 수 있는가

## 목표 (Goals)

- 공개된 정보를 사용자별 관심사에 맞춰 수집함.
- 수집, 분석, 전달을 독립된 서비스로 나눔.
- 장애가 나도 데이터가 사라지지 않고 다시 처리할 수 있게 만듦.
- 분류와 요약의 품질을 숫자로 평가함.

## 다루는 정보 (Scope)

| 대주제 | 소주제 |
| --- | --- |
| 대학 | 본교(가천대) |
| 대학원 | 입학·모집, 연구실 소식, 장학·지원, 관심 연구자 |
| AI 국제정세 | 국가별 |

## 시스템 구성 (System Architecture)

컨테이너 8개를 하나의 Docker 네트워크에 둠. 이름과 세부 구성은 구현하면서 바뀔 수 있음.

| 컨테이너 | 역할 | 기술 |
| --- | --- | --- |
| `crawler-proxy` | 역방향 프록시, 경로별 요청 분배 | Nginx Proxy Manager |
| `crawler-front` | 로그인, 키워드 등록, 결과 화면 | HTML, JavaScript |
| `crawler-user` | 회원과 인증 | PHP |
| `crawler-api` | 수집 실행, 결과 조회 | FastAPI |
| `crawler-analyzer` | 중복 제거, 분류, 통계, 요약 | Python, Claude API |
| `crawler-sync` | 예약 실행, 구글 드라이브 전달 | rclone |
| `crawler-redis` | 서버 간 세션 공유 | Redis |
| `crawler-db` | 회원, 키워드, 수집 결과 저장 | MySQL |


<!-- ![시스템 구성도](docs/system-architecture.png) -->

## 통신 절차 (Communication Flow)


<!-- ![통신 절차](docs/communication-flow.png) -->

## 설계 결정 (Design Decisions)

| 결정 | 이유 |
| --- | --- |
| 서버를 PHP와 Python으로 분리 | 회원 기능과 수집 기능을 나누고, 이기종 서버 간 세션 공유를 검증함 |
| 글마다 처리 상태를 기록 | `collected → analyzed → uploaded` 단계로 관리해 실패한 지점부터 다시 처리함 |
| 전달을 분석과 분리 | 분석이 끝난 데이터만 내보내고, 외부 서비스 장애가 수집에 번지지 않게 함 |
| 원문 대신 링크와 요약 저장 | 저작권을 지키고 출처를 언제든 다시 확인할 수 있게 함 |
| 인증 정보를 이미지 밖에 보관 | 공개 저장소와 Docker Hub에 비밀 정보가 들어가지 않게 함 |

## 검증 계획 (Evaluation Plan)

구현 후 아래 항목을 측정해 결과를 공개함. 지금은 계획이며 측정값은 없음.

| 항목 | 방법 |
| --- | --- |
| 수집 안정성 | 실행 횟수 대비 성공률, 실패 원인 기록 |
| 중복 제거 | 표본을 직접 확인해 놓친 중복과 잘못 제거한 글 집계 |
| 분류 품질 | 사람이 라벨링한 표본과 비교해 정밀도, 재현율 계산 |
| 요약 품질 | 표본 요약을 원문과 대조해 사실 오류 확인 |
| 세션 공유 | PHP에서 로그인한 세션을 FastAPI에서 확인 |
| 데이터 영속성 | 컨테이너 재시작 후 DB 데이터 유지 확인 |
| 파이 자원 사용 | 서비스 8개 동작 중 CPU, 메모리, 온도 측정 |

## 수집 원칙 (Data Ethics)

- 공개된 정보만 수집하고, `robots.txt`와 이용약관을 확인함.
- 대상 사이트에 부담을 주지 않도록 수집 주기를 제한함.
- 사람에 대한 정보는 논문, 수상, 임용 같은 공적 활동으로 한정함.
- 개인 연락처와 사생활 정보는 수집하지 않음.

## 진행 상황 (Status)

- [x] 요구사항과 시스템 설계
- [x] 저장소와 실행 환경 준비
- [ ] 로그인과 서버 간 세션 공유
- [ ] 수집과 DB 저장
- [ ] 중복 제거, 분류, 통계
- [ ] 구글 드라이브 전달
- [ ] AI 요약
- [ ] 품질 평가
- [ ] Docker Hub 배포

## 실행 환경 (Environment)

- Raspberry Pi 5, 128GB NVMe SSD
- Debian 13 (aarch64)
- Docker 26.1.5

## 설치와 실행 (How to Run)

Docker Hub 주소와 `docker build`, `docker run` 명령

## 결과 (Results)

구현 화면, 시연 영상, 측정 결과

## 한계 (Limitations)

- 사이트 구조가 바뀌면 해당 소스의 추출 코드를 고쳐야 함.
- 파이 한 대에서 동작하므로 장치가 꺼지면 서비스도 멈춤.
- AI 요약은 사실 오류가 있을 수 있어 원문 링크와 함께 제공.
