package com.interviewbridge.backend.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
@NoArgsConstructor
public class EvaluationResponse {

    private int overallScore;

    private String summary;

    private String question;

    private String answer;

    private List<String> strengths;

    private List<String> weaknesses;

    private List<String> improvementTips;

    private String modelAnswerNative;

    private String modelAnswerTarget;

    // 다음 버전에서 사용
    private String nextQuestion;

    private String nextQuestionTranslation;

}