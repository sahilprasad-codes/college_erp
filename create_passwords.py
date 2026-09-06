import sqlite3

conn = sqlite3.connect('college_erp_final.db')
cursor = conn.cursor()

print("\n⚙️ Generating Login credentials for PDF Students...")

try:
    # 1. students टेबल से सभी के ईमेल निकालो
    cursor.execute("SELECT email, name FROM students;")
    all_students = cursor.fetchall()
    
    count = 0
    for email, name in all_students:
        # 2. चैक करो कि क्या यह ईमेल पहले से users टेबल में है?
        cursor.execute("SELECT id FROM users WHERE LOWER(username)=? OR LOWER(email)=? ;", (email.lower(), email.lower()))
        exists = cursor.fetchone()
        
        if not exists:
            # 3. अगर नहीं है, तो उसे 'student123' पासवर्ड के साथ users टेबल में डाल दो
            # नोट: अगर आपकी टेबल में 'username' कॉलम है तो हम वही इस्तेमाल कर रहे हैं
            cursor.execute("PRAGMA table_info(users);")
            cols = [c[1] for c in cursor.fetchall()]
            
            if 'email' in cols:
                cursor.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?);", (email, email, 'student123', 'student'))
            else:
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?);", (email, 'student123', 'student'))
            count += 1

    conn.commit()
    print(f"✅ Success! Created login accounts for {count} new students.")
    print("🔒 Default Password for all accounts is: student123\n")

except Exception as e:
    print(f"❌ Error: {e}")

conn.close()