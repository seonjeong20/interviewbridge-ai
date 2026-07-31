package com.interviewbridge.backend.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class QuestionRequest {
    
    private String job;
    private String country;
    private String nativeLanguage;
    
}
