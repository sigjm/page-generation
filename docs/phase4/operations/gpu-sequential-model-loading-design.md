# GPU 순차 적재 설계 — 이미지 모델을 쓸 때만 GPU에 올린다

- 작성: 2026-10-01 · 생성형 AI 팀 (상세페이지 생성)
- 상태: **설계안 (미구현)**. 누끼 CPU 실행(GenAI #54) 배포 후에도 오류가 나면 적용한다
- 기준: Stage L40S(44.39 GiB 가용) 실측, SGLang `v0.5.19` 원본 코드

> 성격: 시점 기록. 적용 여부와 실측 결과는 [AWS 배포 가이드](aws-deployment.md) 6절에 반영한다.

---

## 1. 왜 필요한가

텍스트 서버와 이미지 서버가 **요청이 없을 때도** GPU를 붙잡고 있어서, 셋째 모델(누끼)이 쓸 자리가 없다.

| 프로세스 | 상주 (Stage 실측, 2026-10-01) |
| --- | ---: |
| 텍스트 서버 (Qwen3.8-27B AWQ) | 약 23.5 GiB |
| 이미지 서버 (FLUX.2-klein bnb-4bit) | 약 15.8 GiB (가중치 약 10.2 + 기동 워밍업에서 잡은 계산 메모리) |
| 남는 여유 | 약 5.7 GiB |

- 누끼(BiRefNet 1024², fp32)는 이 5.7 GiB에서도 822 MB 버퍼를 못 잡아 실패했다
- 텍스트 서버가 OOM으로 죽어 GPU가 빈 직후의 렌더는 GPU 누끼로 성공했다
- 순차 실행 잠금(작업 하나씩)은 이미 배포됐지만, 각 서버가 붙잡은 메모리는 작업이 끝나도 풀리지 않는다

**결정한 1차 대응:** 누끼를 CPU에서 실행한다 (#54). 다만 다음 중 하나가 생기면 이 설계로 넘어간다.

- 누끼를 CPU로 옮긴 뒤에도 텍스트·이미지 서버에서 CUDA OOM이 난다
- CPU 누끼(1장 약 50~60초) 때문에 렌더가 BE 타임아웃(300초)을 자주 넘긴다
- Pod 메모리가 한도(24 GiB)에 가까워진다 (CPU 누끼 최대 RSS 약 12.9 GiB)

## 2. 핵심 아이디어

**이미지 서버는 평소에 잠들어 있다가, 렌더의 이미지 생성 단계에서만 깨운다.** 텍스트 서버는 계속 상주한다.

SGLang 이미지(diffusion) 서버에는 프로세스를 끄지 않고 GPU를 비우는 API가 기본으로 열려 있다 (`multimodal_gen/runtime/entrypoints/post_training/weights_api.py`, 항상 마운트됨).

| API | 동작 (`memory_occupation_controller.py`) |
| --- | --- |
| `POST /release_memory_occupation` | 모듈 가중치를 **고정(pinned) CPU 메모리로 복사**하고 `empty_cache()` — 워밍업이 잡은 계산 메모리까지 반환 |
| `POST /resume_memory_occupation` | CPU의 가중치를 GPU로 다시 옮김 (디스크에서 다시 읽지 않음) |

서버 프로세스를 내렸다 다시 올리는 방식은 Stage 실측으로 이미지 서버 약 2.5분, 텍스트 서버 약 7.4분이 걸려 렌더마다 쓸 수 없다. 잠들기/깨우기는 RAM↔GPU 복사(약 10 GiB)라 수 초 단위로 예상한다 (실측 필요).

텍스트 서버까지 잠들게 하는 안은 쓰지 않는다. 텍스트 서버는 `--enable-memory-saver`로 GPU를 비울 수는 있지만, 가중치를 RAM에 두려면(`--enable-weights-cpu-backup`) 약 19 GiB가 더 필요해 Pod 한도를 넘는다. RAM에 두지 않으면 매번 디스크에서 다시 읽어야 한다(약 165초).

## 3. 단계별 GPU 사용

작업은 이미 한 번에 하나씩 실행된다 (`DetailPagePipeline`의 잠금). 그래서 단계 전환 중에 다른 작업이 끼어들지 않는다.

| 단계 | 텍스트 서버 | 이미지 서버 | 누끼 | GPU 여유 (예상) |
| --- | --- | --- | --- | ---: |
| 대기·초안(분석) | 상주 23.5 | **잠듦** (CUDA 컨텍스트만, 약 0.5) | 없음 | 약 20 GiB |
| 렌더 ① 누끼 | 상주 | 잠듦 | **GPU**에서 실행 후 메모리 반환 | 약 14 GiB (누끼 중) |
| 렌더 ② 사진 생성·편집 | 상주 | **깨움** → 생성 | 없음 | 약 5 GiB |
| 렌더 ③ 끝 | 상주 | **다시 잠듦** | 없음 | 약 20 GiB |
| 렌더 ④ 페이지 합성 (CPU) | 상주 | 잠듦 | 없음 | 약 20 GiB |

- 렌더 ②에서 텍스트 서버의 분석은 돌지 않으므로(작업 하나씩) 두 서버의 순간 사용량이 겹치지 않는다
- 렌더 ③은 `finally`로 보장한다. 생성이 실패해도 이미지 서버를 잠재운다

## 4. 구현 지점

| 위치 | 변경 |
| --- | --- |
| `deploy/sglang/entrypoint.sh` | 이미지 서버 준비 직후 `/release_memory_occupation` 한 번 → **잠든 상태로 시작**. 실패하면 기동 실패로 처리 |
| `src/local_detail_page_ai/clients.py` (`SglangImageClient`) | `wake()`·`sleep()` 추가 — 각각 `/resume_memory_occupation`·`/release_memory_occupation` 호출, 타임아웃·재시도 포함 |
| `src/detail_page_ai/pipeline.py` (`run`) | 사진 생성 직전에 `wake()`, 직후 `finally`에서 `sleep()`. 초안(`create_draft`)은 깨우지 않음 |
| `src/detail_page_ai/source_photos.py` | 누끼를 다시 GPU로 (`REMBG_USE_CUDA=1`). 누끼가 끝나면 onnxruntime 메모리를 반환 — 렌더마다 세션을 만들고 닫거나, 실행 옵션 `memory.enable_memory_arena_shrinkage`로 계산 메모리만 반환 (둘 중 실측으로 선택) |
| `/health/ready` | 이미지 서버가 잠든 상태도 준비 완료로 본다 (`/v1/models` 응답 확인) |
| 테스트 | 렌더 순서가 누끼 → 깨움 → 생성 → 잠듦인지, 생성 실패에도 잠드는지, 초안은 깨우지 않는지 |

호스트 RAM: 기본 약 9.3 GiB + 잠든 이미지 가중치(pinned) 약 10 GiB = 약 19.3 GiB. 누끼가 GPU로 돌아가므로 CPU 누끼의 RSS 증가는 없어지고, Pod 한도 24 GiB 안에 든다.

## 5. 위험과 확인할 것

| 위험 | 확인 방법 |
| --- | --- |
| **bitsandbytes 4비트 모듈이 CPU↔GPU 이동 후 정상인지** (양자화 상태 텐서 이동) | Stage 배포 후 잠듦→깨움→생성 결과를 이전 생성컷과 비교. 실패 시 `_move_modules` 롤백 로그 확인 |
| 깨우기·잠들기 시간 | 로그에 단계별 시간 기록, 렌더 총 시간이 BE 300초 안인지 |
| 이 API는 사후 학습(post-training)용으로 추가된 기능 | 실패하면 렌더를 재시도 가능 오류(503)로 돌려 BE가 다시 요청하게 한다 |
| 잠들기 실패 시 다음 초안이 OOM | 잠들기 실패는 경고 로그 + 다음 렌더 시작 전에 다시 시도 |
| 누끼 세션을 렌더마다 만들면 로드 시간 증가 | 세션 유지 + 메모리 반환 옵션과 비교해 선택 |

## 6. 검증 계획 (적용 시)

1. 코드 변경 → GenAI CI → 머지·이미지 발행 → 인프라에 Stage 갱신 요청
2. Grafana: L40S 여유 메모리(DCGM)가 대기 시 약 20 GiB, 렌더 중에만 줄었다 돌아오는지
3. Loki: 렌더 200, CUDA OOM·CUBLAS 0건, 단계별 시간
4. 생성컷 품질: 잠듦/깨움 전후 같은 입력의 결과를 육안 확인
