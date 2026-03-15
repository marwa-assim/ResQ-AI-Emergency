import random
from huawei_cloud_api import huawei_services

class AICopilot:
    def __init__(self):
        # The AI Copilot uses Huawei Cloud ModelArts for dynamic inference when keys are provided,
        # otherwise it falls back to a deterministic protocol system for demo resilience.
        self.protocols = {
            "chest_pain": {
                "title": "Suspected Cardiac Event Protocol",
                "steps": [
                    "Sit the patient down immediately in a comfortable semi-reclined position.",
                    "Keep the patient calm to reduce heart strain.",
                    "If the patient has prescribed Angina medication (Nitroglycerin), assist them in taking it.",
                    "Loosen any tight clothing around the neck and chest.",
                    "Monitor breathing and pulse constantly.",
                    "Prepare for CPR if the patient loses consciousness."
                ],
                "warning": "Do not give the patient anything to eat or drink."
            },
            "breathing": {
                "title": "Respiratory Distress Protocol",
                "steps": [
                    "Help the patient sit upright (High Fowler's position) to aid breathing.",
                    "Ask the patient to take slow, deep breaths.",
                    "If asthmatic, assist with their inhaler immediately (usually 2-4 puffs).",
                    "Loosen tight clothing around the chest and neck.",
                    "Check for bluish lips or fingertips (Cyanosis)."
                ],
                "warning": "If breathing stops, begin rescue breathing immediately."
            },
            "bleeding": {
                "title": "Hemorrhage Control Protocol",
                "steps": [
                    "Apply direct, firm pressure to the wound with a clean cloth or gauze.",
                    "Elevate the injured limb above the level of the heart if possible.",
                    "Do not remove the cloth if it soaks through; add more layers on top.",
                    "If blood spurs, a tourniquet may be necessary (2 inches above wound).",
                    "Keep the patient warm to prevent shock."
                ],
                "warning": "Do not remove the original dressing."
            },
            "fainting": {
                "title": "Syncope Recovery Protocol",
                "steps": [
                    "Lay the patient flat on their back.",
                    "Elevate legs 12 inches to restore blood flow to the brain.",
                    "Loosen tight belts, collars, or clothing.",
                    "Check for breathing and pulse.",
                    "When they wake, keep them lying down for 10-15 minutes."
                ],
                "warning": "Do not splash water on their face or slap them."
            },
            "burn": {
                "title": "Thermal Injury Protocol",
                "steps": [
                    "Cool the burn running cool (not cold) tap water for 10-20 minutes.",
                    "Remove jewelry or tight items from the burned area immediately before swelling starts.",
                    "Cover the burn loosely with sterile gauze or plastic wrap.",
                    "Do not break blisters."
                ],
                "warning": "Do not apply butter, oil, or ice to the burn."
            },
            "choking": {
                "title": "Airway Obstruction Protocol",
                "steps": [
                    "Encourage the patient to cough forcefully.",
                    "If silent/unable to breathe: Perform 5 back blows between shoulder blades.",
                    "If failed: Perform 5 abdominal thrusts (Heimlich maneuver).",
                    "Alternate between back blows and abdominal thrusts until object is expelled."
                ],
                "warning": "Call 911 immediately if patient becomes unconscious."
            },
            "default": {
                "title": "General First Aid Protocol",
                "steps": [
                    "Ensure the scene is safe before approaching.",
                    "Check the patient's responsiveness (Tap and Shout).",
                    "Call for emergency help immediately.",
                    "Keep the patient comfortable and monitor vitals.",
                    "Do not move the patient unless in immediate danger."
                ],
                "warning": "Stay on the line with the dispatcher."
            }
        }

    def generate_plan(self, symptoms_text, priority_score):
        """
        Generates a tailored care plan using Huawei Cloud ModelArts.
        Args:
            symptoms_text (str): Raw text from user (voice or typed).
            priority_score (int): 0-3 Criticality score from MindSpore model.
        """
        # Call the Huawei Cloud API Wrapper
        context_str = "Priority Level: " + str(priority_score)
        plan = huawei_services.invoke_modelarts_copilot(symptoms_text, context_str)
        return plan

# Singleton Instance
copilot = AICopilot()
