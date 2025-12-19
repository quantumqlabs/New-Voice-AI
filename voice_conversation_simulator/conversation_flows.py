def get_conversation_flows():
    """Get conversation flows for each sector"""
    return {
        'banking': {
            'opening': "Good morning! This is Sarah from SDFC Bank. We're offering personal loans and credit cards with attractive interest rates. Would you be interested in exploring this today?",
            'interested': [
                "Wonderful! What type of financial product interests you most - personal loan or credit card?",
                "To check your eligibility, could you please let me know your monthly salary range?",
                "Do you currently have any existing loan EMIs?",
                "Based on your profile, you may be eligible. Would you like me to check exact terms?"
            ],
            'not_interested': [
                "I understand. Before I let you go, do you know any friends or relatives who might need a personal loan or credit card?",
                "Is there a better time when I could call you back to discuss our offers?"
            ],
            'closing': "Thank you for your time! We'll be in touch with the next steps. Have a great day!"
        },
        'real_estate': {
            'opening': "Hello! This is Ankita from City Developers. We're offering 1, 2, and 3 BHK apartments on ECR Road, Chennai, starting from 43 lakhs. Would you be interested in exploring this opportunity?",
            'interested': [
                "Wonderful! What type of property are you looking for - 1BHK, 2BHK, or 3BHK?",
                "What's your preferred budget range for the property?",
                "Would you like to schedule a site visit this weekend?",
                "Perfect! We have excellent options in your range. When would be convenient for a site visit?"
            ],
            'not_interested': [
                "No problem! Do you know any friends or family members looking to buy property in Chennai?",
                "Are you planning to buy in the future? I can keep you updated on new launches."
            ],
            'closing': "Thank you for your interest! We look forward to showing you our properties. Have a great day!"
        },
        'medical': {
            'opening': "Hello! This is Lisa from City Medical Center. We're reaching out about our health checkup packages and insurance verification services. Is this a convenient time to talk?",
            'interested': [
                "Great! Are you looking for routine health checkups or specific medical consultations?",
                "Do you currently have health insurance that we should verify?",
                "What age group are we planning this for - yourself or family members?",
                "Based on your needs, I can recommend the most suitable package. Shall I schedule a consultation?"
            ],
            'not_interested': [
                "I understand. Health is important though - do you know anyone who might benefit from our services?",
                "Would you prefer if I called back during a different season for your annual checkup?"
            ],
            'closing': "Thank you for considering our health services. We'll follow up as discussed. Take care!"
        }
    }