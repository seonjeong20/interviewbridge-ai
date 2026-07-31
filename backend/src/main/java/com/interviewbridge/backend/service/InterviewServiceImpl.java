package com.interviewbridge.backend.service;

import com.interviewbridge.backend.dto.EvaluationRequest;
import com.interviewbridge.backend.dto.EvaluationResponse;
import com.interviewbridge.backend.dto.QuestionRequest;
import com.interviewbridge.backend.dto.QuestionResponse;
import org.springframework.stereotype.Service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.client.RestTemplate;

@Service
public class InterviewServiceImpl implements InterviewService {

    private final RestTemplate restTemplate;

    @Value("${python.api.url}")
    private String pythonApiUrl;

    public InterviewServiceImpl(RestTemplate restTemplate){
        this.restTemplate = restTemplate;
    }

    @Override
    public QuestionResponse generateQuestion(QuestionRequest request) {

        // TODO
        return null;

    }

    @Override
    public EvaluationResponse analyzeInterview(EvaluationRequest request) {

        // TODO
        return null;

    }

}