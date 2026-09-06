import sqlite3

conn = sqlite3.connect('college_erp_final.db')
cursor = conn.cursor()

print("\n" + "="*60)
print("       📊 NEXUS ERP CREDENTIALS BYPASS LOGS        ")
print("="*60)

try:
    # 1. पहले देखते हैं कि USERS टेबल में कौन-कौन से कॉलम्स हैं
    cursor.execute("PRAGMA table_info(users);")
    columns = [col[1] for col in cursor.fetchall()]
    
    print(f"-> आपकी 'users' टेबल में ये कॉलम्स मिले: {columns}\n")
    
    # 2. कॉलम्स के हिसाब से डायनामिक क्वेरी बनाना
    query_cols = []
    if 'username' in columns: query_cols.append('username')
    elif 'email' in columns: query_cols.append('email')
    else: query_cols.append(columns[0]) # अगर दोनों न मिले तो पहला कॉलम उठा लो
    
    if 'password' in columns:
        query_cols.append('password')
    if 'role' in columns:
        query_cols.append('role')

    select_clause = ", ".join(query_cols)
    
    # 3. पासवर्ड फेच करना
    cursor.execute(f"SELECT {select_clause} FROM users;")
    users = cursor.fetchall()
    
    print("[🔑 LOGIN USER CREDENTIALS FOUND]")
    if not users:
        print("-> users टेबल पूरी तरह खाली है भाई!")
    for u in users:
        user_info = f"User/Identity: {u[0]}"
        pass_info = f" | Password: {u[1]}" if len(u) > 1 else " | No Password Col"
        role_info = f" | Role: {u[2]}" if len(u) > 2 else ""
        print(user_info + pass_info + role_info)

except Exception as e:
    print(f"❌ गंभीर एरर: {e}")

# 4. टेस्टिंग बाईपास क्रेडेंशियल्स की जानकारी देना
print("-"*60)
print("[💡 QUICK TESTING BYPASS]")
print("अगर डेटाबेस खाली भी हो, तो आप इन क्रेडेंशियल्स से सीधे लॉगिन कर सकते हैं:")
print("• FACULTY LOGIN -> Email: teacher@faculty.com | Password: faculty123")
print("• STUDENT LOGIN -> Email: rahul@student.com   | Password: student123")

conn.close()
print("="*60 + "\n")