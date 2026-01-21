from google import genai
import json

key = "AIzaSyD1wVVh1Zp-cJk4N6KIJUaktCEdeU33Kp4"

class AiModule:
    def __init__(self, key):
        self.key = key
        self.model = "gemini-2.5-flash"
    def activate_module(self):
        client = genai.Client(api_key=self.key)
        return client

    def check_history(self, age, history):

        client = self.activate_module()

        prompt = f"""
        אתה מנוע חישוב למערכת בקרת הורים. אין לך שיקול דעת עצמאי.

        קלט:
        - גיל הילד: {age}
        - היסטוריית גלישה (רשימת אתרים): {history}

        משימה:
        נתח אך ורק את האתרים שמופיעים בהיסטוריית הגלישה.
        יש להחליט אם אתר מסוים אינו מתאים בהתאם לגיל הילד הנתון.
        אסור לך להוסיף, להציע או להמציא אתרים שלא הופיעו בקלט.

        כללים מחייבים:
        1. החזר JSON תקני בלבד.
        2. אסור לכלול אתר שלא מופיע במפורש בהיסטוריית הגלישה.
        3. אם אין אף אתר בעייתי – החזר מערכים ריקים.
        4. אין להשתמש בידע כללי או ברשימות ברירת מחדל.
        5. כל אתר חייב להופיע בדיוק כפי שהופיע בקלט.
        6. הסיבה לכל אתר תהיה קשורה ישירות לתוכן האתר.

        מבנה הפלט:
        {{
          "blocked_websites": [],
          "reason_for_each": []
        }}
        """

        response = client.models.generate_content(model="gemini-2.5-flash", contents=f"{prompt}")
        return response.text

    def recommend_blocked_websites(self, age):
        client = self.activate_module()


        prompt = f"""
                אתה יועץ בינה מלאכותית למערכת בקרת הורים.
        
        קלט:
        - גיל הילד: {age}
        
        משימה:
        בהתאם לגיל הילד, הצע רשימה של אתרי אינטרנט ופלטפורמות מקוונות שיש לחסום כברירת מחדל עבור ילד בגיל זה.
        
        כללים חשובים:
        1. החזר תשובה בפורמט JSON תקני בלבד, ללא טקסט נוסף וללא Markdown.
        2. אל תספק הסברים, נימוקים או סיבות לחסימה.
        3. החזר רק אתרים נפוצים וכלליים (רשתות חברתיות, פלטפורמות תוכן, פורומים, צ'אטים).
        4. אל תכלול אתרים חינוכיים או אתרים המיועדים לילדים.
        5. כל אתר יופיע פעם אחת בלבד.
        6. אם אין אתרים מומלצים לחסימה – החזר מערך ריק.
        
        מבנה הפלט המחייב:
        {{
          "websites_to_block": [
            "example.com",
            "example2.com"
          ]
        }}
        """

        response = client.models.generate_content(model="gemini-2.5-flash", contents=f"{prompt}")
        return response.text

def parse_ai_json(response_text):

    response_text = response_text.strip()

    start = response_text.find("{")
    end = response_text.rfind("}") + 1

    if start == -1 or end == -1:
        return None

    json_str = response_text[start:end]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


