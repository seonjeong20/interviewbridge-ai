# Reviewer / Self-Consistency 검증 실험

InterviewBridge의 평가 파이프라인(Analyzer → Evaluator → Reviewer → Coach)에서
Reviewer가 실제로 무엇을 하는지, Self-Consistency와는 무엇이 다른지를 실행으로 확인하는 실험 코드입니다.
결과 해석은 [docs/ai-evaluation-validation-report.md](../../../docs/ai-evaluation-validation-report.md)에 있습니다.

서비스 코드(`python/src`, `python/api.py`, `python/schemas.py`)는 수정하지 않습니다.
운영 Agent와 운영 Task 프롬프트를 그대로 import해서 쓰고, 앞 단계 출력을 고정값으로 주입하는 배선만 실험 코드에서 새로 만듭니다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `test_cases.json` | 합성 테스트 케이스 17건 (질문, 답변, 손으로 쓴 Evaluator 출력, 삽입한 오류, 기대 동작, 규칙 검사용 필드) |
| `harness.py` | 운영 단계 1개를 고정 컨텍스트로 실행, 호출별 토큰·시간 기록, 예산 차단, LLM Judge 호출 |
| `exp1_reviewer.py` | 실험 1. 손으로 쓴 평가를 Reviewer에 케이스당 5회 통과 |
| `exp2_coach_ab.py` | 실험 2. 같은 평가를 `Coach` 와 `Reviewer → Coach` 에 각각 2회 통과 |
| `exp3_self_consistency.py` | 실험 3. 같은 답변을 Evaluator에 3회 평가, 종합, 그 자연 출력을 Reviewer에 통과 |
| `run_production_baseline.py` | 수정하지 않은 운영 `evaluation_crew` 를 그대로 실행 (호출 수, 응답 시간 기준값) |
| `manual_adjudication.json` | 실험 1 전체 85회, 실험 2 중 28회 출력을 직접 읽고 내린 판정과 근거 인용 |
| `analyze.py` | API 호출 없이 CSV와 `results/summary.json` 생성 |
| `results/` | 원본 출력(JSON), 케이스별 CSV, 호출 원장(`call_ledger.jsonl`) |

## 재실행

```bash
cd python/experiments/reviewer_validation
PY=../../llm/bin/python            # 프로젝트 가상환경. python/.env 의 OPENAI_API_KEY 를 사용

$PY exp1_reviewer.py         > /dev/null   # Agent가 verbose=True 라서 stdout이 많습니다
$PY exp2_coach_ab.py         > /dev/null   # exp1 결과(rep 1)를 입력으로 사용하므로 exp1 다음에 실행
$PY exp3_self_consistency.py > /dev/null
$PY run_production_baseline.py TC-01 TC-04 TC-07 > /dev/null
$PY analyze.py
```

- 각 스크립트는 `results/` 에 이미 있는 실행분을 건너뜁니다. 처음부터 다시 돌리려면 `results/` 를 비우세요.
- `results/` 를 비우면 `manual_adjudication.json` 의 판정은 새 출력과 맞지 않게 됩니다. 새 출력을 읽고 다시 작성해야 `analyze.py` 가 의미 있는 값을 냅니다.
- LLM 출력은 temperature 0.3으로 생성되므로 재실행하면 수치가 조금 달라질 수 있습니다.

## 환경 변수

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `EXPERIMENT_BUDGET_USD` | `2.0` | 추정 누적 비용이 이 값의 90%에 도달하면 다음 호출 전에 중단 |
| `EXP1_REPS` | `5` | 실험 1의 케이스당 반복 횟수 |
| `JUDGE_MODELS` | `gpt-4.1-mini,gpt-4o-mini` | LLM Judge 모델 목록 |

## 이번 실행의 규모

호출 703회(API 요청 715건), 추정 비용 약 $0.53. 단가는 `harness.py` 의 `PRICES` 에 적은 공개 가격 기준 추정치이며 실제 청구액은 확인하지 않았습니다.
