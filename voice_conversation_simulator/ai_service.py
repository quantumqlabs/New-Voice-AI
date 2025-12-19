import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime
from conversation_flows import get_conversation_flows
from functools import lru_cache

load_dotenv()

class AIConversationService:
    """Optimized AI service with structured conversation flow"""

    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4o-mini"
            print(f"✅ Using OpenAI API (model: {self.model})")
        else:
            self.client = None
            print("⚠️ No OPENAI_API_KEY found. Using fallback responses.")

        self.agent_personas = {
            'banking': {
                'name': 'Sarah',
                'company': 'SDFC Bank',
                'personality': 'professional, trustworthy, financially knowledgeable',
                'expertise': 'personal loans, credit cards, banking services'
            },
            'real_estate': {
                'name': 'Ankita',
                'company': 'City Developers',
                'personality': 'enthusiastic, helpful, property expert',
                'expertise': 'residential properties, real estate investment'
            },
            'medical': {
                'name': 'Lisa',
                'company': 'City Medical Center',
                'personality': 'caring, empathetic, health-focused',
                'expertise': 'health checkups, medical consultations, preventive care'
            }
        }
        
        # Structured conversation stages
        self.conversation_stages = {
            'banking': [
                'identify_need',
                'check_eligibility',
                'explain_process',
                'schedule_meeting',
                'confirm_next_steps'
            ],
            'real_estate': [
                'identify_need',
                'budget_discussion',
                'property_details',
                'schedule_site_visit',
                'confirm_next_steps'
            ],
            'medical': [
                'identify_need',
                'gather_details',
                'explain_service',
                'schedule_appointment',
                'confirm_next_steps'
            ]
        }

    def generate_response(self, customer_response, conversation_history, customer_info, conversation_state, customer_preference=None, current_stage=None):
        """Generate AI responses with structured flow"""
        if not self.client:
            return self._get_fallback_response(customer_response, customer_info['sector'])

        sector = customer_info['sector']
        agent = self.agent_personas[sector]

        # Determine current conversation stage
        if current_stage is None:
            current_stage = self._determine_stage(conversation_history, sector, customer_preference)

        # Truncate history to last 6 messages
        trimmed_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history

        messages = self._build_structured_context(
            customer_response, trimmed_history, customer_info, conversation_state, 
            agent, customer_preference, current_stage
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=100,
                temperature=0.7,
                presence_penalty=0.3,
                frequency_penalty=0.2,
                timeout=8
            )

            ai_response = response.choices[0].message.content.strip()
            
            # Quick pattern-based analysis
            quick_analysis = self._quick_analyze(ai_response, customer_response, trimmed_history, current_stage)
            
            if quick_analysis:
                return {
                    'ai_response': ai_response,
                    'analysis': quick_analysis,
                    'current_stage': current_stage
                }
            
            # Detailed analysis
            analysis = self._analyze_response(ai_response, customer_response, trimmed_history, sector, current_stage)
            
            return {
                'ai_response': ai_response,
                'analysis': analysis,
                'current_stage': current_stage
            }

        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return self._get_fallback_response(customer_response, sector)

    def _determine_stage(self, conversation_history, sector, customer_preference):
        """Determine what stage the conversation is at"""
        history_text = ' '.join(conversation_history).lower()
        
        if sector == 'banking':
            if 'meeting' in history_text or 'appointment' in history_text or 'callback' in history_text:
                return 'schedule_meeting'
            elif 'document' in history_text or 'application' in history_text or 'process' in history_text:
                return 'explain_process'
            elif 'salary' in history_text or 'income' in history_text or 'eligible' in history_text:
                return 'check_eligibility'
            elif customer_preference:
                return 'check_eligibility'
            else:
                return 'identify_need'
        
        elif sector == 'real_estate':
            if 'site visit' in history_text or 'visit' in history_text:
                return 'schedule_site_visit'
            elif 'budget' in history_text or 'price' in history_text or 'lakh' in history_text:
                return 'property_details'
            elif customer_preference:
                return 'budget_discussion'
            else:
                return 'identify_need'
        
        elif sector == 'medical':
            if 'appointment' in history_text or 'schedule' in history_text:
                return 'schedule_appointment'
            elif 'checkup' in history_text or 'consultation' in history_text:
                return 'gather_details'
            else:
                return 'identify_need'
        
        return 'identify_need'

    def _build_structured_context(self, customer_response, conversation_history, customer_info, conversation_state, agent, customer_preference, current_stage):
        """Build context with structured stage guidance"""
        sector = customer_info['sector']
        customer_name = customer_info['name']
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Stage-specific instructions
        stage_instructions = self._get_stage_instructions(sector, current_stage, customer_preference)

        system_prompt = f"""You are {agent['name']}, {agent['personality']} representative from {agent['company']}.
Date: {current_date}. Customer: {customer_name}. Sector: {sector}.

YOUR IDENTITY:
- You are {agent['name']} from {agent['company']}
- If asked "who are you" or "what's your name", respond: "I'm {agent['name']} from {agent['company']}"
- If asked about your location or company, respond naturally

CONVERSATION STAGE: {current_stage}
{stage_instructions}

CRITICAL RULES:
1. Answer ANY question the customer asks (math, general knowledge, etc.)
2. After answering off-topic questions, SMOOTHLY return to the main conversation
3. Keep responses SHORT (2-3 sentences MAX)
4. Follow the conversation flow toward scheduling a meeting/appointment
5. Be helpful and informative, but guide toward next steps
6. IMPORTANT: If you've already scheduled a meeting/callback with specific date/time, DO NOT ask to schedule again
7. After customer confirms scheduled meeting with "OK" or "sure", simply thank them - NO MORE QUESTIONS
8. Once meeting is confirmed, say "Have a great day" and STOP asking questions

Recent conversation:
{json.dumps(conversation_history[-4:], indent=2)}

Customer just said: "{customer_response}"

Respond naturally. If meeting already scheduled with time, just thank them warmly and end. If it's off-topic, answer briefly then redirect."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for entry in conversation_history[-4:]:
            if entry.startswith("AI Agent:"):
                messages.append({"role": "assistant", "content": entry.replace("AI Agent: ", "")})
            elif entry.startswith("Customer:"):
                messages.append({"role": "user", "content": entry.replace("Customer: ", "")})
        
        messages.append({"role": "user", "content": customer_response})
        return messages

    def _get_stage_instructions(self, sector, stage, customer_preference):
        """Get specific instructions for each conversation stage"""
        
        if sector == 'banking':
            instructions = {
                'identify_need': """
