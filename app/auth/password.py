"""
Password Hashing and Verification
Uses bcrypt for secure password storage
"""

from passlib.context import CryptContext
import secrets
import string

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain password
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_random_password(length: int = 12) -> str:
    """
    Generate a secure random password
    
    Args:
        length: Length of password (default 12)
        
    Returns:
        Random password string
    """
    # Characters to use: letters (upper and lower) + digits
    characters = string.ascii_letters + string.digits
    
    # Generate random password
    password = ''.join(secrets.choice(characters) for _ in range(length))
    
    return password