package com.interviewbridge.backend.service;

import com.interviewbridge.backend.dto.EvaluationRequest;
import com.interviewbridge.backend.dto.EvaluationResponse;
import com.interviewbridge.backend.dto.QuestionRequest;
import com.interviewbridge.backend.dto.QuestionResponse;
import org.springframework.stereotype.Service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

@Service
public class InterviewServiceImpl implements InterviewService {

    private final RestTemplate restTemplate;
    private final String pythonApiUrl;

    public InterviewServiceImpl(
            RestTemplate restTemplate,
            @Value("${python.api.url}") String pythonApiUrl) {
        this.restTemplate = restTemplate;
        this.pythonApiUrl = pythonApiUrl;
    }

    @Override
    public QuestionResponse generateQuestion(QuestionRequest request) {
        return postForObject("/generate-question", request, QuestionResponse.class);
    }

    @Override
    public EvaluationResponse analyzeInterview(EvaluationRequest request) {
        return postForObject("/analyze", request, EvaluationResponse.class);
    }

    private <T> T postForObject(String path, Object request, Class<T> responseType) {
        try {
            T response = restTemplate.postForObject(pythonApiUrl + path, request, responseType);

            if (response == null) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_GATEWAY,
                        "Python API returned an empty response"
                );
            }

            return response;
        } catch (RestClientException exception) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "Failed to call Python API",
                    exception
            );
        }
    }
}