GOAL: Find out what they need (personal loan or credit card).
NEXT: Once identified, move to eligibility check.
ASK: "What interests you - personal loan or credit card?"
                """,
                'check_eligibility': f"""
GOAL: Check their eligibility (salary, existing loans).
PRODUCT: {customer_preference or 'banking product'}
ASK: "What's your monthly salary range?" or "Do you have any existing loan EMIs?"
NEXT: After getting details, explain the application process.
                """,
                'explain_process': f"""
GOAL: Explain what documents they need and the application process.
TELL THEM: "You'll need: ID proof, salary slips (3 months), bank statements (6 months)"
NEXT: Offer to schedule a meeting/callback for the application.
                """,
                'schedule_meeting': f"""
GOAL: Schedule a meeting or callback to complete the application.
ASK: "When would be convenient for our executive to call you?" or "What time works best?"
OFFER: Tomorrow, this week, specific date/time
CRITICAL: Once customer gives specific time, say "Perfect! I've scheduled a callback for [TIME]. Our executive will call you then. Have a great day!" and STOP.
                """,
                'confirm_next_steps': """
GOAL: Confirm everything and end the call professionally.
SAY: "Perfect! Our executive will call you on [date/time]. Have a great day!"
CRITICAL: This is the FINAL message. Do NOT ask any follow-up questions. Just confirm and end warmly.
                """
            }
        
        elif sector == 'real_estate':
            instructions = {
                'identify_need': """
