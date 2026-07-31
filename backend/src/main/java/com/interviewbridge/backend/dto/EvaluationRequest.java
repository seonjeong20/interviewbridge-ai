package com.interviewbridge.backend.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class EvaluationRequest {
    private String job;
    private String country;
    private String nativeLanguage;
    private String question;
    private String answer;
}
