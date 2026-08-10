package com.interviewbridge.backend.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class EvaluationRequest {
    private String job;
    private String country;

    @JsonAlias("nativeLanguage")
    @JsonProperty("native_language")
    private String nativeLanguage;
    private String question;
    private String answer;
}
