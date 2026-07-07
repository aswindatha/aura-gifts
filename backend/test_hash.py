import bcrypt
hashed = '$2b$12$qeOYGo57bFFwAd0r9fv4sO1P40Ea3skiOOdjRrN4/znn3iMK3ToKa'.encode('utf-8')
plain = 'deva123'.encode('utf-8')
try:
    if bcrypt.checkpw(plain, hashed):
        print("MATCHES!")
    else:
        print("DOES NOT MATCH!")
except Exception as e:
    print(f"Error: {e}")
