from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, BadPassword, TwoFactorRequired
import time

USERNAME = "gensnap37"
PASSWORD = "GenSnap@37"

cl = Client()

try:
    cl.login(USERNAME, PASSWORD)
    cl.dump_settings("session.json")
    print("✅ Login successful, session saved!")

except ChallengeRequired:
    print("📲 Instagram sent a verification code to your email/phone.")
    
    # Request the code to be sent
    try:
        cl.challenge_resolve(cl.last_json)
        time.sleep(2)
    except Exception as e:
        print(f"(challenge_resolve: {e})")

    code = input("Enter the 6-digit code: ").strip()

    # Try submitting the code
    try:
        cl.challenge_resolve_simple(code)
        print("✅ Code accepted!")
    except Exception as e:
        print(f"(challenge_resolve_simple failed: {e}, trying challenge_flow...)")
        try:
            cl.challenge_flow(cl.last_json, code)
            print("✅ Code accepted via challenge_flow!")
        except Exception as e2:
            print(f"❌ Both methods failed: {e2}")
            raise

    cl.dump_settings("session.json")
    print("✅ Session saved!")

except TwoFactorRequired:
    code = input("Enter your 2FA code: ").strip()
    cl.login(USERNAME, PASSWORD, verification_code=code)
    cl.dump_settings("session.json")
    print("✅ Login successful, session saved!")

except BadPassword as e:
    print(f"❌ Blocked by Instagram (IP issue): {e}")
    print("→ Connect to mobile hotspot and try again")
