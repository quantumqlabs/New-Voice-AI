from datetime import datetime, timedelta
import time
from ai_service import AIConversationService
from conversation_flows import get_conversation_flows

class VoiceConversationSimulator:
    """Enhanced AI-powered voice conversation simulator with empathy and realism"""
    
    def __init__(self, customer_name, phone_number, sector):
        self.customer_name = customer_name
        self.phone_number = phone_number
        self.sector = sector
        self.conversation_log = []
        self.start_time = datetime.now()
        self.end_time = None
        self.customer_interest_level = 'Unknown'
        self.lead_score = 5
        self.next_action = 'None'
        self.action_assignee = 'None'
        self.call_status = 'In Progress'
        self.remarks = ''
        self.action_required = 'No'
        self.conversation_state = 'opening'
        self.total_interactions = 0
        self.application_initiated = False
        self.customer_preference = None
        self.disinterest_count = 0
        self.closing_sent = False
        
        self.questions_asked = []
        self.meaningful_responses_count = 0
        self.last_ai_message = ""
        self.explicit_confirmation_received = False
        self.consecutive_simple_acks = 0
        self.meeting_scheduled_with_time = False
        
        # NEW: Track if we've asked substantive questions yet
        self.substantive_questions_asked = 0
        
        # NEW: Track consecutive closing messages to prevent loops
        self.consecutive_closing_messages = 0
        
        self.ai_service = AIConversationService()
        
        self.customer_info = {
            'name': customer_name,
            'phone': phone_number,
            'sector': sector
        }
    
    def get_opening_message(self):
        """Generate personalized AI opening message"""
        opening = self.ai_service.generate_opening_message(self.customer_info)
        self.last_ai_message = opening
        self.conversation_log.append(f"AI Agent: {opening}")
        return opening
    
    def get_next_ai_response(self, customer_response):
        if self.closing_sent:
            print(f"[DEBUG] Closing message already sent, ignoring response: {customer_response}")
            return None

        self.conversation_log.append(f"Customer: {customer_response}")
        self.total_interactions += 1
        
        # Track substantive questions (not just opening)
        if self.total_interactions > 1 and '?' in self.last_ai_message:
            substantive_questions = [
                'what type', 'what service', 'which', 'when would', 'could you',
                'do you have', 'are you looking', 'what\'s your', 'what is your',
                'any specific', 'for yourself', 'what age', 'what concerns'
            ]
            if any(q in self.last_ai_message.lower() for q in substantive_questions):
                self.substantive_questions_asked += 1
                print(f"[DEBUG] Substantive questions asked: {self.substantive_questions_asked}")
        
        print(f"[DEBUG] Processing customer response: {customer_response}")
        print(f"[DEBUG] Total interactions: {self.total_interactions}")
        print(f"[DEBUG] Substantive questions: {self.substantive_questions_asked}")
        print(f"[DEBUG] Meeting scheduled flag: {self.meeting_scheduled_with_time}")
        print(f"[DEBUG] Last AI message: {self.last_ai_message[:50]}...")
        
        # CRITICAL: If meeting already scheduled AND AI already gave closing ("Have a great day"), END immediately
        if self.meeting_scheduled_with_time:
            closing_indicators = ['have a great day', 'have a wonderful day', 'take care', 'talk to you soon', 
                                'our executive will call you', 'looking forward to seeing you', 
                                'see you on', 'see you this', 'see you next']
            last_ai_had_closing = any(phrase in self.last_ai_message.lower() for phrase in closing_indicators)
            
            # SPECIAL CHECK: If customer just said simple ack after closing, END NOW
            simple_acks = ['ok', 'okay', 'sure', 'alright', 'yes', 'yeah', 'thank you', 'thanks', 'bye', 'ok.', 'okay.', 'sure.', 'thank you.', 'thanks.']
            customer_lower = customer_response.lower().strip()
            
            # Check if we're in post-closing loop (AI said closing AND customer is just acknowledging)
            if last_ai_had_closing and customer_lower in simple_acks:
                print(f"[DEBUG] ✅ Meeting scheduled + Customer acknowledged closing - ENDING NOW")
                self.end_time = datetime.now()
                self.closing_sent = True
                self.set_final_actions()
                # Don't send another message, just return None to end
                return None
            
            # NEW: If AI said "You're welcome! Have a great day!" - this means we're ALREADY in closing loop
            if "you're welcome" in self.last_ai_message.lower() and last_ai_had_closing:
                print(f"[DEBUG] ✅ AI already responded to thank you - ENDING NOW")
                self.end_time = datetime.now()
                self.closing_sent = True
                self.set_final_actions()
                return None
        
        # Track consecutive simple acknowledgments
        if customer_response.lower().strip() in ['ok', 'okay', 'sure', 'alright', 'yes', 'yeah', 'thank you', 'thanks']:
            self.consecutive_simple_acks += 1
        else:
            self.consecutive_simple_acks = 0
        
        print(f"[DEBUG] Consecutive simple acks: {self.consecutive_simple_acks}")
        
        # Check for explicit disinterest FIRST - highest priority
        if self._check_for_explicit_disinterest(customer_response):
            self.end_time = datetime.now()
            self.customer_interest_level = 'Not Interested'
            closing_message = get_conversation_flows()[self.sector]['closing']
            self.conversation_log.append(f"AI Agent: {closing_message}")
            self.closing_sent = True
            self.set_final_actions()
            print(f"[DEBUG] Conversation ending - Customer explicitly not interested")
            return closing_message
        
        # Check for explicit goodbye
        if self._check_for_explicit_end(customer_response):
            self.end_time = datetime.now()
            closing_message = get_conversation_flows()[self.sector]['closing']
            self.conversation_log.append(f"AI Agent: {closing_message}")
            self.closing_sent = True
            self.set_final_actions()
            print(f"[DEBUG] Conversation ending - User said goodbye")
            return closing_message
        
        # Check for inconvenience/busy - but DON'T end yet, generate response first
        is_inconvenient = self._check_for_inconvenience(customer_response)
        
        if self._is_meaningful_response(customer_response):
            self.meaningful_responses_count += 1
            print(f"[DEBUG] Meaningful responses count: {self.meaningful_responses_count}")
        
        self._extract_customer_preference(customer_response)
        
        # If customer is busy/inconvenient, generate a polite closing
        if is_inconvenient:
            self.end_time = datetime.now()
            self.customer_interest_level = 'Medium'
            closing_message = self._generate_follow_up_closing(customer_response)
            self.conversation_log.append(f"AI Agent: {closing_message}")
            self.closing_sent = True
            self.set_final_actions()
            print(f"[DEBUG] Conversation ending - Customer expressed inconvenience")
            return closing_message

        # Generate AI response for normal conversation
        ai_result = self.ai_service.generate_response(
            customer_response=customer_response,
            conversation_history=self.conversation_log,
            customer_info=self.customer_info,
            conversation_state=self.conversation_state,
            customer_preference=self.customer_preference
        )
        
        ai_response = ai_result['ai_response']
        analysis = ai_result['analysis']
        
        self.last_ai_message = ai_response
        if '?' in ai_response:
            self.questions_asked.append(ai_response)
        
        # Check if AI explicitly scheduled a meeting with time
        self._check_meeting_scheduled(ai_response, customer_response)
        
        # CRITICAL: If AI just confirmed scheduling with "Have a great day", mark as closing sent
        if self.meeting_scheduled_with_time:
            closing_phrases = ['have a great day', 'take care', 'have a wonderful day', 'talk to you soon',
                             'looking forward to seeing you', 'see you on', 'see you this']
            if any(phrase in ai_response.lower() for phrase in closing_phrases):
                print(f"[DEBUG] ✅ AI confirmed scheduling and said goodbye - Setting closing_sent flag")
                self.conversation_log.append(f"AI Agent: {ai_response}")
                return ai_response
        
        self.customer_interest_level = analysis['interest_level']
        self.lead_score = analysis.get('lead_score', self.lead_score)
        
        print(f"[DEBUG] AI Analysis - Interest: {self.customer_interest_level}, Score: {self.lead_score}")
        print(f"[DEBUG] Continue conversation: {analysis['continue_conversation']}")
        print(f"[DEBUG] Meeting scheduled: {self.meeting_scheduled_with_time}")
        
        self._update_conversation_state(analysis)
        should_end_conversation = self._should_end_conversation(analysis, customer_response)
        
        if should_end_conversation:
            self.end_time = datetime.now()
            closing_message = get_conversation_flows()[self.sector]['closing']
            self.conversation_log.append(f"AI Agent: {closing_message}")
            self.closing_sent = True
            self.set_final_actions()
            print(f"[DEBUG] Conversation ending - AI decided to end. Reason: {analysis.get('end_reason', 'natural')}")
            return closing_message
        
        self.conversation_log.append(f"AI Agent: {ai_response}")
        return ai_response
    
    def _check_meeting_scheduled(self, ai_response, customer_response):
        """Check if meeting was explicitly scheduled with specific time - FIXED FOR REAL ESTATE"""
        ai_lower = ai_response.lower()
        customer_lower = customer_response.lower()
        
        # Check if AI confirmed scheduling with specific time
        scheduling_confirmations = [
            'scheduled the call', 'scheduled a callback', 'scheduled for tomorrow',
            'appointment is scheduled', 'i\'ve scheduled', 'meeting is set',
            'we\'re all set', 'callback for you tomorrow', 'i have scheduled',
            'scheduled your', 'booked for', 'appointment for', 'call for you',
            'set up for', 'confirmed for', 'scheduled your appointment',
            'your appointment is', 'i\'ve booked',
            # REAL ESTATE SPECIFIC:
            'looking forward to seeing you', 'see you on', 'see you this',
            'site visit is scheduled', 'visit is confirmed', 'property visit'
        ]
        
        # Check if customer provided specific time - ENHANCED FOR REAL ESTATE
        time_indicators = [
            '10 am', '11 am', '2 pm', '3 pm', '4 pm', '5 pm', '6 pm','7 pm','9 am','12 pm','1 pm','8 am','9 pm',
            'morning', 'afternoon', 'evening', 
            'tomorrow','today','saturday' 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'this week', 'next week', 'weekend',
            # REAL ESTATE SPECIFIC DAY+TIME:
            'thursday at', 'friday at', 'saturday at', 'sunday at',
            'monday at', 'tuesday at', 'wednesday at'
        ]
        
        has_scheduling = any(phrase in ai_lower for phrase in scheduling_confirmations)
        has_time = any(time in customer_lower for time in time_indicators) or any(time in ai_lower for time in time_indicators)
        
        # SPECIAL CHECK FOR REAL ESTATE: "Thursday at 3 PM" pattern
        day_time_pattern = ['thursday at', 'friday at', 'saturday at', 'sunday at', 
                           'monday at', 'tuesday at', 'wednesday at']
        customer_has_day_time = any(pattern in customer_lower for pattern in day_time_pattern)
        
        if has_scheduling and has_time:
            self.meeting_scheduled_with_time = True
            self.application_initiated = True
            print(f"[DEBUG] ✅ Meeting scheduled with specific time detected!")
        elif customer_has_day_time:
            # Customer gave specific day+time, mark as scheduled
            self.meeting_scheduled_with_time = True
            self.application_initiated = True
            print(f"[DEBUG] ✅ Customer provided specific day+time - Meeting scheduled!")
    
    def _check_for_explicit_disinterest(self, customer_response):
        """Check if customer explicitly says they're not interested"""
        response_lower = customer_response.lower().strip()
        
        # Strong disinterest phrases
        explicit_disinterest = [
            'not interested', "i'm not interested", "i am not interested",
            "not interest", "no interest", "no thanks", "no thank you",
            "don't want", "dont want", "do not want", "not for me",
            "never interested"
        ]
        
        # Check if any explicit disinterest phrase is present
        if any(phrase in response_lower for phrase in explicit_disinterest):
            if "not busy" in response_lower or "i'm not busy" in response_lower:
                return True
            return True
        
        return False
        
    def _is_meaningful_response(self, response):
        """Check if response is meaningful (not just yes/no/ok)"""
        response_lower = response.lower().strip()
        simple_affirmations = ['yes', 'yeah', 'ok', 'okay', 'sure', 'yep', 'no', 'nope']
        if response_lower in simple_affirmations:
            return False
        if len(response.split()) >= 3:
            return True
        if any(char.isdigit() for char in response):
            return True
        return False
    
    def _extract_customer_preference(self, response):
        """Extract and update customer preferences from response"""
        response_lower = response.lower()
        
        # Check for follow-up requests (but NOT if they said "not busy")
        if "not busy" not in response_lower and "i'm not busy" not in response_lower:
            follow_up_keywords = ['call me tomorrow', 'call tomorrow', 'tomorrow', 'later', 'busy', 'stressed']
            if any(keyword in response_lower for keyword in follow_up_keywords):
                self.customer_preference = 'follow_up_requested'
                print(f"[DEBUG] Customer requested follow-up")
        
        if self.sector == 'banking':
            if 'credit card' in response_lower:
                self.customer_preference = 'credit card'
                print(f"[DEBUG] Updated preference to: credit card")
            elif 'personal loan' in response_lower or 'loan' in response_lower:
                self.customer_preference = 'personal loan'
                print(f"[DEBUG] Updated preference to: personal loan")
        elif self.sector == 'real_estate':
            if '1 bhk' in response_lower or '1bhk' in response_lower:
                self.customer_preference = '1 BHK'
            elif '2 bhk' in response_lower or '2bhk' in response_lower:
                self.customer_preference = '2 BHK'
            elif '3 bhk' in response_lower or '3bhk' in response_lower:
                self.customer_preference = '3 BHK'
        elif self.sector == 'medical':
            if 'health checkup' in response_lower or 'checkup' in response_lower:
                self.customer_preference = 'health checkup'
                print(f"[DEBUG] Updated preference to: health checkup")
            elif 'consultation' in response_lower:
                self.customer_preference = 'medical consultation'
                print(f"[DEBUG] Updated preference to: medical consultation")
    
    def _check_for_explicit_completion(self, customer_response):
        """Check if customer has EXPLICITLY confirmed a concrete next step"""
        response_lower = customer_response.lower().strip()
        last_ai_lower = self.last_ai_message.lower()
        
        information_gathering_phrases = [
            'what day', 'what time', 'which day', 'which time', 'when would',
            'please let me know', 'could you tell me', 'could you please',
            'what is your', 'what\'s your', 'can you provide', 'can you share',
            'specific time', 'preferred time', 'preferred date', 'what works',
            'salary range', 'monthly income', 'budget range', 'how much',
            'which property', 'what type', 'which package', 'what area',
            'what service', 'which service', 'what concerns', 'any concerns'
        ]
        
        if any(phrase in last_ai_lower for phrase in information_gathering_phrases):
            print(f"[DEBUG] AI is gathering information - NOT completing")
            return False
        
        final_confirmation_phrases = [
            'shall i send', 'should i send', 'shall i book', 'should i book',
            'shall i schedule', 'should i schedule', 'shall i proceed',
            'would you like me to send', 'would you like me to book',
            'can i send', 'can i book', 'let me send', 'let me book',
            'i will send', 'i\'ll send', 'i will book', 'i\'ll book'
        ]
        
        if any(phrase in last_ai_lower for phrase in final_confirmation_phrases):
            if self.meaningful_responses_count >= 2 and self.total_interactions >= 5:
                print(f"[DEBUG] Final confirmation received after AI offered specific action")
                self.explicit_confirmation_received = True
                return True
        
        explicit_confirmations = [
            'yes please send', 'yes send it', 'yes book it', 'yes schedule it',
            'please proceed', 'go ahead and send', 'go ahead and book',
            'confirm booking', 'confirm appointment', 'send the link',
            'book the appointment', 'schedule the appointment'
        ]
        
        if any(phrase in response_lower for phrase in explicit_confirmations):
            print(f"[DEBUG] Customer explicitly confirmed specific action")
            self.explicit_confirmation_received = True
            return True
        
        return False
    
    def _check_for_explicit_end(self, customer_response):
        """Check if customer explicitly wants to end the conversation"""
        response_lower = customer_response.lower().strip()
        
        if response_lower in ['thank you', 'thanks', 'thank you.', 'thanks.']:
            return False
        
        end_phrases = [
            'bye', 'goodbye', 'good bye', 'thank you. bye', 'thanks. bye', 
            'thank you, bye', 'thanks, bye', 'talk to you later', 'see you',
            'talk later', 'speak later', 'have a good day', 'bye bye'
        ]
        
        return any(phrase in response_lower for phrase in end_phrases)
    
    def _check_for_inconvenience(self, customer_response):
        """Check if customer is expressing inconvenience/busy/not available"""
        response_lower = customer_response.lower().strip()
        
        # Exclude cases where they say "not busy"
        if "not busy" in response_lower or "i'm not busy" in response_lower or "im not busy" in response_lower:
            print(f"[DEBUG] Customer said 'not busy' - NOT marking as inconvenient")
            return False
        
        inconvenience_phrases = [
            'busy', 'stressed', 'later', 'call me later',
            'call later', 'call me back', 'call back', 'not a good time',
            'bad time', 'not available', 'in a meeting', 'driving',
            'at work', 'working', 'can\'t talk', 'cannot talk',
            'call me tomorrow', 'call tomorrow', 'call me next week',
            'maybe later', 'some other time',
            'occupied', 'hectic', 'rush', 'hurry', 'running late'
        ]
        
        return any(phrase in response_lower for phrase in inconvenience_phrases)
    
    def _generate_follow_up_closing(self, customer_response):
        """Generate a polite closing when customer is busy"""
        response_lower = customer_response.lower()
        
        if 'tomorrow' in response_lower:
            follow_up_time = 'tomorrow'
        elif 'next week' in response_lower:
            follow_up_time = 'next week'
        else:
            follow_up_time = 'at a better time'
        
        closings = {
            'banking': f"I completely understand, {self.customer_name}. I'll give you a call {follow_up_time} to discuss our banking services. Thank you for your time!",
            'real_estate': f"No problem at all, {self.customer_name}! I'll reach out {follow_up_time} regarding our properties. Have a great day!",
            'medical': f"Of course, {self.customer_name}. I'll contact you {follow_up_time} about our health services. Take care!"
        }
        
        return closings.get(self.sector, f"I understand, {self.customer_name}. I'll call you {follow_up_time}. Thank you!")
    
    def _handle_completion(self):
        """Handle conversation completion"""
        self.application_initiated = True
        self.end_time = datetime.now()
        
        if self.sector == 'real_estate':
            closing = f"Perfect, {self.customer_name}! I've scheduled your site visit for this weekend. You'll receive a confirmation call with all the details within 24 hours. Thank you for your interest!"
        elif self.sector == 'banking':
            product = self.customer_preference or 'application'
            closing = f"Excellent! I'll send you the {product} details and application link right away via SMS. You should receive it within the next few minutes. Thank you for choosing us!"
        elif self.sector == 'medical':
            closing = f"Great! Your consultation appointment is being scheduled. Our team will call you within 24 hours to confirm the exact date and time. Take care!"
        else:
            closing = f"Thank you so much, {self.customer_name}! I'll process this right away and you'll receive confirmation shortly. Have a wonderful day!"
        
        self.conversation_log.append(f"AI Agent: {closing}")
        self.closing_sent = True
        self.set_final_actions()
        return closing
    
    def _update_conversation_state(self, analysis):
        """Update conversation state based on AI analysis"""
        interest_level = analysis.get('interest_level', 'Unknown')
        if interest_level == 'High':
            self.conversation_state = 'interested'
        elif interest_level == 'Not Interested':
            self.conversation_state = 'not_interested'
        elif interest_level in ['Low', 'Medium']:
            self.conversation_state = 'exploring'
        elif self.customer_preference:
            self.conversation_state = 'interested'
    
    def _should_end_conversation(self, analysis, customer_response):
        """Determine if conversation should end - IMPROVED WITH MEDICAL FIX"""
        if self.closing_sent:
            print(f"[DEBUG] Closing message already sent - Ending conversation")
            return True
        
        # CRITICAL FIX FOR MEDICAL: Require MINIMUM interactions AND substantive questions
        # Medical needs at least: Opening -> Service type -> Details -> Schedule -> Confirm
        min_interactions = 6
        min_substantive_questions = 2  # Must ask at least 2 real questions beyond opening
        
        if self.total_interactions < min_interactions:
            print(f"[DEBUG] Conversation too short ({self.total_interactions}/{min_interactions} interactions) - NOT ending")
            return False
        
        # NEW: For medical, ensure we've asked substantive questions
        if self.sector == 'medical' and self.substantive_questions_asked < min_substantive_questions:
            print(f"[DEBUG] MEDICAL: Not enough substantive questions ({self.substantive_questions_asked}/{min_substantive_questions}) - NOT ending")
            return False
        
        last_ai_lower = self.last_ai_message.lower()
        response_lower = customer_response.lower().strip()
        
        # CRITICAL: End immediately if meeting/appointment was EXPLICITLY scheduled with specific time
        meeting_scheduled_phrases = [
            'scheduled the call', 'scheduled a callback', 'scheduled for tomorrow',
            'appointment is scheduled', 'i\'ve scheduled', 'meeting is set',
            'we\'re all set', 'callback for you tomorrow', 'i have scheduled',
            'scheduled your', 'booked for', 'appointment for', 'call for you',
            'set up for', 'confirmed for', 'your appointment is',
            # REAL ESTATE SPECIFIC:
            'looking forward to seeing you', 'see you on', 'see you this'
        ]
        
        has_scheduled_confirmation = any(phrase in last_ai_lower for phrase in meeting_scheduled_phrases)
        
        # If AI JUST confirmed scheduling with time in previous message, END NOW
        if self.meeting_scheduled_with_time and has_scheduled_confirmation:
            print(f"[DEBUG] ✅ Ending: Meeting was scheduled with specific time and AI confirmed it")
            return True
        
        # If AI just asked a question, NEVER end
        if '?' in self.last_ai_message:
            print(f"[DEBUG] AI just asked a question - NOT ending")
            return False
        
        # Check for follow-up scheduling
        follow_up_scheduled_phrases = [
            'call you tomorrow', 'call tomorrow', 'speak tomorrow', 'talk tomorrow',
            'follow up tomorrow', 'get back to you', 'reach out tomorrow'
        ]
        
        simple_acknowledgments = ['ok', 'okay', 'sure', 'alright', 'fine', 'yes', 'yeah']
        
        if any(phrase in last_ai_lower for phrase in follow_up_scheduled_phrases):
            if response_lower in simple_acknowledgments and self.consecutive_simple_acks >= 3:
                print(f"[DEBUG] Ending: Follow-up scheduled and customer confirmed 3+ times")
                return True
            else:
                print(f"[DEBUG] Follow-up mentioned but not enough confirmations ({self.consecutive_simple_acks})")
                return False
        
        # Information gathering - NEVER end
        information_gathering_phrases = [
            'what day', 'what time', 'which day', 'which time', 'when would',
            'please let me know', 'could you tell me', 'could you please',
            'what is your', 'what\'s your', 'can you provide', 'specific time',
            'salary range', 'monthly income', 'budget range', 'what works',
            'would you like', 'are you interested', 'what type', 'what service',
            'which service', 'any concerns', 'what concerns', 'for yourself'
        ]
        
        if any(phrase in last_ai_lower for phrase in information_gathering_phrases):
            print(f"[DEBUG] AI waiting for information - NOT ending")
            return False
    
        # Check for explicit completion
        if self._check_for_explicit_completion(customer_response):
            print(f"[DEBUG] Ending: Application confirmed with all details")
            return True
        
        # Disinterest tracking
        if analysis.get('interest_level') in ['Low', 'Not Interested']:
            self.disinterest_count += 1
            print(f"[DEBUG] Disinterest detected ({self.disinterest_count}/4)")
            if self.disinterest_count >= 4:
                print(f"[DEBUG] Ending: Repeated disinterest detected")
                return True
        else:
            self.disinterest_count = 0
        
        # Let AI analysis decide
        if not analysis.get('continue_conversation', True):
            end_reason = analysis.get('end_reason', '')
            if end_reason in ['explicit_goodbye', 'action_confirmed_with_details', 'repeated_not_interested']:
                print(f"[DEBUG] Ending: AI determined strong completion signal - {end_reason}")
                return True
            else:
                print(f"[DEBUG] AI suggested ending but reason unclear ({end_reason}) - continuing")
                return False
        
        # Length-based ending
        if self.total_interactions >= 20 and self.meaningful_responses_count < 3:
            print(f"[DEBUG] Ending: Too long without engagement")
            return True
        
        if self.total_interactions >= 30:
            print(f"[DEBUG] Ending: Maximum interactions reached")
            return True
        
        return False
    
    def set_final_actions(self):
        """Set final actions based on conversation outcome"""
        print(f"[DEBUG] Setting final actions - Interest: {self.customer_interest_level}")
        print(f"[DEBUG] Application initiated: {self.application_initiated}")
        print(f"[DEBUG] Meaningful responses: {self.meaningful_responses_count}")
        print(f"[DEBUG] Meeting scheduled: {self.meeting_scheduled_with_time}")
        
        if self.meeting_scheduled_with_time or (self.application_initiated and self.explicit_confirmation_received):
            self.action_required = 'Yes'
            product = self.customer_preference or 'service'
            if self.sector == 'medical':
                self.next_action = f"Schedule {product.title()} Appointment - CONFIRMED"
            elif self.sector == 'real_estate':
                self.next_action = f"Site Visit Scheduled - CONFIRMED"
            else:
                self.next_action = f"Process {product.title()} Application/Booking - MEETING SCHEDULED"
            self.action_assignee = 'Application Team'
            self.remarks = f"Customer {self.customer_name} scheduled {'appointment' if self.sector == 'medical' else 'site visit' if self.sector == 'real_estate' else 'meeting'} with specific time. Follow up as scheduled."
        elif self.customer_preference == 'follow_up_requested':
            self.action_required = 'Yes'
            self.next_action = 'Follow-up Call Tomorrow'
            self.action_assignee = 'To the Agent'
            self.remarks = f"Customer {self.customer_name} was busy/stressed and requested follow-up. Schedule call at convenient time."
        elif self.customer_interest_level == 'High' or self.meaningful_responses_count >= 3:
            self.action_required = 'Yes'
            self._set_high_interest_actions()
        elif self.customer_interest_level == 'Medium' or self.meaningful_responses_count >= 1:
            self.action_required = 'Yes'
            self.next_action = 'Follow-up Call Tomorrow'
            self.action_assignee = 'To the Agent'
            self.remarks = f"Customer {self.customer_name} showed moderate interest or deferred to a later time. Schedule follow-up call tomorrow."
        elif self.customer_interest_level == 'Low':
            self.action_required = 'Yes'
            self.next_action = 'Follow-up Call in 2 weeks'
            self.action_assignee = 'To the Agent'
            self.remarks = f"Customer {self.customer_name} showed minimal interest. Follow-up after 2 weeks."
        elif self.customer_interest_level == 'Not Interested':
            self.action_required = 'No'
            self.next_action = 'Mark as Do Not Call'
            self.action_assignee = 'System'
            self.remarks = f"Customer {self.customer_name} clearly not interested in {self.sector} services."
        else:
            self.action_required = 'Yes'
            self.next_action = 'Follow-up Call in 1 week'
            self.action_assignee = 'To the Agent'
            self.remarks = f"Conversation with {self.customer_name} was inconclusive. Requires follow-up."
        
        conversation_duration = (self.end_time - self.start_time).total_seconds() / 60 if self.end_time else 0
        self.remarks += f" Duration: {conversation_duration:.1f}min. Interactions: {self.total_interactions}. Meaningful responses: {self.meaningful_responses_count}."
    
    def _set_high_interest_actions(self):
        """Set actions for high-interest customers"""
        if self.sector == 'banking':
            financial_info_provided = any(
                keyword in ' '.join(self.conversation_log).lower() 
                for keyword in ['salary', 'income', 'rupees', 'lakh', 'thousand', 'per month']
            )
            if self.customer_preference:
                self.next_action = f'Send {self.customer_preference.title()} Application Link'
                self.remarks = f"Customer interested in {self.customer_preference}. Send application immediately."
            elif financial_info_provided:
                self.next_action = 'Pre-qualify & Send Application'
                self.remarks = f"Customer provided financial details. Pre-qualify and send application."
            else:
                self.next_action = 'Schedule Callback for Details'
                self.remarks = f"Customer interested. Schedule callback to collect information."
        elif self.sector == 'real_estate':
            property_details = any(
                keyword in ' '.join(self.conversation_log).lower() 
                for keyword in ['bhk', 'budget', 'area', 'location']
            )
            if property_details:
                self.next_action = 'Schedule Site Visit This Weekend'
                self.remarks = f"Customer has specific requirements. Arrange site visit."
            else:
                self.next_action = 'Send Brochures & Schedule Call'
                self.remarks = f"Customer interested. Send materials and follow up."
        elif self.sector == 'medical':
            health_mentioned = any(
                keyword in ' '.join(self.conversation_log).lower() 
                for keyword in ['checkup', 'health', 'consultation', 'appointment']
            )
            if health_mentioned:
                self.next_action = 'Schedule Consultation This Week'
                self.remarks = f"Customer needs health services. Priority booking."
            else:
                self.next_action = 'Send Package Details & Follow-up'
                self.remarks = f"Customer interested. Send comprehensive info."
        self.action_assignee = 'To the Agent'