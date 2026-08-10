package com.interviewbridge.backend.controller;

import com.interviewbridge.backend.dto.EvaluationRequest;
import com.interviewbridge.backend.dto.EvaluationResponse;
import com.interviewbridge.backend.dto.QuestionRequest;
import com.interviewbridge.backend.dto.QuestionResponse;
import com.interviewbridge.backend.service.InterviewService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/interview")
public class InterviewController {

    private final InterviewService interviewService;

    public InterviewController(InterviewService interviewService) {
        this.interviewService = interviewService;
    }

    @PostMapping("/generate-question")
    public QuestionResponse generateQuestion(@RequestBody QuestionRequest request) {
        return interviewService.generateQuestion(request);
    }

    @PostMapping("/analyze")
    public EvaluationResponse analyzeInterview(@RequestBody EvaluationRequest request) {
        return interviewService.analyzeInterview(request);
    }
}
