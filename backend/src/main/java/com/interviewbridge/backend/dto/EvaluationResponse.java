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
    private String question;
    private String answer;

    private Evaluation evaluation;
    private Coaching coaching;

    @Getter
    @Setter
    @NoArgsConstructor
    public static class Evaluation {
        private String summary;
        private EvaluationScores evaluationScores;
        private List<String> strengths;
        private List<String> weaknesses;
    }

    @Getter
    @Setter
    @NoArgsConstructor
    public static class EvaluationScores {
        private ScoreFeedback logicalThinking;
        private ScoreFeedback specificity;
        private ScoreFeedback communication;
        private ScoreFeedback jobFit;
        private ScoreFeedback starStructure;
    }

    @Getter
    @Setter
    @NoArgsConstructor
    public static class ScoreFeedback {
        private int score;
        private String feedback;
    }

    @Getter
    @Setter
    @NoArgsConstructor
    public static class Coaching {
        private String overallSummary;
        private List<String> improvementTips;
        private BilingualText modelAnswer;
        private BilingualText nextPracticeQuestion;
    }

    @Getter
    @Setter
    @NoArgsConstructor
    public static class BilingualText {
        private String nativeLanguage;
        private String targetLanguage;
    }
}
