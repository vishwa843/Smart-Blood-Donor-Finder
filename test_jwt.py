from app.auth.jwt_handler import (
    create_access_token,
    verify_access_token,
)

data = {
    "sub": "sakthi@gmail.com",
    "role": "donor",
}

token = create_access_token(data)

print("TOKEN:\n")
print(token)

print("\nPAYLOAD:\n")
print(verify_access_token(token))