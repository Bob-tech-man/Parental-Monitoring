import json
import base64

def vigenere_cipher(text, key, decrypt=False):
    result = ""
    for i in range(len(text)):
        char = text[i]
        key_char = key[i % len(key)]

        if decrypt:
            # (Cipher - Key) modulo 256
            new_char = chr((ord(char) - ord(key_char)) % 256)
        else:
            # (Original + Key) modulo 256
            new_char = chr((ord(char) + ord(key_char)) % 256)
        result += new_char
    return result


def encrypt_data(data_dict, key):
    json_str = json.dumps(data_dict)
    encrypted = vigenere_cipher(json_str, key)
    return base64.b64encode(encrypted.encode('latin-1')).decode('utf-8')


def decrypt_data(encoded_str, key):
    try:
        encrypted_str = base64.b64decode(encoded_str).decode('latin-1')
        json_str = vigenere_cipher(encrypted_str, key, decrypt=True)
        return json.loads(json_str)
    except Exception as e:
        print(f"Decryption failed: {e}")
        return None

CIPHER_KEY = "my_super_secret_key_123"
