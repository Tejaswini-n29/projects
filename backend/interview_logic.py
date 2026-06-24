def evaluate_answer_quality(domain: str, question: str, answer: str) -> tuple[int, str]:
    """
    Evaluates the quality of the answer using basic NLP keyword matching.
    Returns a tuple of (score_out_of_10, feedback_string).
    """
    answer_lower = answer.lower()
    
    # Define keywords for specific domains/questions
    keywords = {
        "software_engineering": ["memory", "execution", "parallel", "concurrency", "shared", "resource", "lightweight", "independent", "context", "cpu"],
        "data_science": ["imputation", "mean", "median", "mode", "drop", "predict", "knn", "regression", "ignore", "distribution"],
        "marketing": ["kpi", "roi", "conversion", "engagement", "audience", "metrics", "analytics", "reach", "target", "budget"]
    }
    
    domain_keywords = keywords.get(domain, ["good", "experience", "team", "project", "result", "action", "situation"])
    
    # Count how many relevant keywords were mentioned
    matched_words = [kw for kw in domain_keywords if kw in answer_lower]
    match_count = len(matched_words)
    
    # Basic scoring logic
    base_score = 4 # minimum score for answering
    
    # Add points for length of answer (up to 3 points)
    words = answer.split()
    if len(words) > 50:
        base_score += 3
    elif len(words) > 20:
        base_score += 2
    elif len(words) > 5:
        base_score += 1
        
    # Add points for keywords (up to 3 points)
    if match_count >= 3:
        base_score += 3
    elif match_count >= 2:
        base_score += 2
    elif match_count >= 1:
        base_score += 1
        
    final_score = min(10, base_score)
    
    # Generate feedback
    if final_score >= 8:
        feedback = "Excellent answer! You covered the key concepts well and provided a detailed explanation."
    elif final_score >= 6:
        feedback = "Good answer, but it could be improved by mentioning more specific technical details or examples."
    else:
        feedback = "Your answer was a bit brief. Try to elaborate more and use industry-standard terminology."
        
    # Append matched keywords for transparency
    if matched_words:
        feedback += f" You correctly mentioned concepts like: {', '.join(matched_words)}."
        
    return final_score, feedback
