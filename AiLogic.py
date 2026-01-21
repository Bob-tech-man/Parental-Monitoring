import ollama
import json

class AiModule:
    def __init__(self):
        self.model= 'gemma3:4b'

    def check_history(self, age, history):
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
        6. הסיבה לכל אתר תהיה קשורה ישירות לתוכן האתר בכמה משפטים.

        מבנה הפלט:
        {{
          "blocked_websites": [],
          "reason_for_each": []
        }}
        """

        response = ollama.chat(
            model=self.model,
            format="json",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        raw_text = response["message"]["content"]
        parsed = parse_ai_json(raw_text)
        return parsed

    def recommend_blocked_websites(self, age):
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

        response = ollama.chat(
            model=self.model,
            format="json",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        raw_text = response["message"]["content"]
        parsed = parse_ai_json(raw_text)
        return parsed


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


# def process_history(self, data, age):
#     history_sites = []
#
#     for item in data:
#         url = item.get("url", "")
#         if url:
#             domain = url.split("//")[-1].split("/")[0]
#             history_sites.append(domain)
#
#     response = self.agent.check_history(age, history_sites)
#     return response

    # ADD THIS INTO SERVER!!!!!!!!!!!! SWITCH FROM OLD TO NEW