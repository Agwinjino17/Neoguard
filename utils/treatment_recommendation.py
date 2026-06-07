def get_treatment_recommendation(risk_probability):
    """
    Determines Sepsis risk level and provides clinical recommendations.
    risk_probability: Float between 0 and 1 (or 0 and 100) representing risk %.
    """
    
    # Ensure it's treated as a percentage 0-100
    if risk_probability <= 1.0:
        risk_probability = risk_probability * 100
        
    risk_score = round(risk_probability, 2)
    
    if risk_score <= 30.0:
        level = "LOW"
        color = "Green"
        actions = [
            "Continue routine monitoring.",
            "Check vital signs every 4 hours."
        ]
    elif risk_score <= 60.0:
        level = "MODERATE"
        color = "Yellow"
        actions = [
            "Increase monitoring frequency.",
            "Perform infection screening.",
            "Check white blood cell count."
        ]
    elif risk_score <= 80.0:
        level = "HIGH"
        color = "Orange"
        actions = [
            "Start IV antibiotics.",
            "Monitor lactate levels.",
            "Administer fluid resuscitation.",
            "Notify attending physician."
        ]
    else:
        level = "CRITICAL"
        color = "Red"
        actions = [
            "Immediate ICU intervention.",
            "Broad-spectrum IV antibiotics.",
            "Aggressive fluid therapy.",
            "Continuous vital monitoring."
        ]
        
    return {
        "risk_score": risk_score,
        "risk_level": level,
        "color_indicator": color,
        "recommendations": actions
    }