GOAL: Find out what type of property they want (1/2/3 BHK).
ASK: "What type of property are you looking for - 1BHK, 2BHK, or 3BHK?"
NEXT: Once identified, discuss budget.
                """,
                'budget_discussion': """
GOAL: Understand their budget range.
ASK: "What's your budget range for the property?"
NEXT: Move to property details and site visit.
                """,
                'property_details': """
GOAL: Share property details matching their needs.
TELL: Location, price, amenities, availability
NEXT: Offer to schedule a site visit.
                """,
                'schedule_site_visit': """
GOAL: Schedule a site visit.
ASK: "When would you like to visit the property? This weekend or next week?"
OFFER: Specific dates and times
NEXT: Once confirmed, END gracefully.
                """,
                'confirm_next_steps': """
GOAL: Confirm the site visit and end positively.
SAY: "Great! We'll arrange the site visit on [date]. Our representative will contact you."
IMPORTANT: After confirmation, say "Have a great day!" and STOP.
                """
            }
        
        elif sector == 'medical':
            instructions = {
                'identify_need': """
GOAL: Find out what service they need (checkup, consultation, etc.).
ASK: "What service are you interested in - routine checkup or specific consultation?"
NEXT: Gather details about their needs.
                """,
                'gather_details': """
GOAL: Understand their specific needs (age, concerns, urgency).
ASK: "Do you have any specific health concerns?" or "Is this for yourself or family?"
NEXT: Explain the service/package.
                """,
                'explain_service': """
GOAL: Explain what the service includes.
TELL: What's covered, duration, cost, benefits
NEXT: Offer to schedule an appointment.
                """,
                'schedule_appointment': """
GOAL: Schedule the appointment.
ASK: "When would be convenient? We have slots tomorrow at 10 AM, 2 PM, or 5 PM."
OFFER: Specific dates and times
NEXT: Once confirmed, END gracefully.
                """,
                'confirm_next_steps': """
GOAL: Confirm the appointment and end positively.
SAY: "Perfect! Your appointment is scheduled for [date/time]. We'll send a confirmation."
IMPORTANT: After confirmation, say "Take care!" and STOP asking questions.
                """
            }
        
        else:
            instructions = {'identify_need': 'Start the conversation and understand customer needs.'}
        
        return instructions.get(stage, '')

    def _quick_analyze(self, ai_response, customer_response, conversation_history, current_stage):
        """Fast pattern-based analysis"""
        response_lower = customer_response.lower().strip()
        
        # Check if we're at scheduling stage and customer confirmed
        if current_stage in ['schedule_meeting', 'schedule_site_visit', 'schedule_appointment']:
            confirmation_words = ['yes', 'sure', 'ok', 'okay', 'tomorrow', 'today', 'this week', 'next week']
            has_time = any(word in response_lower for word in ['morning', 'afternoon', 'evening', 'am', 'pm', '10', '11', '2', '3', '4', '5'])
            
            if any(word in response_lower for word in confirmation_words) or has_time:
                return {
                    'interest_level': 'High',
                    'continue_conversation': False,
                    'end_reason': 'meeting_scheduled',
                    'lead_score': 9,
                    'meeting_scheduled': True
                }
        
        # Explicit disinterest
        if any(phrase in response_lower for phrase in ['not interested', 'no thanks', 'no thank you', "don't want"]):
            return {
                'interest_level': 'Not Interested',
                'continue_conversation': False,
                'end_reason': 'explicit_disinterest',
                'lead_score': 2
            }
        
        # Explicit goodbye
        if any(phrase in response_lower for phrase in ['bye', 'goodbye', 'talk later']):
            return {
                'interest_level': 'Medium',
                'continue_conversation': False,
                'end_reason': 'explicit_goodbye',
                'lead_score': 5
            }
        
        # High engagement signals
        if '?' in customer_response or len(customer_response.split()) > 10:
            return {
                'interest_level': 'High',
                'continue_conversation': True,
                'end_reason': None,
                'lead_score': 8
            }
        
        return None

    def _analyze_response(self, ai_response, customer_response, conversation_history, sector, current_stage):
        """Analyze conversation with stage awareness"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        analysis_prompt = f"""Analyze this {sector} conversation at stage: {current_stage}

