from src.crew import (
    question_crew,
    evaluation_crew
)

from src.config import COUNTRY_PROFILE


def select_country():

    countries = list(COUNTRY_PROFILE.keys())

    print("지원 국가를 선택하세요.\n")

    for idx, country in enumerate(countries, start=1):
        print(f"{idx}. {country}")

    while True:
        try:
            choice = int(input("\n번호를 입력하세요.\n> "))

            if 1 <= choice <= len(countries):
                return countries[choice - 1]

            print("올바른 번호를 입력해주세요.")

        except ValueError:
            print("숫자를 입력해주세요.")


def main():

    print("===== InterviewBridge AI =====\n")

    # ==========================================================
    # User Settings
    # ==========================================================

    native_language = input("모국어를 입력하세요. (예: Korean)\n> ").strip()

    country = select_country()

    profile = COUNTRY_PROFILE[country]

    target_language = profile["language"]
    culture = profile["culture"]
    style = profile["style"]

    print(f"\n선택한 국가 : {country}")
    print(f"면접 언어 : {target_language}")

    job = input("\n지원 직무를 입력하세요.\n> ").strip()

    # ==========================================================
    # Generate Interview Question
    # ==========================================================

    question_result = question_crew.kickoff(
        inputs={
            "job": job,
            "country": country,
            "native_language": native_language,
            "target_language": target_language,
            "culture": culture,
            "style": style
        }
    )

    question = str(question_result)

    print("\n==============================")
    print("면접 질문")
    print("==============================")
    print(question)

    # ==========================================================
    # User Answer
    # ==========================================================

    answer = input("\n답변을 입력하세요.\n> ")

    # ==========================================================
    # Evaluation
    # ==========================================================

    result = evaluation_crew.kickoff(
        inputs={
            "question": question,
            "answer": answer,
            "country": country,
            "native_language": native_language,
            "target_language": target_language,
            "culture": culture,
            "style": style
        }
    )

    print("\n==============================")
    print("최종 피드백")
    print("==============================")
    print(result)


if __name__ == "__main__":
    main()