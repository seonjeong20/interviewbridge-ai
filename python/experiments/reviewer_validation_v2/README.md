# 평가 검증 파이프라인 개선 실험 (2차)

1차 실험([../reviewer_validation/](../reviewer_validation/))에서 확인된 기존 Reviewer의 한계를 고치는 구조를 구현하고, 같은 17개 케이스로 다시 측정한 실험입니다.
결과 해석은 [docs/ai-evaluation-validation-v2-report.md](../../../docs/ai-evaluation-validation-v2-report.md)에 있습니다.

서비스 코드(`python/src`, `python/api.py`, `python/schemas.py`)와 1차 실험 디렉터리는 수정하지 않습니다.
1차의 하네스, 테스트 케이스, 규칙 검사, Judge 프롬프트는 import해서 그대로 씁니다.

## 구조

```
Evaluator 출력
  → validator.py          코드   스키마, 점수 범위, 종합 점수 산술, 완전 중복
  → context_reviewer*.py  LLM    질문과 답변을 보고 발견 사항만 반환 (재작성 없음, 점수 제안 없음)
  → correction*.py        코드   게이트를 통과한 수정만 적용, 종합 점수는 코드로 재계산
  → Coach (운영 그대로)
```

두 판이 있습니다. 둘 다 결과를 보존했습니다.

| 판 | 파일 | 특징 |
| --- | --- | --- |
| v2.0 | `context_reviewer.py`, `correction.py`, `pipeline.py` | 문장 인용으로 근거를 제시. 인용이 원문과 일치해야 적용 |
| v2.1 | `context_reviewer_v21.py`, `correction_v21.py`, `pipeline_v21.py` | v2.0의 실패를 분석해 개정. 코드가 붙인 ID로 참조, 조각별 사실 확인 선행, 중복 묶음, 최대 2회 호출 |

## 파일

| 파일 | 역할 |
| --- | --- |
| `PREREGISTRATION.md` | 실행 전에 정한 지표, 동결한 프롬프트 해시, v2.1 개정 경위 |
| `prereg.py` | 케이스별 결함 위치 정의 (탐지 지표용) |
| `heldout_cases.json` | v2.0 동결 후 작성한 보조 케이스 8건 |
| `run_reviewer_comparison.py` | E1(17건 × 5회), E4(보조 8건 × 3회) |
| `run_coach_3way.py` | E2. 같은 평가를 네 경로로 Coach에 전달 (경로당 3회) |
| `run_natural_outputs.py` | E3. 1차에서 수집한 실제 Evaluator 출력 51건에 적용 |
| `build_adjudication.py` | 판독 결과에 근거 문장을 붙여 `ai_assisted_adjudication.json` 생성 |
| `analyze_v2.py` | API 호출 없이 CSV와 `results/summary.json` 생성 |
| `test_offline.py`, `test_offline_v21.py` | 코드 전용 부분(Validator, Correction)의 오프라인 검사 |

`ai_assisted_adjudication.json` 의 판정은 실험을 수행한 AI 코딩 에이전트가 출력을 읽고 내린 것입니다(AI-assisted adjudication). 사람이 검토한 결과가 아닙니다.

## 재실행

```bash
cd python/experiments/reviewer_validation_v2
PY=../../llm/bin/python

$PY test_offline.py && $PY test_offline_v21.py          # API 호출 없음

$PY run_reviewer_comparison.py main      > /dev/null     # v2.0
$PY run_reviewer_comparison.py heldout   > /dev/null
$PY run_natural_outputs.py               > /dev/null
$PY run_coach_3way.py                    > /dev/null     # 경로 A, B, C

export PIPELINE_VERSION=v21                              # v2.1 (결과는 *_v21.json)
$PY run_reviewer_comparison.py main      > /dev/null
$PY run_reviewer_comparison.py heldout   > /dev/null
$PY run_natural_outputs.py               > /dev/null
unset PIPELINE_VERSION
COACH_ARM_D=1 $PY run_coach_3way.py      > /dev/null     # 경로 D 추가

$PY build_adjudication.py && $PY analyze_v2.py
```

- 각 스크립트는 `results/` 에 이미 있는 실행분을 건너뜁니다.
- `results/` 를 비우고 다시 돌리면 `build_adjudication.py` 안의 판정표는 새 출력과 맞지 않습니다. 새 출력을 읽고 다시 판정해야 합니다.
- 추정 누적 비용이 `EXPERIMENT_BUDGET_USD`(기본 2.0)의 90%에 도달하면 다음 호출 전에 중단합니다.

## 이번 실행의 규모

호출 1,559회, 추정 비용 약 $1.14 (공개 단가 기준 추정, 실제 청구액은 확인하지 않음).