Customer said: "{customer_response}"
AI said: "{ai_response}"
Recent history: {json.dumps(conversation_history[-4:], indent=2)}

RULES:
1. If at 'schedule_meeting/appointment/site_visit' stage AND customer confirmed time/date, END conversation
2. If customer asked specific question (math, general), CONTINUE (they'll ask more or return to topic)
3. END only if: explicit goodbye, "not interested" repeatedly, OR meeting/appointment scheduled
4. CONTINUE if: questions asked, gathering information, explaining process

Respond ONLY with JSON:
{{"interest_level": "High", "continue_conversation": true, "end_reason": null, "meeting_scheduled": false}}"""

        try:
            analysis_response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": analysis_prompt}],
                max_tokens=60,
                temperature=0.3,
                response_format={"type": "json_object"},
                timeout=5
            )
            content = analysis_response.choices[0].message.content.strip()
            analysis = json.loads(content)
            
            # Override: If at scheduling stage and got confirmation, mark as scheduled
            if current_stage in ['schedule_meeting', 'schedule_site_visit', 'schedule_appointment']:
                response_lower = customer_response.lower()
                if any(word in response_lower for word in ['yes', 'ok', 'sure', 'tomorrow', 'today', 'morning', 'afternoon', 'am', 'pm']):
                    analysis['meeting_scheduled'] = True
                    analysis['continue_conversation'] = False
                    analysis['interest_level'] = 'High'
            
            return {
                'interest_level': analysis.get('interest_level', 'Medium'),
                'continue_conversation': analysis.get('continue_conversation', True),
                'end_reason': analysis.get('end_reason', None),
                'lead_score': self._calculate_lead_score(analysis.get('interest_level', 'Medium')),
                'meeting_scheduled': analysis.get('meeting_scheduled', False)
            }
        except Exception as e:
            print(f"Error analyzing response: {e}")
            return {
                'interest_level': 'Medium',
                'continue_conversation': True,
                'end_reason': None,
                'lead_score': 5,
                'meeting_scheduled': False
            }
    
    def _calculate_lead_score(self, interest_level):
        """Calculate lead score"""
        scores = {
            'High': 8,
            'Medium': 6,
            'Low': 4,
            'Not Interested': 2,
            'Unknown': 5
        }
        return scores.get(interest_level, 5)

    def generate_opening_message(self, customer_info):
        """Generate opening message"""
        agent = self.agent_personas[customer_info['sector']]
        customer_name = customer_info['name']
        
        if not self.client:
            return self._fallback_opening(customer_info)

        system_prompt = f"""You are {agent['name']} from {agent['company']}.
Write ONE warm opening line to {customer_name} about {agent['expertise']}.
Keep it under 25 words. Be natural and friendly."""

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Greet {customer_name}"}
                ],
                max_tokens=60,
                temperature=0.8,
                timeout=5
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating opening: {e}")
            return self._fallback_opening(customer_info)

    def _fallback_opening(self, customer_info):
        """Fallback opening"""
        sector = customer_info['sector']
        agent = self.agent_personas[sector]
        name = customer_info.get('name', 'there')
        fallbacks = {
            'banking': f"Hi {name}, this is {agent['name']} from {agent['company']}. We have great loan and credit card offers today—interested?",
            'real_estate': f"Hi {name}, {agent['name']} from {agent['company']}. We have new residential projects—want details?",
            'medical': f"Hello {name}, {agent['name']} from {agent['company']}. We're offering health checkups—would you like to know more?"
        }
        return fallbacks.get(sector, f"Hello {name}, this is {agent['name']} from {agent['company']}.")

    def _get_fallback_response(self, customer_response, sector):
        """Fallback response"""
        return {
            'ai_response': f"Thank you for that. Could you tell me more about what you're looking for in {sector} services?",
            'analysis': {
                'interest_level': 'Medium',
                'lead_score': 5,
                'continue_conversation': True,
                'end_reason': None,
                'meeting_scheduled': False
            },
            'current_stage': 'identify_need'
        }