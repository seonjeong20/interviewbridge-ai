package com.interviewbridge.backend.service;

import com.interviewbridge.backend.dto.EvaluationRequest;
import com.interviewbridge.backend.dto.EvaluationResponse;
import com.interviewbridge.backend.dto.QuestionRequest;
import com.interviewbridge.backend.dto.QuestionResponse;

public interface InterviewService {

    QuestionResponse generateQuestion(QuestionRequest request);
    EvaluationResponse analyzeInterview(EvaluationRequest request);
    
}
