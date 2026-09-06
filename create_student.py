import sqlite3
# अगर आपका प्रोजेक्ट पासवर्ड हैश करता है, तो ये इम्पोर्ट काम आएगा
try:
    from werkzeug.security import generate_password_hash
    USE_HASH = True
except ImportError:
    USE_HASH = False

def add_fresh_student():
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    # क्रेडेंशियल्स जो हम सेट कर रहे हैं
    email = "rahul@student.com"
    plain_password = "student123"
    name = "Rahul Sharma"
    class_name = "TY-CS" # जो भी आपकी क्लास का नाम हो
    
    # पासवर्ड को हैश करना है या प्लेन टेक्स्ट रखना है, ये चेक करते हैं
    if USE_HASH:
        password_to_store = generate_password_hash(plain_password)
    else:
        password_to_store = plain_password

    try:
        # 1. पहले मुख्य 'users' टेबल में एंट्री करते हैं (जहाँ से लॉगिन चेक होता है)
        cursor.execute("""
            INSERT INTO users (name, email, password, role) 
            VALUES (?, ?, ?, 'student')
        """, (name, email, password_to_store))
        
        # 2. फिर 'students' प्रोफाइल टेबल में एंट्री करते हैं (ताकि फैकल्टी को डैशबोर्ड पर दिखे)
        # नोट: अगर आपकी टेबल में रोल नंबर या कोई और कॉलम है, तो यहाँ एडजस्ट कर सकते हैं
        cursor.execute("""
            INSERT INTO students (name, email, class_name) 
            VALUES (?, ?, ?)
        """, (name, email, class_name))
        
        conn.commit()
        print("==========================================")
        print("✅ Student Account Created Successfully!")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {plain_password}")
        print("==========================================")
        
    except sqlite3.IntegrityError:
        print("❌ यह ईमेल पहले से मौजूद है! आप नीचे दिए गए क्रेडेंशियल्स से सीधे लॉगिन ट्राई करें।")
    except sqlite3.OperationalError as e:
        print(f"❌ डेटाबेस एरर: {e}")
        print("💡 एक बार अपनी टेबल के कॉलम्स चेक कर लें।")
    finally:
        conn.close()

if __name__ == "__main__":
    add_fresh_student()